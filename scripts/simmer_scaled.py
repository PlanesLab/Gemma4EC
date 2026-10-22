"""
simmer_scaled.py — SIMMER (Holm/Bhattacharya-style reaction similarity EC predictor) with a
reference database built from a training set, re-implemented to scale to ~50K reference
reactions. Same algorithm as SIMMER2_generic.py + build_rhea_nocofactor_db.py
(ECNumberPrediction/methods/SIMMER), only the computation is vectorized:

  * reference fingerprints: RDKit difference fingerprint of ReactionFromSmarts(SMILES)
    (as build_rhea_nocofactor_db.py); query fingerprints: per-molecule SMILES -> SMARTS with
    'R' -> '*' first (as SIMMER2_generic.run_rxn);
  * similarity profile of a reaction = its Tanimoto similarities to all reference reactions;
    neighbours ranked by Euclidean distance between profiles (stable sort, as sorted());
  * per EC level (EC1 -> EC2 within significant EC1 -> EC3 within significant EC2), running
    enrichment walk over the ranked list (+1 same class, 0 NIL, -1 other), score = max / class
    count, p = (#null scores > score + 1) / (n_null + 1); significant if p < 0.05 and score > 0;
  * null: 1,000 shuffles of the reference EC labels, scored for each level's most frequent class.
    --null per_class (NOT the published method; sensitivity analysis): a separate null for every
    class, scored for that class itself. SIMMER's single modal-class null is miscalibrated when one
    class dominates the database (e.g. EC 2 = 56% of ECReact): its walk drifts upwards under
    shuffling, so the threshold is too high for every other class and they are never called.

Modes
  default : profiles over reference columns only; other queries are not part of the ranking
            (batch-independent — a query's answer does not depend on the other queries).
  --exact : reproduce SIMMER2_generic exactly — queries are appended to the matrix as extra rows
            and columns (NIL label) — for validation against the original implementation.

Output TSV: query_id, rxn_smiles, pred (';'-joined EC3 predictions, best first, 'NONE' if none).

Usage:
  python scripts/simmer_scaled.py --train train.csv --queries test.csv --out preds.tsv \
      [--smiles_col rxn_smiles --ec_col ec --id_col ID] [--perm_csv ec_perm.csv] [--exact] [--workers 16]
"""

import argparse
import multiprocessing as mp
import time

import numpy as np
import pandas as pd
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdChemReactions

RDLogger.DisableLog("rdApp.*")
_FPS = None  # reference fingerprints, shared with forked workers


def ref_fp(smiles):
    try:
        l, r = smiles.replace("->>", ">>").split(">>", 1)
        return rdChemReactions.CreateDifferenceFingerprintForReaction(
            rdChemReactions.ReactionFromSmarts(f"{l.strip()}>>{r.strip()}"))
    except Exception:
        return None


def query_fp(smiles):
    try:
        sides = []
        for side in smiles.replace("->>", ">>").split(">>", 1):
            sides.append(".".join(Chem.MolToSmarts(Chem.MolFromSmiles(m.replace("R", "*")), isomericSmiles=True)
                                  for m in side.split(".")))
        return rdChemReactions.CreateDifferenceFingerprintForReaction(
            rdChemReactions.ReactionFromSmarts(sides[0] + ">>" + sides[1]))
    except Exception:
        return None


def _rows(args):
    fps, start, stop, dtype = args
    return start, np.array([DataStructs.BulkTanimotoSimilarity(fps[i], _FPS) for i in range(start, stop)],
                           dtype=dtype)


def tanimoto_rows(row_fps, ref_fps, workers, chunk=256, dtype=np.float32):
    """Tanimoto similarities of row_fps (list) against ref_fps -> float32 [len(row_fps), len(ref_fps)]."""
    global _FPS
    _FPS = ref_fps
    out = np.empty((len(row_fps), len(ref_fps)), dtype=dtype)
    jobs = [(row_fps, s, min(s + chunk, len(row_fps)), dtype) for s in range(0, len(row_fps), chunk)]
    if workers > 1:
        with mp.get_context("fork").Pool(workers) as pool:
            for s, block in pool.imap_unordered(_rows, jobs):
                out[s:s + len(block)] = block
    else:
        for job in jobs:
            s, block = _rows(job)
            out[s:s + len(block)] = block
    return out


