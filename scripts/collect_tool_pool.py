"""
collect_tool_pool.py — Gather SIMMER / SelenzymeRF chunk results on the deduplicated pool
(slurm/seeds/run_tool_{simmer,selenzyme}.sh) and write one prediction TSV per seed:
    <work_root>/seed{S}/tools/{SIMMER,SelenzymeRF}_predictions.tsv
(columns true_label, pred, smiles; row-aligned with that seed's test.csv), which
results/seeds/compute_seed_metrics.py picks up. Pending reactions are written empty.

Usage: python scripts/collect_tool_pool.py [--work_root DIR]
"""

import argparse
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SPLIT_SET = os.environ.get("SPLIT_SET", "strat_dedup")  # which seed split set (data/ECReact_seeds_<set>)
SEEDS_DIR = ROOT / "data" / f"ECReact_seeds_{SPLIT_SET}"
TOOLS = {  # name: (subdir, id column, prediction column)
    "SIMMER": ("simmer", "Reaction name", "SIMMER pred"),
    "SelenzymeRF": ("selenzyme", "Reaction", "All ECs"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work_root", type=Path, default=Path(os.environ.get("GEMMA4EC_WORK", "work")) / f"seeds_{SPLIT_SET}")
    ap.add_argument("--reuse_from", nargs="*", default=[],
                    help="Other split sets whose tool results are reused (matched by reaction SMILES).")
    args = ap.parse_args()
    pool = pd.read_csv(SEEDS_DIR / "api_pool.csv", dtype=str)
    # (pool csv the Q ids refer to, tool results root): this split set's own run, which may
    # have been made on a todo subset (tool_todo.csv), plus any reused split sets
    sources = [(SEEDS_DIR / ("tool_todo.csv" if (SEEDS_DIR / "tool_todo.csv").exists() else "api_pool.csv"), args.work_root)]
    for other in args.reuse_from:
        sources.append((ROOT / "data" / f"ECReact_seeds_{other}" / "api_pool.csv",
                        Path(os.environ.get("GEMMA4EC_WORK", "work")) / f"seeds_{other}"))

    for name, (sub, id_col, pred_col) in TOOLS.items():
        by_smiles = {}
        for src_csv, root in sources:
            chunks = sorted((root / "tools" / sub).glob("chunk_*.csv"))
            if not chunks or not src_csv.exists():
                continue
            src = pd.read_csv(src_csv, dtype=str)
            res = pd.concat([pd.read_csv(c, dtype=str, keep_default_na=False) for c in chunks])
            res = res[res[id_col].str.match(r"^Q\d+$")]
            for i, p in zip(res[id_col].str[1:].astype(int), res[pred_col]):
                if i < len(src):
                    by_smiles.setdefault(src.at[i, "rxn_smiles"], p)
        by_idx = {i: by_smiles[s] for i, s in enumerate(pool["rxn_smiles"]) if s in by_smiles}
        answered = sum(1 for p in by_idx.values() if p)
        print(f"[{name}] {len(by_idx)}/{len(pool)} pool reactions returned, {answered} with ≥1 EC")
        if not by_idx:
            continue

        for test_csv in sorted(SEEDS_DIR.glob("seed*/test.csv")):
            test = pd.read_csv(test_csv, dtype=str)
            # A tool answering "no EC" (or unable to parse a reaction) is a real outcome, scored
            # as a miss: write NONE so it isn't mistaken for a not-yet-run (empty) row.
            done = len(by_idx) >= len(pool) * 0.95
            out = pd.DataFrame({"true_label": test["ec"],
                                "pred": [by_smiles.get(s) or ("NONE" if done else "") for s in test["rxn_smiles"]],
                                "smiles": test["rxn_smiles"]})
            dst = args.work_root / test_csv.parent.name / "tools" / f"{name}_predictions.tsv"
            dst.parent.mkdir(parents=True, exist_ok=True)
            out.to_csv(dst, sep="\t", index=False)


if __name__ == "__main__":
    main()
