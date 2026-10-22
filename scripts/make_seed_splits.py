"""
make_seed_splits.py — The 10 deduplicated, EC-stratified ECReact splits used in the benchmark.

By default it rebuilds every seed's train/val/test CSVs from the published assignment table
data/ECReact_strat_dedup_splits.csv.gz (one row per reaction-EC pair; columns rxn_smiles, ec,
seed0 ... seed9, each holding train / val / test). Nothing else is needed:

    python scripts/make_seed_splits.py          # -> data/ECReact_seeds_strat_dedup/seed{0..9}/

With --from_ecreact DIR the splits are recomputed from the raw ECReact train/val/test CSVs in
DIR (columns rxn_smiles, ec) and the assignment table is rewritten; this needs RDKit. The
splits are built as follows:

  * reactions are identified by their RDKit-canonical reaction SMILES;
  * exact duplicates (same reaction and same EC) are dropped;
  * every row of a reaction goes to the same split, so no reaction appears in both train and
    test (a reaction with several ECs keeps all of them);
  * reactions are split 80/10/10 within each EC sub-subclass (EC3; for a reaction with several
    ECs, its most frequent EC3). Sub-subclasses with fewer than 3 reactions go entirely to
    train; every other one gets at least one reaction in val and in test.

Output: data/ECReact_seeds_strat_dedup/seed{S}/{train,val,test}.csv and manifest.csv
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "ECReact_strat_dedup_splits.csv.gz"
OUT = ROOT / "data" / "ECReact_seeds_strat_dedup"
SPLITS = ("train", "val", "test")


def ec3(ec):
    return ".".join(str(ec).split(".")[:3])


def dedup(pool):
    """Drop duplicate (reaction, EC) pairs and give each reaction one stratification label."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from canonicalize_smiles import canon_rxn
    pool = pool.copy()
    pool["key"] = pool["rxn_smiles"].map(canon_rxn)
    pool = pool.drop_duplicates(["key", "ec"]).reset_index(drop=True)
    # one label per reaction: its most frequent EC3 (ties -> first seen)
    label = pool.assign(e3=pool["ec"].map(ec3)).groupby("key")["e3"].agg(lambda s: s.value_counts().index[0])
    return pool, label


def split_strat(label, seed):
    """Assign each reaction to train/val/test, stratified within its EC3."""
    rng = np.random.default_rng(seed)
    assign = {}
    for _, keys in label.groupby(label).groups.items():
        keys = list(keys)
        rng.shuffle(keys)
        n = len(keys)
        n_te = n_va = max(1, int(0.1 * n + 0.5)) if n >= 3 else 0
        for i, k in enumerate(keys):
            assign[k] = "test" if i < n_te else "val" if i < n_te + n_va else "train"
    return assign


def build_table(src, seeds):
    parts = [pd.read_csv(src / f"{s}.csv", dtype=str) for s in SPLITS]
    pool = pd.concat(parts, ignore_index=True)
    print(f"Pooled {len(pool)} rows from {src}")
    pool, label = dedup(pool)
    print(f"After dedup: {len(pool)} rows, {pool['key'].nunique()} unique reactions, "
          f"{label.nunique()} EC3 classes ({(label.value_counts() < 3).sum()} with < 3 reactions -> train only)")
    for seed in seeds:
        pool[f"seed{seed}"] = pool["key"].map(split_strat(label, seed))
    table = pool[["rxn_smiles", "ec"] + [f"seed{s}" for s in seeds]]
    table.to_csv(TABLE, index=False, compression="gzip")
    print(f"Wrote {TABLE} ({len(table)} rows)")
    return table


def write_splits(table, seeds):
    rows = []
    for seed in seeds:
        col = f"seed{seed}"
        if col not in table.columns:
            sys.exit(f"{TABLE} has no column {col}")
        out = OUT / f"seed{seed}"
        out.mkdir(parents=True, exist_ok=True)
        for split in SPLITS:
            df = table[table[col] == split]
            df[["rxn_smiles", "ec"]].to_csv(out / f"{split}.csv", index=False)
            rows.append({"seed": seed, "split": split, "n_rows": len(df),
                         "n_reactions": df["rxn_smiles"].nunique(), "n_ec3": df["ec"].map(ec3).nunique()})
        print(f"seed{seed}: " + ", ".join(f"{r['split']} {r['n_rows']}" for r in rows[-3:]))
    pd.DataFrame(rows).to_csv(OUT / "manifest.csv", index=False)
    print(f"Wrote {OUT}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from_ecreact", type=Path, default=None,
                    help="Raw ECReact directory with train/val/test.csv: recompute the splits (needs RDKit)")
    ap.add_argument("--seeds", type=int, nargs="+", default=list(range(10)))
    args = ap.parse_args()

    if args.from_ecreact:
        table = build_table(args.from_ecreact, args.seeds)
    elif TABLE.exists():
        table = pd.read_csv(TABLE, dtype=str)
    else:
        sys.exit(f"{TABLE} not found — pass --from_ecreact <dir with the raw ECReact CSVs>")
    write_splits(table, args.seeds)


if __name__ == "__main__":
    main()
