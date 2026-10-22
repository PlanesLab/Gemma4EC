"""
collect_selenzyme_traindb.py — Per seed, merge the SelenzymeRF (train DB) chunk results
(<work>/seed{S}/tools/selenzyme_traindb/chunk_*.csv, ids Q<test row>) into
<work>/seed{S}/tools/SelenzymeRF_trainDB_predictions.tsv (true_label, pred, smiles), the file
results/seeds/compute_seed_metrics.py scores as "SelenzymeRF (train DB)". Reactions Selenzyme
returned without an EC are written as NONE (a miss).

Usage: SPLIT_SET=strat_dedup python scripts/collect_selenzyme_traindb.py
"""
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SPLIT_SET = os.environ.get("SPLIT_SET", "strat_dedup")
DB_SPLITS = os.environ.get("DB_SPLITS", "train")   # train | trainval
SUF, TAG = ("_trainval", "trainvalDB") if DB_SPLITS == "trainval" else ("", "trainDB")
SPLITS = ROOT / "data" / f"ECReact_seeds_{SPLIT_SET}"
WORK = Path(os.environ.get("GEMMA4EC_WORK", "work")) / f"seeds_{SPLIT_SET}"

for test_csv in sorted(SPLITS.glob("seed*/test.csv")):
    seed = test_csv.parent.name
    chunks = sorted((WORK / seed / "tools" / f"selenzyme_traindb{SUF}").glob("chunk_*.csv"))
    if not chunks:
        print(f"{seed}: no results yet")
        continue
    t = pd.read_csv(test_csv, dtype=str)
    res = pd.concat([pd.read_csv(c, dtype=str, keep_default_na=False) for c in chunks])
    by = dict(zip(res["Reaction"].str[1:].astype(int), res["All ECs"]))
    pred = [by[i] or "NONE" if i in by else "" for i in range(len(t))]
    out = WORK / seed / "tools" / f"SelenzymeRF_{TAG}_predictions.tsv"
    pd.DataFrame({"true_label": t["ec"], "pred": pred, "smiles": t["rxn_smiles"]}).to_csv(out, sep="\t", index=False)
    print(f"{seed}: {len(by)}/{len(t)} test reactions returned, {sum(1 for p in pred if p not in ('', 'NONE'))} with an EC")
