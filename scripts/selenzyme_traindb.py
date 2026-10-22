"""
selenzyme_traindb.py — Build SelenzymeRF reference databases from ECReact training splits.

Selenzyme's own pipeline (ECNumberPrediction/methods/SelenzymeRF/SelenzymeRF_code/data_update/
make_fingerprint_atomMap.py) builds its compound (FP_Morg) and reacting-fragment (FP_MorgRF,
RXNMapper) fingerprints from MetaNetX-format tables. This script feeds it ECReact instead:

  prepare  : all ECReact reactions -> MetaNetX-format raw tables (chem_prop.tsv, reac_prop.tsv,
             reaction_smiles_enz_filter.tsv) split into N shards, + id map. Reactions are keyed
             by RDKit-canonical SMILES (ECRR<n>), molecules by canonical SMILES (ECRM<n>); a
             reaction with several ECs gets them ';'-joined (Selenzyme supports that).
  merge    : (inside build/selenzyme.sif) merge the per-shard builder outputs into one FP_Morg.npz / FP_MorgRF.npz / reac_prop.tsv.
  seed_rids: per seed, the train reaction IDs (clean_ec env: same RDKit as prepare).
  seed_db  : (inside build/selenzyme.sif, whose RDKit unpickles the fingerprints) per seed, a Selenzyme data dir restricted to the seed's TRAIN reactions. Each
             reaction is linked (reac_seqs.tsv) to up to K UniProt sequences annotated with the
             same EC3 in Selenzyme's 2023 data (EC2/EC1 fallback), because Selenzyme only reports
             reactions that have sequences; the EC it reports is the reaction's own EC.

Usage (clean_ec env for prepare/seed_db; the builder runs inside build/selenzyme.sif):
  python scripts/selenzyme_traindb.py prepare --shards 20
  apptainer exec --bind /scratch build/selenzyme.sif python scripts/selenzyme_traindb.py merge
  python scripts/selenzyme_traindb.py seed_rids --seed 0
  apptainer exec --bind /scratch build/selenzyme.sif python scripts/selenzyme_traindb.py seed_db --seed 0
"""

import argparse
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SPLITS = ROOT / "data" / "ECReact_seeds_strat_dedup"
WORK = Path(os.environ.get("GEMMA4EC_WORK", "work")) / "selenzyme_traindb"
SEL = Path(os.environ.get("ECN_ROOT", "ECNumberPrediction")) / "methods/SelenzymeRF/SelenzymeRF_code"
BASE = SEL / "data_2023"
PAD = 351  # make_fingerprint_atomMap.py reads MetaNetX tables with skiprows=351


def norm_ec(ec):
    p = str(ec).strip().split(".")
    return ".".join(str(int(x)) if x.isdigit() else x for x in p)


def canon_mol(smi, cache={}):
    if smi not in cache:
        from rdkit import Chem
        m = Chem.MolFromSmiles(smi)
        cache[smi] = Chem.MolToSmiles(m) if m is not None else smi
    return cache[smi]


def write_padded(path, header, rows):
    with open(path, "w") as f:
        f.write("".join(f"# ECReact-derived table (padding for skiprows={PAD})\n" for _ in range(PAD)))
        f.write("\t".join(header) + "\n")
        for r in rows:
            f.write("\t".join("" if v is None else str(v) for v in r) + "\n")