def ec_levels(ec):
    p = str(ec).split(".")
    return [".".join(p[:k]) for k in (1, 2, 3)] + [str(ec)]


def walk_scores(labels, cat):
    """Enrichment walk over a ranked label array: returns (max tally, first argmax)."""
    steps = np.where(labels == cat, 1, np.where(labels == "NIL", 0, -1))
    tally = np.cumsum(steps)
    i = int(np.argmax(tally))
    return int(tally[i]), i


def build_null(ref_ec, n_perm, seed):
    """As build_ec_permutations: per level, shuffled reference labels scored for the modal class."""
    rng = np.random.default_rng(seed)
    lv = np.array([ec_levels(e) for e in ref_ec])
    null = {}
    for k, name in enumerate(["EC1", "EC2", "EC3", "EC4"]):
        col = lv[:, k]
        rep = pd.Series(col).mode().iloc[0]
        denom = (col == rep).sum()
        null[name] = [walk_scores(rng.permutation(col), rep)[0] / denom for _ in range(n_perm)]
    return null


def build_null_per_class(ref_ec, n_perm, seed, block=250):
    """Per-class null: for each level and class, shuffled labels scored for that class. The null of a
    class only depends on its count k among n labels, so it is computed once per distinct count."""
    rng = np.random.default_rng(seed)
    lv = np.array([ec_levels(e) for e in ref_ec])
    n = len(lv)
    by_count, null = {}, {}
    for k, name in enumerate(["EC1", "EC2", "EC3"]):
        null[name] = {}
        for cat, cnt in pd.Series(lv[:, k]).value_counts().items():
            if cnt not in by_count:
                base = np.full(n, -1, dtype=np.int8)
                base[:cnt] = 1
                scores = []
                for b in range(0, n_perm, block):
                    m = rng.permuted(np.tile(base, (min(block, n_perm - b), 1)), axis=1)
                    scores.append(np.cumsum(m, axis=1, dtype=np.int32).max(axis=1) / cnt)
                by_count[cnt] = np.concatenate(scores)
            null[name][cat] = by_count[cnt]
    print(f"[null] per-class nulls for {sum(len(v) for v in null.values())} classes "
          f"({len(by_count)} distinct counts)", flush=True)
    return null


def significant(cats, labels, counts, null):
    rows = []
    for cat in cats:
        if cat in ("NIL", "DM"):
            continue
        es, where = walk_scores(labels, cat)
        es_norm = es / counts[cat]
        nl = null[cat] if isinstance(null, dict) else null
        p = (np.sum(np.asarray(nl) > es_norm) + 1) / (len(nl) + 1)
        if p < 0.05 and es_norm > 0:
            rows.append((cat, es_norm, p, where))
    return sorted(rows, key=lambda r: r[3])


def predict_one(order, lab):
    """lab: dict level -> label array in reference order (+ NIL tail); order: ranked indices."""
    ranked = {k: v[order] for k, v in lab.items()}
    counts = {k: pd.Series(v).value_counts().to_dict() for k, v in ranked.items()}
    s1 = significant(pd.unique(ranked["EC1"]), ranked["EC1"], counts["EC1"], NULL["EC1"])
    if not s1:
        return []
    m1 = np.isin(ranked["EC1"], [r[0] for r in s1])
    s2 = significant(pd.unique(ranked["EC2"][m1]), ranked["EC2"], counts["EC2"], NULL["EC2"])
    if not s2:
        return []
    m2 = np.isin(ranked["EC2"], [r[0] for r in s2])
    s3 = significant(pd.unique(ranked["EC3"][m2]), ranked["EC3"], counts["EC3"], NULL["EC3"])
    return [r[0] for r in s3]


NULL = None


