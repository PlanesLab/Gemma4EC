"""
compute_per_class.py — Recompute per-class benchmark table.

Produces one output file at the sub-subclass level (3-digit EC, e.g. 1.1.1):
  - summary/per_class_mcc.csv : per-EC-class weighted MCC for all models

Same shared-label-space methodology as compute_weighted_metrics.py.

Usage:
    cd results/
    python compute_per_class.py
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import matthews_corrcoef, precision_score, recall_score
from sklearn.preprocessing import MultiLabelBinarizer

warnings.filterwarnings("ignore")

RESULTS = Path(__file__).parent
SUMMARY = RESULTS / "summary"

# ---------------------------------------------------------------------------
# Model files (same as file1)
# ---------------------------------------------------------------------------

MODELS = {
    "ChatGPT-4.1-mini": RESULTS / "APIs/chatgpt-4_1-mini/test_predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API.gpt-4_1-mini.tsv",
    "ChatGPT-5.1":      RESULTS / "APIs/chatgpt-5_1/test_predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API.gpt-5_1.tsv",
    "ChatGPT-5.2":      RESULTS / "APIs/chatgpt-5_2/test_predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API.gpt-5_2.tsv",
    "Gemini-2.5-flash": RESULTS / "APIs/gemini-2_5-flash/test_predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API.gemini-2_5-flash.tsv",
    "TxGemma-9b":       RESULTS / "zeroshot/results/zeroshot_test_20260415-170538.tsv",
    "BEC-Pred":         RESULTS / "bec-pred/results_test_ec.csv",
    "Gemma4EC-2b":      RESULTS / "Gemma4EC-2b/2b_test_predictor_predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_2.d6i9pynh.tsv",
    "Gemma4EC-9b":      RESULTS / "Gemma4EC-9b/9b_test_predictions_pred_EC_NUMBER.EC_NUMBER_PROMPT_2_gemma4ec.tsv",
    "Theia":            RESULTS / "Theia/theia_test_predictions.tsv",
}

TRUE_CSV = RESULTS.parent / "Benchmarking" / "bec-pred" / "DB" / "test.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_ecs(s):
    ecs = set()
    if not s or (isinstance(s, float) and np.isnan(s)):
        return ecs
    for ec in str(s).split(";")[0].split("|"):
        parts = ec.strip().split(".")
        if len(parts) >= 3 and all(p.isdigit() for p in parts[:3]):
            norm = ".".join(str(int(p)) for p in parts[:3])
            if norm.split(".")[0] in "1234567":
                ecs.add(norm)
    return ecs


def load_sets(path):
    sep = "," if path.suffix == ".csv" else "\t"
    df = pd.read_csv(path, sep=sep, low_memory=False)
    if "Reaction" in df.columns:  # BEC-Pred format: join true labels from test.csv
        true_df = pd.read_csv(TRUE_CSV)
        df = pd.merge(df[["Reaction", "Prediction"]], true_df,
                      left_on="Reaction", right_on="rxn_smiles", how="inner"
                      ).drop_duplicates(subset=["Reaction"])
        true_sets = df["ec"].fillna("").apply(parse_ecs).tolist()
        pred_sets = df["Prediction"].fillna("").apply(parse_ecs).tolist()
    else:
        pred_col = "pred_fragment" if "pred_fragment" in df.columns else "pred"
        true_sets = df["true_label"].fillna("").apply(parse_ecs).tolist()
        pred_sets = df[pred_col].fillna("").apply(parse_ecs).tolist()
    pairs = [(t, p) for t, p in zip(true_sets, pred_sets) if t]
    return [t for t, _ in pairs], [p for _, p in pairs]


def evaluate(true_sets, pred_sets, mlb, all_labels):
    y_true = mlb.transform(true_sets)
    y_pred = mlb.transform(pred_sets)
    support = y_true.sum(axis=0)

    mcc_list  = [matthews_corrcoef(y_true[:, i], y_pred[:, i]) for i in range(len(all_labels))]
    prec_list = precision_score(y_true, y_pred, average=None, zero_division=0)
    rec_list  = recall_score(y_true, y_pred, average=None, zero_division=0)

    w_mcc  = float(np.average(mcc_list,  weights=support))
    w_prec = float(np.average(prec_list, weights=support))
    w_rec  = float(np.average(rec_list,  weights=support))

    label_to_class = {lbl: lbl.split(".")[0] for lbl in all_labels}
    per_class = {}
    for cls in "1234567":
        idx = [i for i, lbl in enumerate(all_labels) if label_to_class[lbl] == cls]
        cls_support = support[idx].sum()
        per_class[cls] = float(np.average([mcc_list[i] for i in idx], weights=support[idx])) \
            if cls_support > 0 else float("nan")

    return w_mcc, w_prec, w_rec, per_class


# ---------------------------------------------------------------------------
# FILE 2 — per-class MCC for main models
# ---------------------------------------------------------------------------

print("=" * 60)
print("FILE 2 — per-class MCC (subsubclass)")
print("=" * 60)

model_data = {}
for name, path in MODELS.items():
    if not path.exists():
        print(f"[skip] {name}: file not found ({path})")
        continue
    model_data[name] = load_sets(path)

all_labels = sorted(
    {lbl for ts, ps in model_data.values() for s in ts + ps for lbl in s}
)
mlb = MultiLabelBinarizer(classes=all_labels)
mlb.fit([all_labels])

file2_rows = []
weighted_avgs = {}
for name, (ts, ps) in model_data.items():
    w_mcc, _, _, per_class = evaluate(ts, ps, mlb, all_labels)
    weighted_avgs[name] = w_mcc
    file2_rows.append({"EC_class": "Weighted_avg", **{name: w_mcc for name in [name]},
                        "_name": name, "_val": w_mcc, "_class": "Weighted_avg"})
    for cls, mcc in per_class.items():
        file2_rows.append({"_name": name, "_val": mcc, "_class": cls})
    print(f"  {name:<22}  w_MCC={w_mcc:.3f}  per_class={' '.join(f'{c}:{v:.3f}' for c,v in per_class.items())}")

# Pivot to wide format
records_dict = {"Weighted_avg": {"EC_class": "Weighted_avg"}}
for cls in "1234567":
    records_dict[cls] = {"EC_class": cls}

for name, (ts, ps) in model_data.items():
    w_mcc, _, _, per_class = evaluate(ts, ps, mlb, all_labels)
    records_dict["Weighted_avg"][name] = w_mcc
    for cls in "1234567":
        records_dict[cls][name] = per_class.get(cls, float("nan"))

file2_df = pd.DataFrame(
    [records_dict["Weighted_avg"]] + [records_dict[c] for c in "1234567"]
)
file2_df = file2_df[["EC_class"] + list(model_data.keys())]
out2 = SUMMARY / "per_class_mcc.csv"
file2_df.to_csv(out2, index=False, float_format="%.3f")
print(f"\nSaved → {out2}\n")


# ---------------------------------------------------------------------------
# FILE 3 — splits weighted MCC (Gemma4EC-9b/2b recomputed, BEC-Pred kept)
# ---------------------------------------------------------------------------
