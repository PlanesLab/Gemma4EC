"""ECReact 10-seed benchmark metrics: support-weighted EC3 MCC / precision / recall per method and seed.

Predictions are aligned to each seed's test rows by (reaction SMILES, true EC); missing rows count as misses.
Few-shot examples used by the API prompt are excluded for all methods. Only the methods shown in the figures
are written, under their figure names.

Writes results/seeds_strat_dedup/{seed_metrics,seed_summary,per_class_metrics,level_metrics}.csv.
Usage: python results/seeds/compute_seed_metrics.py [--seeds 0 ... 9] [--work_root DIR]
"""

import argparse
import os
import re
import warnings
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import matthews_corrcoef, precision_score, recall_score
from sklearn.preprocessing import MultiLabelBinarizer

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
SPLIT_SET = os.environ.get("SPLIT_SET", "strat_dedup")  # which seed split set
ROOT = HERE.parent.parent
METRICS = ["mcc", "ppv", "recall"]
# method as scored -> figure name; methods not listed are not written
LABELS = {
    "Gemma4EC-9b": "Gemma4EC-9B", "Gemma4EC-2b": "Gemma4EC-2B", "BEC-Pred": "BEC-Pred", "Theia": "Theia",
    "CLAIRE": "CLAIRE", "SelenzymeRF": "SelenzymeRF", "SIMMER (train+val DB, per-class null)": "SIMMER",
    "Gemini-3.1-flash-lite": "Gemini", "ChatGPT-4.1-mini": "GPT",
}


def label(d):
    d = d[d["method"].isin(LABELS)].copy()
    d["method"] = d["method"].map(LABELS)
    return d

# Display names for API model IDs (file names use '_' for '.')
API_NAMES = {
    "gpt-4_1-mini": "ChatGPT-4.1-mini",
    "gpt-5_1": "ChatGPT-5.1",
    "gpt-5_2": "ChatGPT-5.2",
    "gemini-2_5-flash": "Gemini-2.5-flash",
    "gemini-3_1-flash-lite": "Gemini-3.1-flash-lite",
    "gpt-6-luna": "ChatGPT-6-luna",
}


def parse_ecs(s):
    """Set of normalised 3-part ECs from the first ';'-group ('2.03.01' → '2.3.1')."""
    ecs = set()
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ecs
    for ec in str(s).split(";")[0].split("|"):
        parts = ec.strip().split(".")
        if len(parts) >= 3 and all(p.isdigit() for p in parts[:3]):
            norm = ".".join(str(int(p)) for p in parts[:3])
            if norm.split(".")[0] in "1234567":
                ecs.add(norm)
    return ecs


def label_key(s):
    return "|".join(sorted(parse_ecs(s)))


def newest(paths):
    paths = sorted(paths, key=lambda p: p.stat().st_mtime)
    return paths[-1] if paths else None


def locate(work):
    """{method: (path, loader)} for every prediction file found for one seed."""
    found = {}

    def add(name, path, loader):
        if path is not None and path.exists():
            found[name] = (path, loader)

    add("Gemma4EC-9b", newest(work.glob("gemma4ec_9b/results/predictions_test.*.tsv"))
        or newest(work.glob("gemma4ec_9b/predict_best/predictions_pred.*.tsv")), "tsv_fragment")   # runs killed after training
    add("Gemma4EC-2b", newest(work.glob("gemma4ec_2b/results/predictions_test.*.tsv"))
        or newest(work.glob("gemma4ec_2b/predict_best/predictions_pred.*.tsv")), "tsv_fragment")   # runs killed after training
    add("TxGemma-9b (no FT)", newest(work.glob("txgemma_noft/zeroshot_test_*.tsv")), "tsv_pred")
    add("Theia", work / "theia/test_predictions.tsv", "tsv_pred")
    add("BEC-Pred", work / "becpred/Results/results_test_ec.csv", "becpred")
    add("CLAIRE", work / "claire/CLAIRE.csv", "claire")
    add("SIMMER", work / "tools/SIMMER_predictions.tsv", "tsv_pred")
    add("SelenzymeRF", work / "tools/SelenzymeRF_predictions.tsv", "tsv_pred")
    add("SIMMER (train DB)", work / "tools/SIMMER_trainDB_predictions.tsv", "tsv_pred")
    add("SIMMER (train DB, per-class null)", work / "tools/SIMMER_trainDB_perclass_predictions.tsv", "tsv_pred")
    add("SelenzymeRF (train DB)", work / "tools/SelenzymeRF_trainDB_predictions.tsv", "tsv_pred")
    add("SIMMER (train+val DB)", work / "tools/SIMMER_trainvalDB_predictions.tsv", "tsv_pred")
    add("SIMMER (train+val DB, per-class null)", work / "tools/SIMMER_trainvalDB_perclass_predictions.tsv", "tsv_pred")
    add("SelenzymeRF (train+val DB)", work / "tools/SelenzymeRF_trainvalDB_predictions.tsv", "tsv_pred")
    for p in work.glob("api/predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API.*.tsv"):
        model_id = re.sub(r"^predictions_pred\.EC_NUMBER\.EC_NUMBER_PROMPT_API\.|\.tsv$", "", p.name)
        add(API_NAMES.get(model_id, model_id.replace("_", ".")), p, "tsv_fragment")
    return found


