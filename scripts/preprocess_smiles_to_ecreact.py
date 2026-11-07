#!/usr/bin/env python3
"""Map an external benchmark's reaction SMILES onto ECReact's molecule forms (what Gemma4EC was trained on).

Per molecule, first match wins:
  1 exact     already written as in ECReact
  2 neutral   same uncharged structure (with stereo) -> ECReact form
  3 nostereo  same uncharged structure without stereo (source has no stereo)
  4 skeleton  same InChIKey skeleton -> ECReact form; reverted if two participants become identical (EC 5.1)
  5 ionized   not in ECReact: pH 7.3 rules, RDKit canonical
Only molecule forms come from ECReact, never labels.

Writes <out>/seed{S}/test.csv and <out>/prep_log.csv.
Usage: python scripts/preprocess_smiles_to_ecreact.py --src data/ECReact_seeds_rhea500 --out data/ECReact_seeds_rhea500_prep
"""

import argparse
import collections
from pathlib import Path

import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize

RDLogger.DisableLog("rdApp.*")
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "ECReact_seeds_rhea500"
OUT = ROOT / "data" / "ECReact_seeds_rhea500_prep"
ECREACT = ROOT / "data" / "ECReact_strat_dedup_splits.csv.gz"

UNCHARGER = rdMolStandardize.Uncharger()

ACID_O = Chem.MolFromSmarts("[OX2H1][$([CX3]=O),$([PX4]=O),$([SX4](=O)=O)]")
AMINE_N = Chem.MolFromSmarts("[NX3;H2,H1,H0;+0;!$(N[a]);!$(N[#6]=[#7,#8,#16]);!$(N[#7,#8,#15,#16]);!$(N[#6]#*)]"
                             "([CX4,#1])")


def uncharged(smi):
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return None
    try:
        return UNCHARGER.uncharge(m)
    except Exception:
        return m


def keys(smi):
    m = uncharged(smi)
    if m is None:
        return None, None
    return Chem.MolToSmiles(m), Chem.MolToSmiles(m, isomericSmiles=False)


def skeleton(smi):
    """InChIKey first block: connectivity only, blind to stereo and protonation."""
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return None
    try:
        k = Chem.MolToInchiKey(m)
        return k.split("-")[0] if k else None
    except Exception:
        return None


def ionize(smi):
    m = Chem.MolFromSmiles(smi)
    if m is None:
        return smi
    m = Chem.RWMol(m)
    acid = {a for (a, _) in m.GetSubstructMatches(ACID_O)}
    # amines bonded only to sp3 C / H (no amide, aniline, sulfonamide, N-N, N-O, nitrile)
    amine = {n for (n, *_) in m.GetSubstructMatches(AMINE_N)
             if all(nb.GetSymbol() == "C" and nb.GetHybridization() == Chem.HybridizationType.SP3
                    for nb in m.GetAtomWithIdx(n).GetNeighbors())}
    for i in acid:
        a = m.GetAtomWithIdx(i)
        a.SetFormalCharge(-1); a.SetNumExplicitHs(0); a.SetNoImplicit(True)
    for i in amine:
        a = m.GetAtomWithIdx(i)
        a.SetFormalCharge(1); a.SetNumExplicitHs(a.GetTotalNumHs() + 1); a.SetNoImplicit(True)
    try:
        Chem.SanitizeMol(m)
        return Chem.MolToSmiles(m)
    except Exception:
        return smi


def canonical(smi):
    """ECReact is RDKit canonical SMILES; put a molecule into that form."""
    m = Chem.MolFromSmiles(smi)
    return Chem.MolToSmiles(m) if m is not None else smi