def main():
    global NULL
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--queries", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--smiles_col", default="rxn_smiles")
    ap.add_argument("--ec_col", default="ec")
    ap.add_argument("--id_col", default=None, help="query id column (default: row index)")
    ap.add_argument("--perm_csv", default=None, help="use an existing SIMMER ec_perm.csv as the null")
    ap.add_argument("--n_perm", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--exact", action="store_true")
    ap.add_argument("--null", choices=["modal", "per_class"], default="modal",
                    help="modal = published SIMMER; per_class = separate null per class (sensitivity analysis)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--batch", type=int, default=512)
    args = ap.parse_args()
    sep = lambda p: "\t" if p.endswith(".tsv") else ","
    t0 = time.time()

    tr = pd.read_csv(args.train, sep=sep(args.train), dtype=str)
    tr = tr[tr[args.ec_col].notna() & (tr[args.ec_col].str.lower() != "nan")].reset_index(drop=True)
    rfps = [ref_fp(s) for s in tr[args.smiles_col]]
    keep = [i for i, f in enumerate(rfps) if f is not None]
    rfps = [rfps[i] for i in keep]
    ref_ec = tr[args.ec_col].iloc[keep].str.strip().tolist()
    print(f"[ref] {len(rfps)} reference reactions ({len(tr) - len(rfps)} unparsable dropped)", flush=True)

    q = pd.read_csv(args.queries, sep=sep(args.queries), dtype=str)
    qid = q[args.id_col].tolist() if args.id_col else [str(i) for i in range(len(q))]
    qfps = [query_fp(s) for s in q[args.smiles_col]]
    ok = [i for i, f in enumerate(qfps) if f is not None]
    print(f"[query] {len(q)} queries, {len(q) - len(ok)} unparsable (-> NONE)", flush=True)

    dt = np.float64 if args.exact else np.float32
    T = tanimoto_rows(rfps, rfps, args.workers, dtype=dt)                       # [n, n]
    QT = tanimoto_rows([qfps[i] for i in ok], rfps, args.workers, dtype=dt)     # [Q, n]
    print(f"[tanimoto] done in {time.time() - t0:.0f}s", flush=True)

    if args.null == "per_class":
        NULL = build_null_per_class(ref_ec, args.n_perm, args.seed)
    elif args.perm_csv:
        pdf = pd.read_csv(args.perm_csv)
        NULL = {c: pdf[c].dropna().tolist() for c in ["EC1", "EC2", "EC3", "EC4"] if c in pdf}
    else:
        NULL = build_null(ref_ec, args.n_perm, args.seed)

    lv = np.array([ec_levels(e) for e in ref_ec])
    preds = {}
    if args.exact:
        # SIMMER2_generic: queries appended as rows and columns; queries rank as NIL rows
        QQ = tanimoto_rows([qfps[i] for i in ok], [qfps[i] for i in ok], args.workers, dtype=dt)
        X = np.block([[T, QT.T], [QT, QQ]]).astype(np.float64)
        n = len(rfps)
        lab = {f"EC{k + 1}": np.concatenate([lv[:, k], np.array(["NIL"] * len(ok))]) for k in range(3)}
        sq = (X ** 2).sum(1)
        for j, i in enumerate(ok):
            d2 = sq + sq[n + j] - 2 * X @ X[n + j]
            order = np.argsort(np.sqrt(np.maximum(d2, 0)), kind="stable")
            order = order[order != n + j]
            preds[i] = predict_one(order, lab)
    else:
        lab = {f"EC{k + 1}": lv[:, k] for k in range(3)}
        # float32 matmul: a 46K x 46K float64 copy would not fit; ranking is unaffected in practice
        Tsq = (T ** 2).sum(1)
        for b in range(0, len(ok), args.batch):
            Qb = QT[b:b + args.batch]
            d2 = (Qb ** 2).sum(1)[:, None] + Tsq[None, :] - 2 * (Qb @ T.T)
            for r, i in enumerate(ok[b:b + args.batch]):
                order = np.argsort(np.sqrt(np.maximum(d2[r], 0)), kind="stable")
                preds[i] = predict_one(order, lab)
            print(f"[predict] {min(b + args.batch, len(ok))}/{len(ok)} ({time.time() - t0:.0f}s)", flush=True)

    out = pd.DataFrame({"query_id": qid, "rxn_smiles": q[args.smiles_col],
                        "pred": [";".join(preds.get(i, [])) or "NONE" for i in range(len(q))]})
    out.to_csv(args.out, sep="\t", index=False)
    print(f"[done] {args.out} in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