def prepare(args):
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog("rdApp.*")
    sys.path.insert(0, str(ROOT / "scripts"))
    from canonicalize_smiles import canon_rxn
    allrows = pd.concat([pd.read_csv(SPLITS / "seed0" / f"{s}.csv", dtype=str) for s in ("train", "val", "test")],
                        ignore_index=True)
    allrows["rxn_smiles"] = allrows["rxn_smiles"].str.replace("->>", ">>", regex=False)
    allrows["key"] = allrows["rxn_smiles"].map(canon_rxn)
    rxns = allrows.groupby("key", sort=False).agg(smiles=("rxn_smiles", "first"),
                                                  ecs=("ec", lambda s: ";".join(sorted({norm_ec(e) for e in s}))))
    rxns = rxns.reset_index()
    rxns["rid"] = [f"ECRR{i}" for i in range(len(rxns))]

    mol_id, eqs, comps = {}, [], []
    for smi in rxns["smiles"]:
        sides, used = [], set()
        for side in smi.split(">>", 1):
            cnt = Counter(canon_mol(m) for m in side.split(".") if m)
            terms = []
            for m, n in cnt.items():
                if m not in mol_id:
                    mol_id[m] = f"ECRM{len(mol_id)}"
                terms.append(f"{n} {mol_id[m]}")
                used.add(mol_id[m])
            sides.append(" + ".join(terms))
        eqs.append(" = ".join(sides))
        comps.append(",".join(sorted(used)))
    rxns["equation"], rxns["compounds"] = eqs, comps

    WORK.mkdir(parents=True, exist_ok=True)
    rxns[["key", "rid", "smiles", "ecs", "equation"]].to_csv(WORK / "reaction_map.tsv", sep="\t", index=False)
    chem_rows = []
    for m, cid in mol_id.items():
        mol = Chem.MolFromSmiles(m)
        inchi = Chem.MolToInchi(mol) if mol is not None else ""
        chem_rows.append([cid, cid, "ecreact", "", "", "", inchi, "", m])
    chem_header = ["#ID", "name", "reference", "formula", "charge", "mass", "InChI", "InChIKey", "SMILES"]
    reac_header = ["#ID", "mnx_equation", "reference", "classifs", "is_balanced", "is_transport"]

    for k, shard in enumerate(np.array_split(rxns, args.shards)):
        raw = WORK / "raw" / f"shard{k}"
        raw.mkdir(parents=True, exist_ok=True)
        write_padded(raw / "chem_prop.tsv", chem_header, chem_rows)
        write_padded(raw / "reac_prop.tsv", reac_header,
                     [[r.rid, r.equation, "ecreact", r.ecs, "B", ""] for r in shard.itertuples()])
        with open(raw / "reaction_smiles_enz_filter.tsv", "w") as f:
            for r in shard.itertuples():
                f.write(f"{r.rid}\t{r.compounds}\n")
    print(f"[prepare] {len(rxns)} reactions, {len(mol_id)} molecules -> {args.shards} shards in {WORK}/raw")


def merge(args):
    fp_x, fp_y, seen = [], [], set()
    rf = {"x": [], "y": [], "z": [], "d": []}
    props = []
    for sh in sorted((WORK / "built").glob("shard*"), key=lambda p: int(p.name[5:])):
        m = np.load(sh / "Morgan" / "FP_Morg.npz", allow_pickle=True)
        for x, y in zip(m["x"], m["y"]):
            if y not in seen:
                seen.add(y); fp_x.append(x); fp_y.append(y)
        r = np.load(sh / "Morgan" / "RF" / "FP_MorgRF.npz", allow_pickle=True)
        for k in rf:
            rf[k].extend(list(r[k]))
        props.append(pd.read_csv(sh / "reac_prop.tsv", sep="\t", header=None, dtype=str))
    out = WORK / "merged"
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "FP_Morg.npz", x=np.array(fp_x, dtype=object), y=np.array(fp_y))
    d = np.empty(len(rf["d"]), dtype=object)
    d[:] = rf["d"]
    np.savez_compressed(out / "FP_MorgRF.npz", x=np.array(rf["x"], dtype=object), y=np.array(rf["y"]),
                        z=np.array(rf["z"]), d=d)
    pd.concat(props).to_csv(out / "reac_prop.tsv", sep="\t", header=False, index=False)
    print(f"[merge] {len(fp_y)} compound fps, {len(set(rf['z']))} reactions with reacting-fragment fps")


def db_name(args):
    """db/seed{S} for the train split; db/seed{S}_trainval for --splits train,val."""
    return f"seed{args.seed}" + ("" if args.splits == "train" else "_" + args.splits.replace(",", ""))