def align(test, path, loader):
    """Return (list of prediction strings aligned to test rows, coverage)."""
    n = len(test)
    if loader == "claire":
        df = pd.read_csv(path, dtype=str)
        pred = [""] * n
        for rid, p in zip(df["reactionID"], df["predictions"]):
            if str(rid).isdigit() and int(rid) < n:
                pred[int(rid)] = p
        return pred, float(np.mean([p != "" for p in pred]))

    if loader == "becpred":
        df = pd.read_csv(path, dtype=str)
        # eval_model.py keeps test.csv row order; its Reaction column holds the
        # RDKit-canonicalized SMILES, so align by position when the row count matches
        if len(df) == n:
            return df["Prediction"].fillna("").tolist(), 1.0
        smiles, labels, preds = df["Reaction"], [None] * len(df), df["Prediction"]
    else:
        df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
        col = "pred_fragment" if loader == "tsv_fragment" else "pred"
        smiles, labels, preds = df["smiles"], df["true_label"], df[col]

    # Queue predictions per (smiles, label); DDP eval may reorder / pad rows
    queues = defaultdict(deque)
    for s, l, p in zip(smiles, labels, preds):
        queues[(str(s).strip(), None if l is None else label_key(l))].append(p)
    pred = []
    for s, ec in zip(test["rxn_smiles"], test["ec"]):
        q = queues.get((s.strip(), label_key(ec))) or queues.get((s.strip(), None))
        pred.append(q.popleft() if q else "")
    # coverage = test rows with an answer (API fan-out writes empty rows for pending reactions)
    return pred, float(np.mean([str(p).strip() != "" for p in pred]))


def weighted_metrics(true_sets, pred_sets, mlb):
    y_true, y_pred = mlb.transform(true_sets), mlb.transform(pred_sets)
    support = y_true.sum(axis=0)
    mcc = [matthews_corrcoef(y_true[:, i], y_pred[:, i]) for i in range(y_true.shape[1])]
    prec = precision_score(y_true, y_pred, average=None, zero_division=0)
    rec = recall_score(y_true, y_pred, average=None, zero_division=0)
    return {
        "mcc": float(np.average(mcc, weights=support)),
        "ppv": float(np.average(prec, weights=support)),
        "recall": float(np.average(rec, weights=support)),
    }


EXTRA = {"per_class": [], "levels": []}  # filled by score_seed, written by main


def per_label(ts, ps, mlb):
    y_true, y_pred = mlb.transform(ts), mlb.transform(ps)
    support = y_true.sum(axis=0)
    mcc = np.array([matthews_corrcoef(y_true[:, i], y_pred[:, i]) for i in range(y_true.shape[1])])
    prec = precision_score(y_true, y_pred, average=None, zero_division=0)
    rec = recall_score(y_true, y_pred, average=None, zero_division=0)
    return mcc, prec, rec, support


def truncate(sets, level):
    return [{".".join(l.split(".")[:level]) for l in s} for s in sets]