def ecreact_forms(mols, no_skeleton=False, canon=False):
    """Map molecules to ECReact spellings. Returns (mapping, how, fallback)."""
    mols = set(mols)
    mkeys = {m: keys(m) for m in mols}
    want = [{k[i] for k in mkeys.values() if k[i]} for i in range(2)]
    ec = pd.read_csv(ECREACT, usecols=["rxn_smiles"])
    counts = collections.Counter(m for r in ec["rxn_smiles"] for side in r.split(">>") for m in side.split("."))
    luts = [{}, {}]
    want_skel = set() if no_skeleton else {skeleton(m) for m in mols} - {None}
    lut_skel = {}
    for m, _ in counts.most_common():
        k = keys(m)
        for i in range(2):
            if k[i] in want[i] and k[i] not in luts[i]:
                luts[i][k[i]] = m
        if want_skel:
            sk = skeleton(m)
            if sk in want_skel and sk not in lut_skel:
                lut_skel[sk] = m

    mapping, how, fallback = {}, {}, {}
    for m in mols:
        k = mkeys[m]
        has_stereo = any(c in m for c in "@/\\")
        if m in counts:
            mapping[m], how[m] = m, "exact"
        elif k[0] in luts[0]:
            mapping[m], how[m] = luts[0][k[0]], "neutral"
        elif not has_stereo and k[1] in luts[1]:
            mapping[m], how[m] = luts[1][k[1]], "nostereo"
        elif (sk := skeleton(m)) in lut_skel:
            mapping[m], how[m], fallback[m] = lut_skel[sk], "skeleton", ionize(m)
        else:
            mapping[m], how[m] = ionize(m), "ionized"
            if canon:
                mapping[m] = canonical(mapping[m])
    return mapping, how, fallback


def map_reaction(r, mapping, how, fallback, drop=(), keep_order=False, reverted=None):
    """Map every participant; revert skeleton matches that would merge two participants; sort each side."""
    parts = [side.split(".") for side in r.split(">>")]
    flat = [m for side in parts for m in side]
    use = dict(mapping)
    for _ in range(len(flat)):
        seen = collections.defaultdict(list)
        for m in flat:
            seen[use[m]].append(m)
        clash = [ms for ms in seen.values() if len(set(ms)) > 1]
        if not clash:
            break
        changed = False
        for ms in clash:
            for m in ms:
                if how[m] == "skeleton" and use[m] != fallback[m]:
                    use[m] = fallback[m]
                    if reverted is not None:
                        reverted[m] += 1
                    changed = True
        if not changed:
            break
    out = []
    for side in parts:
        got = [use[m] for m in side]
        if drop:
            got = [m for m in got if m not in drop] or got   # never empty a side
        out.append(".".join(got if keep_order else sorted(got)))   # ECReact sorts each side alphabetically
    return ">>".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=SRC, help="input split dir with seed*/test.csv")
    ap.add_argument("--out", type=Path, default=OUT, help="output split dir")
    ap.add_argument("--no_skeleton", action="store_true", help="disable rule 4 (skeleton match)")
    ap.add_argument("--canonical", action="store_true", help="RDKit-canonicalise molecules mapped by rule 5")
    ap.add_argument("--drop_species", default="", help="comma-separated species to remove from both sides")
    ap.add_argument("--keep_order", action="store_true", help="keep the source participant order")
    args = ap.parse_args()
    drop = {x.strip() for x in args.drop_species.split(",") if x.strip()}
    seeds = sorted(int(d.name[4:]) for d in args.src.glob("seed*") if (d / "test.csv").exists())
    print(f"{args.src} -> {args.out}  seeds {seeds}")
    bench = {s: pd.read_csv(args.src / f"seed{s}" / "test.csv", dtype=str) for s in seeds}
    mols = {m for d in bench.values() for r in d["rxn_smiles"] for side in r.split(">>") for m in side.split(".")}
    mapping, how, fallback = ecreact_forms(mols, args.no_skeleton, args.canonical)
    reverted = collections.Counter()
    for s, d in bench.items():
        d = d.copy()
        d["rxn_smiles"] = d["rxn_smiles"].map(
            lambda r: map_reaction(r, mapping, how, fallback, drop, args.keep_order, reverted))
        (args.out / f"seed{s}").mkdir(parents=True, exist_ok=True)
        d.to_csv(args.out / f"seed{s}" / "test.csv", index=False)
    if reverted:
        print(f"skeleton matches reverted: {len(reverted)} molecules")
    pd.DataFrame({"bench": list(mapping), "ecreact_form": [mapping[m] for m in mapping],
                  "how": [how[m] for m in mapping]}).to_csv(args.out / "prep_log.csv", index=False)
    by = collections.Counter(how.values())
    print("molecules: " + ", ".join(f"{k} {v}" for k, v in by.most_common()))
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
