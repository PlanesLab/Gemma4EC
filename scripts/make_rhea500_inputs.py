#!/usr/bin/env python3
"""Rhea500 inputs: 10 bootstrap samples of 500 reactions from $ECN_ROOT/data/Splits-Rhea/master.tsv
(uniform, with replacement), EC7 dropped, deduplicated per sample.

Writes data/ECReact_seeds_rhea500/seed{S}/test.csv (reaction_id, rxn_smiles, ec).
Usage: python scripts/make_rhea500_inputs.py [--n 500] [--seeds 10]
"""

import argparse
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ecn_root", default=os.environ.get("ECN_ROOT", ""))
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--out", default=str(ROOT / "data" / "ECReact_seeds_rhea500"))
    args = ap.parse_args()

    pool = pd.read_csv(Path(args.ecn_root) / "data/Splits-Rhea/master.tsv", sep="\t", dtype=str).dropna()
    pool = pool.rename(columns={"REACTION_ID": "reaction_id", "REACTION_SMILES": "rxn_smiles",
                                "EC_NUMBER": "ec"})
    before = len(pool)
    pool = pool[~pool.ec.str.startswith("7.")].reset_index(drop=True)
    print(f"pool {before} reactions, {before - len(pool)} EC 7 dropped, {len(pool)} usable")

    for s in range(args.seeds):
        d = pool.sample(n=args.n, replace=True, random_state=s)
        d = d.drop_duplicates("reaction_id").reset_index(drop=True)
        out = Path(args.out) / f"seed{s}"
        out.mkdir(parents=True, exist_ok=True)
        d[["reaction_id", "rxn_smiles", "ec"]].to_csv(out / "test.csv", index=False)
        print(f"  seed{s}: {len(d)} unique reactions, {d.ec.str[:5].nunique()} EC3 classes -> {out}")


if __name__ == "__main__":
    main()