def score_seed(seed, data_root, work_root):
    test = pd.read_csv(data_root / f"seed{seed}" / "test.csv", dtype=str)
    true_sets = test["ec"].apply(parse_ecs).tolist()
    # The few-shot examples in EC_NUMBER_PROMPT_API are ECReact reactions; drop them from
    # scoring for every method so the API / TxGemma prompts never contain a test answer.
    excl_csv = data_root / "fewshot_examples_excluded.csv"
    excluded = set(pd.read_csv(excl_csv, dtype=str)["rxn_smiles"]) if excl_csv.exists() else set()
    keep = [i for i, t in enumerate(true_sets) if t and test.at[i, "rxn_smiles"] not in excluded]

    preds = {}
    for name, (path, loader) in locate(work_root / f"seed{seed}").items():
        pred, cov = align(test, path, loader)
        preds[name] = ([parse_ecs(pred[i]) for i in keep], cov)
    if not preds:
        return []

    ts = [true_sets[i] for i in keep]
    labels = sorted({l for s in ts for l in s} | {l for ps, _ in preds.values() for s in ps for l in s})
    mlb = MultiLabelBinarizer(classes=labels).fit([labels])

    rows = []
    for name, (ps, cov) in preds.items():
        m = weighted_metrics(ts, ps, mlb)
        rows.append({"method": name, "seed": seed, **m, "n_test": len(ts), "coverage": round(cov, 4)})
        flag = "" if cov > 0.99 else f"  ⚠ coverage {cov:.1%}"
        print(f"seed{seed}  {name:<22} MCC={m['mcc']:.3f} PPV={m['ppv']:.3f} Rec={m['recall']:.3f}{flag}")

        # per EC class (1-7): support-weighted metrics over that class's sub-subclasses

        mcc, prec, rec, sup = per_label(ts, ps, mlb)
        for cls in "1234567":
            idx = [i for i, l in enumerate(labels) if l.split(".")[0] == cls]
            if idx and sup[idx].sum() > 0:
                w = sup[idx]
                EXTRA["per_class"].append({"method": name, "seed": seed, "ec_class": cls, "support": int(w.sum()),
                                           "mcc": np.average(mcc[idx], weights=w), "ppv": np.average(prec[idx], weights=w),
                                           "recall": np.average(rec[idx], weights=w)})
        # hierarchy levels: class (EC1), subclass (EC2), sub-subclass (EC3)
        for level in (1, 2, 3):
            t_l, p_l = truncate(ts, level), truncate(ps, level)
            labs = sorted({l for s in t_l + p_l for l in s})
            lm = weighted_metrics(t_l, p_l, MultiLabelBinarizer(classes=labs).fit([labs]))
            EXTRA["levels"].append({"method": name, "seed": seed, "level": level, **lm})
    return rows


def summarize(df):
    rows = []
    for method, g in df.groupby("method"):
        r = {"method": method, "n_seeds": len(g), "min_coverage": g["coverage"].min()}
        for m in METRICS:
            x = g[m].values
            sd = x.std(ddof=1) if len(x) > 1 else np.nan
            half = stats.t.ppf(0.975, len(x) - 1) * sd / np.sqrt(len(x)) if len(x) > 1 else np.nan
            r.update({f"{m}_mean": x.mean(), f"{m}_sd": sd, f"{m}_ci_low": x.mean() - half, f"{m}_ci_high": x.mean() + half})
        rows.append(r)
    return pd.DataFrame(rows).sort_values("mcc_mean", ascending=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=list(range(10)))
    ap.add_argument("--data_root", type=Path, default=ROOT / "data" / f"ECReact_seeds_{SPLIT_SET}")
    ap.add_argument("--work_root", type=Path, default=Path(os.environ.get("GEMMA4EC_WORK", "work")) / f"seeds_{SPLIT_SET}")
    ap.add_argument("--out_dir", type=Path, default=HERE.parent / f"seeds_{SPLIT_SET}")
    ap.add_argument("--min_coverage", type=float, default=0.99,
                    help="Methods below this coverage in any seed are left out of the summary and tests.")
    args = ap.parse_args()

    df = pd.DataFrame([r for s in args.seeds for r in score_seed(s, args.data_root, args.work_root)])
    if df.empty:
        print("No predictions found.")
        return
    args.out_dir.mkdir(parents=True, exist_ok=True)
    label(df).to_csv(args.out_dir / "seed_metrics.csv", index=False, float_format="%.4f")
    label(pd.DataFrame(EXTRA["per_class"])).to_csv(args.out_dir / "per_class_metrics.csv", index=False, float_format="%.4f")
    label(pd.DataFrame(EXTRA["levels"])).to_csv(args.out_dir / "level_metrics.csv", index=False, float_format="%.4f")

    incomplete = sorted(df.loc[df["coverage"] < args.min_coverage, "method"].unique())
    df = df[~df["method"].isin(incomplete)]
    summary = label(summarize(df))
    summary.to_csv(args.out_dir / "seed_summary.csv", index=False, float_format="%.4f")
    print(summary[["method", "n_seeds", "mcc_mean", "mcc_sd"]].to_string(index=False, float_format="%.3f"))
    print(f"-> {args.out_dir}")


if __name__ == "__main__":
    main()
