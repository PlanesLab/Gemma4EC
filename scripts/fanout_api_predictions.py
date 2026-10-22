"""
fanout_api_predictions.py — Copy deduplicated API pool predictions into every seed.

Reads <work_root>/api_pool/predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API.<model>.tsv
(row-aligned with data/ECReact_seeds/api_pool.csv) and writes, for each seed, a TSV with
the same name under <work_root>/seed{S}/api/, row-aligned with that seed's test.csv and
carrying the seed's own true labels. Reactions not yet predicted are written with an
empty prediction (scored as misses; compute_seed_metrics.py reports coverage).

Usage:
    python scripts/fanout_api_predictions.py [--models gpt-5_2 ...] [--work_root DIR]
"""

import argparse
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SPLIT_SET = os.environ.get("SPLIT_SET", "strat_dedup")  # which seed split set (data/ECReact_seeds_<set>)
SEEDS_DIR = ROOT / "data" / f"ECReact_seeds_{SPLIT_SET}"
TSV_PREFIX = "predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", help="Model IDs with '.'→'_' (default: all in the pool dir)")
    ap.add_argument("--work_root", type=Path, default=Path(os.environ.get("GEMMA4EC_WORK", "work")) / f"seeds_{SPLIT_SET}")
    args = ap.parse_args()

    pool = pd.read_csv(SEEDS_DIR / "api_pool.csv", dtype=str)
    pool_dir = args.work_root / "api_pool"
    files = ([pool_dir / f"{TSV_PREFIX}{m}.tsv" for m in args.models] if args.models
             else sorted(pool_dir.glob(f"{TSV_PREFIX}*.tsv")))

    for f in files:
        pred = pd.read_csv(f, sep="\t", dtype=str, keep_default_na=False)
        assert len(pred) == len(pool), f"{f.name}: {len(pred)} rows, pool has {len(pool)}"
        wf = pred["pred_well_formed"].str.lower() == "true"
        answered = pred["status"].isin(["OK", "ERROR_PARSE", "REUSED_ORIGINAL_TEST"]) | wf
        by_smiles = {s: r for s, r, a in zip(pool["rxn_smiles"], pred.to_dict("records"), answered) if a}

        for test_csv in sorted(SEEDS_DIR.glob("seed*/test.csv")):
            test = pd.read_csv(test_csv, dtype=str)
            recs = [by_smiles.get(s, {}) for s in test["rxn_smiles"]]
            out = pd.DataFrame({
                "true_label": test["ec"],
                "pred_raw": [r.get("pred_raw", "") for r in recs],
                "pred_fragment": [r.get("pred_fragment", "") for r in recs],
                "pred_well_formed": [r.get("pred_well_formed", "False") for r in recs],
                "smiles": test["rxn_smiles"],
                "n_attempts": [r.get("n_attempts", "0") for r in recs],
                "status": [r.get("status", "PENDING") for r in recs],
            })
            dst = args.work_root / test_csv.parent.name / "api" / f.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            out.to_csv(dst, sep="\t", index=False)
        print(f"[fanout] {f.name}: {answered.sum()}/{len(pool)} pool reactions answered → {len(list(SEEDS_DIR.glob('seed*/test.csv')))} seeds")


if __name__ == "__main__":
    main()
