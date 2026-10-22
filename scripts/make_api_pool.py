"""
make_api_pool.py — Deduplicated reaction pool for API models in the seed benchmark.

API models are zero-shot, so a prediction depends only on the reaction SMILES, not on
the seed. Each unique reaction across the 10 seed test sets is therefore queried once
per model; scripts/fanout_api_predictions.py then copies the answers into every seed.

1. Writes data/ECReact_seeds/api_pool.csv (unique rxn_smiles over all seed test sets).
Usage (needs RDKit, e.g. the clean_ec env):
    python scripts/make_api_pool.py [--work_root $GEMMA4EC_WORK/seeds_<split>]
"""

import argparse
import os
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from canonicalize_smiles import canon_rxn  # noqa: E402

SPLIT_SET = os.environ.get("SPLIT_SET", "strat_dedup")  # which seed split set (data/ECReact_seeds_<set>)
SEEDS_DIR = ROOT / "data" / f"ECReact_seeds_{SPLIT_SET}"
POOL_CSV = SEEDS_DIR / "api_pool.csv"
TSV_PREFIX = "predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API."
COLS = ["true_label", "pred_raw", "pred_fragment", "pred_well_formed", "smiles", "n_attempts", "status"]


def build_pool():
    tests = sorted(SEEDS_DIR.glob("seed*/test.csv"))
    df = pd.concat([pd.read_csv(p, dtype=str) for p in tests], ignore_index=True)
    pool = df.drop_duplicates("rxn_smiles").reset_index(drop=True)
    pool.to_csv(POOL_CSV, index=False)
    print(f"[pool] {len(df)} test rows over {len(tests)} seeds → {len(pool)} unique reactions → {POOL_CSV}")
    return pool


def reuse(pool, out_dir, other):
    """Prefill this pool's TSVs with well-formed predictions from another split set's pool."""
    o_pool = pd.read_csv(ROOT / "data" / f"ECReact_seeds_{other}" / "api_pool.csv", dtype=str)
    o_dir = Path(os.environ.get("GEMMA4EC_WORK", "work")) / f"seeds_{other}" / "api_pool"
    out_dir.mkdir(parents=True, exist_ok=True)
    for o_tsv in sorted(o_dir.glob(f"{TSV_PREFIX}*.tsv")):
        prev = pd.read_csv(o_tsv, sep="\t", dtype=str, keep_default_na=False)
        prev["smiles_key"] = o_pool["rxn_smiles"].values[: len(prev)]
        prev = prev[prev["pred_well_formed"].str.lower() == "true"].set_index("smiles_key")
        target = out_dir / o_tsv.name
        if target.exists():
            cur = pd.read_csv(target, sep="\t", dtype=str, keep_default_na=False)
        else:
            cur = pd.DataFrame({c: [""] * len(pool) for c in COLS})
            cur["pred_well_formed"], cur["n_attempts"] = "False", "0"
        n = 0
        for i, s in enumerate(pool["rxn_smiles"]):
            if cur.at[i, "pred_well_formed"].lower() != "true" and s in prev.index:
                r = prev.loc[s] if not isinstance(prev.loc[s], pd.DataFrame) else prev.loc[s].iloc[0]
                for c in COLS:
                    cur.at[i, c] = r[c]
                cur.at[i, "true_label"], cur.at[i, "smiles"] = pool.at[i, "ec"], s
                n += 1
        cur[COLS].to_csv(target, sep="\t", index=False)
        done = (cur["pred_well_formed"].str.lower() == "true").sum()
        print(f"[reuse {other}] {o_tsv.name}: +{n} reused, {done}/{len(pool)} done")


def write_tool_todo(pool, other):
    o_pool = pd.read_csv(ROOT / "data" / f"ECReact_seeds_{other}" / "api_pool.csv", dtype=str)
    todo = pool[~pool["rxn_smiles"].isin(set(o_pool["rxn_smiles"]))].reset_index(drop=True)
    todo.to_csv(SEEDS_DIR / "tool_todo.csv", index=False)
    print(f"[tool_todo] {len(todo)} reactions not run by SIMMER/Selenzyme in {other} → {SEEDS_DIR / 'tool_todo.csv'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse_from", nargs="*", default=[],
                    help="Other split sets whose API pool predictions are reused (exact SMILES match).")
    ap.add_argument("--tool_todo_from", default=None,
                    help="Split set whose pool was already run by SIMMER/Selenzyme: write tool_todo.csv "
                         "with only this pool's reactions not in that pool.")
    ap.add_argument("--work_root", type=Path, default=Path(os.environ.get("GEMMA4EC_WORK", "work")) / f"seeds_{SPLIT_SET}")
    args = ap.parse_args()
    pool = build_pool()
    for other in args.reuse_from:
        reuse(pool, args.work_root / "api_pool", other)
    if args.tool_todo_from:
        write_tool_todo(pool, args.tool_todo_from)


if __name__ == "__main__":
    main()