def seed_rids(args):
    """Seed's train reaction IDs. Run with the RDKit that ran `prepare` (keys are its canonical SMILES)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from canonicalize_smiles import canon_rxn
    rmap = pd.read_csv(WORK / "reaction_map.tsv", sep="\t", dtype=str)
    key2rid = dict(zip(rmap["key"], rmap["rid"]))
    tr = pd.concat([pd.read_csv(SPLITS / f"seed{args.seed}" / f"{sp}.csv", dtype=str) for sp in args.splits.split(",")])
    rids = sorted({key2rid[canon_rxn(s.replace("->>", ">>"))] for s in tr["rxn_smiles"]})
    out = WORK / "db" / db_name(args)
    out.mkdir(parents=True, exist_ok=True)
    (out / "train_rids.txt").write_text("\n".join(rids) + "\n")
    print(f"[seed_rids] seed{args.seed}: {len(rids)} train reactions")


def seed_db(args):
    """Run inside build/selenzyme.sif: the server unpickles these fingerprints with its own RDKit."""
    rmap = pd.read_csv(WORK / "reaction_map.tsv", sep="\t", dtype=str)
    out = WORK / "db" / db_name(args)
    rids = set((out / "train_rids.txt").read_text().split())
    m = WORK / "merged"

    prop = pd.read_csv(m / "reac_prop.tsv", sep="\t", header=None, dtype=str)
    prop = prop[prop[0].isin(rids)]
    prop.to_csv(out / "reac_prop.tsv", sep="\t", header=False, index=False)
    with np.load(m / "FP_MorgRF.npz", allow_pickle=True) as f:
        r = {k: f[k] for k in ("x", "y", "z", "d")}  # NpzFile re-decompresses on every r[key] access
    keep = np.isin(r["z"], list(rids))
    d = np.empty(int(keep.sum()), dtype=object)
    d[:] = [r["d"][i] for i in np.flatnonzero(keep)]
    np.savez_compressed(out / "FP_MorgRF.npz", x=r["x"][keep], y=r["y"][keep], z=r["z"][keep], d=d)
    shutil.copy(m / "FP_Morg.npz", out / "FP_Morg.npz")
    sub = rmap[rmap["rid"].isin(rids)]
    pd.DataFrame({"RID": sub["rid"], "SMILES": sub["smiles"]}).to_csv(out / "reac_smi.csv", index=False)

    # reaction -> sequences of the same EC (EC3, then EC2/EC1 fallback) from Selenzyme 2023 data
    seqs = pd.read_csv(BASE / "reac_seqs.tsv", sep="\t", header=None, dtype=str, usecols=[1, 2, 4])
    seqs.columns = ["db", "seq", "ec"]
    seqs = seqs.dropna().drop_duplicates(["seq", "ec"])
    by = {lvl: {} for lvl in (3, 2, 1)}
    for db, sq, ec in seqs.itertuples(index=False):
        p = norm_ec(ec).split(".")
        for lvl in (3, 2, 1):
            if len(p) >= lvl:
                lst = by[lvl].setdefault(".".join(p[:lvl]), [])
                if len(lst) < args.k and (db, sq) not in lst:
                    lst.append((db, sq))
    rows = []
    for rid, ecs in zip(sub["rid"], sub["ecs"]):
        for ec in ecs.split(";"):
            p = ec.split(".")
            for lvl in (3, 2, 1):
                hit = by[lvl].get(".".join(p[:lvl]))
                if hit:
                    rows += [[rid, db, sq, "ecreact", ec] for db, sq in hit]
                    break
    pd.DataFrame(rows).drop_duplicates().to_csv(out / "reac_seqs.tsv", sep="\t", header=False, index=False)
    for f in ("seq_org.tsv", "org_lineage.csv", "seqs.fasta", "reac_xref.tsv", "rxn_consensus_20160612.txt"):
        if (BASE / f).exists() and not (out / f).exists():
            os.symlink(BASE / f, out / f)
    print(f"[seed_db] seed{args.seed}: {len(prop)} train reactions, {int(keep.sum())} RF entries, "
          f"{len(rows)} reaction-sequence links -> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["prepare", "merge", "seed_rids", "seed_db"])
    ap.add_argument("--shards", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--k", type=int, default=3, help="sequences linked per EC")
    ap.add_argument("--splits", default="train", help="splits whose reactions form the reference DB, e.g. train,val")
    args = ap.parse_args()
    {"prepare": prepare, "merge": merge, "seed_rids": seed_rids, "seed_db": seed_db}[args.action](args)


if __name__ == "__main__":
    main()
