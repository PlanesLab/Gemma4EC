"""
compute_weighted_metrics.py — Recompute the main benchmark table (weighted_metrics.csv).

Evaluates all models at the sub-subclass level (3-digit EC, e.g. 1.1.1) using a shared
label space across all models, a MultiLabelBinarizer, and support-weighted averages of
per-subsubclass MCC, PPV, and Recall.

Usage:
    cd results/
    python compute_weighted_metrics.py
    # writes summary/weighted_metrics.csv
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import matthews_corrcoef, precision_score, recall_score
from sklearn.preprocessing import MultiLabelBinarizer

warnings.filterwarnings("ignore")

RESULTS = Path(__file__).parent
TRUE_CSV = RESULTS.parent / "src" / "bec-pred" / "DB" / "test.csv"

MODELS = {
    "ChatGPT-4.1-mini": (
        RESULTS / "APIs/chatgpt-4_1-mini/test_predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API.gpt-4_1-mini.tsv",
        "API",
    ),
    "ChatGPT-5.1": (
        RESULTS / "APIs/chatgpt-5_1/test_predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API.gpt-5_1.tsv",
        "API",
    ),
    "ChatGPT-5.2": (
        RESULTS / "APIs/chatgpt-5_2/test_predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API.gpt-5_2.tsv",
        "API",
    ),
    "Gemini-2.5-flash": (
        RESULTS / "APIs/gemini-2_5-flash/test_predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API.gemini-2_5-flash.tsv",
        "API",
    ),
    "TxGemma-9b": (
        RESULTS / "zeroshot/results/zeroshot_test_20260415-170538.tsv",
        "TxGemma",
    ),
    "BEC-Pred": (
        RESULTS / "bec-pred/results_test_ec.csv",
        "BEC-Pred",
    ),
    "Gemma4EC-2b": (
        RESULTS / "Gemma4EC-2b/2b_test_predictor_predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_2.d6i9pynh.tsv",
        "Gemma4EC",
    ),
    "Gemma4EC-9b": (
        RESULTS / "Gemma4EC-9b/9b_test_predictions_pred_EC_NUMBER.EC_NUMBER_PROMPT_2_gemma4ec.tsv",
        "Gemma4EC",
    ),
}


def parse_ecs(s):
    """Return set of normalised 3-part EC strings (e.g. {'1.1.1'}).
    Only first ';'-group is used. Leading zeros stripped (2.03.01 → 2.3.1).
    """
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


# Load all model data
model_data = {}  # name -> (true_sets, pred_sets)
for name, (path, group) in MODELS.items():
    sep = "," if path.suffix == ".csv" else "\t"
    df = pd.read_csv(path, sep=sep, low_memory=False)
    if "Reaction" in df.columns:  # BEC-Pred: join true labels from test.csv
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
    model_data[name] = ([t for t, _ in pairs], [p for _, p in pairs])

# Shared label space
all_labels = sorted(
    {lbl for ts, ps in model_data.values() for s in ts + ps for lbl in s}
)

mlb = MultiLabelBinarizer(classes=all_labels)
mlb.fit([all_labels])

# Evaluate
records = []
for name, (path, group) in MODELS.items():
    true_sets, pred_sets = model_data[name]
    y_true = mlb.transform(true_sets)
    y_pred = mlb.transform(pred_sets)
    support = y_true.sum(axis=0)

    mcc_list  = [matthews_corrcoef(y_true[:, i], y_pred[:, i]) for i in range(len(all_labels))]
    prec_list = precision_score(y_true, y_pred, average=None, zero_division=0)
    rec_list  = recall_score(y_true, y_pred, average=None, zero_division=0)

    w_mcc  = float(np.average(mcc_list,  weights=support))
    w_prec = float(np.average(prec_list, weights=support))
    w_rec  = float(np.average(rec_list,  weights=support))

    print(f"{name:<22}  MCC={w_mcc:.4f}  PPV={w_prec:.4f}  Recall={w_rec:.4f}")
    records.append({
        "Model": name,
        "Group": group,
        "Weighted_MCC": round(w_mcc, 4),
        "Weighted_PPV": round(w_prec, 4),
        "Weighted_Recall": round(w_rec, 4),
    })

out = pd.DataFrame(records)
out_path = RESULTS / "summary" / "weighted_metrics.csv"
out.to_csv(out_path, index=False)
print(f"\nSaved → {out_path}")
