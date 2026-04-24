# DEPRECATED — legacy one-off analysis script with hardcoded paths.
# Use results/get_metrics.py or results/compute_weighted_mcc.py instead.

import re
import pandas as pd
from sklearn.metrics import matthews_corrcoef, precision_score, recall_score, f1_score
from sklearn.preprocessing import LabelEncoder
import numpy as np

# --- Load data ---
bec_pred = pd.read_csv('/scratch/jarcagniriv/ProjectECNum/BEC-Pred/Results/results_test_ec.csv')
true = pd.read_csv('/scratch/jarcagniriv/ProjectECNum/BEC-Pred/DB/test.csv')
gemma4ec = pd.read_csv(
    '/scratch/jarcagniriv/ProjectECNum/final_results/gemma-predictor/no-shot/predictions_test.EC_NUMBER.EC_NUMBER_PROMPT_2.otyp3x3f.tsv',
    sep='\t'
)

# New datasets: finetuned gemma 9b and txgemma 9b
gemma4ec_9b = pd.read_csv(
    '/scratch/jarcagniriv/ProjectECNum/final_results/gemma-predictor/no-shot/9b/finetuned_gemma4ec_9b.tsv',
    sep='\t'
)
txgemma_9b = pd.read_csv(
    '/scratch/jarcagniriv/ProjectECNum/final_results/gemma-predictor/no-shot/9b/nofinetuned_txgemma_9b.tsv',
    sep='\t'
)

# --- Utility: extract main EC class (first number before dot) ---
def extract_ec_class(ec_number):
    try:
        if pd.isna(ec_number):
            return np.nan
        return str(ec_number).split('.')[0]
    except Exception:
        return np.nan

# For txgemma: keep only predictions that are full EC numbers (e.g., 1.2.3.4)
def is_full_ec(ec):
    try:
        ec_str = str(ec).strip()
        # Check if it matches full EC format (1.2.3.4) and starts with 1-7
        if re.match(r'^[1-7](\.\d+){3}$', ec_str):
            return True
        return False
    except Exception:
        return False

# Filter txgemma predictions that are not full EC format
if 'pred_fragment' in txgemma_9b.columns:
    txgemma_9b = txgemma_9b[txgemma_9b['pred_fragment'].apply(is_full_ec)].copy()

# --- Compute all metrics (global + per-class) ---
def compute_all_metrics(pred_df, true_df, pred_col, rxn_col_pred, rxn_col_true, true_ec_col):
    merged = pd.merge(pred_df, true_df, left_on=rxn_col_pred, right_on=rxn_col_true, how='inner')
    merged = merged.dropna(subset=[true_ec_col, pred_col])
    merged['true_class'] = merged[true_ec_col].apply(extract_ec_class)
    merged['pred_class'] = merged[pred_col].apply(extract_ec_class)

    # Keep only true EC classes 1-7
    merged = merged[merged['true_class'].isin(['1','2','3','4','5','6','7'])]

    # --- GLOBAL METRICS ---
    # Fit LabelEncoder on all classes appearing in either true or predicted
    all_ecs = pd.concat([merged['true_class'], merged['pred_class']]).unique()
    le_global = LabelEncoder().fit(all_ecs)

    y_true_global = le_global.transform(merged['true_class'])
    y_pred_global = le_global.transform(merged['pred_class'])

    global_metrics = {
        'MCC': matthews_corrcoef(y_true_global, y_pred_global) if len(np.unique(y_true_global)) > 1 else 0.0,
        'PPV': precision_score(y_true_global, y_pred_global, average='weighted', zero_division=0),
        'Recall': recall_score(y_true_global, y_pred_global, average='weighted', zero_division=0),
        'F1': f1_score(y_true_global, y_pred_global, average='weighted', zero_division=0)
    }

    # --- PER-CLASS METRICS (EC class 1–7) ---
    all_classes = sorted(pd.concat([merged['true_class'], merged['pred_class']]).unique())
    if len(all_classes) == 0:
        results_df = pd.DataFrame(columns=['EC_class','MCC','PPV','Recall','F1','Samples'])
        weighted = {'MCC':0.0,'PPV':0.0,'Recall':0.0,'F1':0.0}
        return global_metrics, weighted, results_df

    le = LabelEncoder().fit(all_classes)
    y_true = le.transform(merged['true_class'])
    y_pred = le.transform(merged['pred_class'])
    class_labels = le.classes_

    results = []
    for cls, label in zip(np.unique(y_true), class_labels):
        y_true_bin = (y_true == cls).astype(int)
        y_pred_bin = (y_pred == cls).astype(int)
        try:
            mcc = matthews_corrcoef(y_true_bin, y_pred_bin)
        except Exception:
            mcc = 0.0
        ppv = precision_score(y_true_bin, y_pred_bin, zero_division=0)
        rec = recall_score(y_true_bin, y_pred_bin, zero_division=0)
        f1 = f1_score(y_true_bin, y_pred_bin, zero_division=0)
        n_samples = int(np.sum(y_true_bin))
        results.append({'EC_class': label, 'MCC': mcc, 'PPV': ppv, 'Recall': rec, 'F1': f1, 'Samples': n_samples})

    results_df = pd.DataFrame(results)

    # Weighted averages by sample count
    total_samples = results_df['Samples'].sum()
    if total_samples == 0:
        weighted = {'MCC':0.0,'PPV':0.0,'Recall':0.0,'F1':0.0}
    else:
        weighted = {
            'MCC': np.average(results_df['MCC'], weights=results_df['Samples']),
            'PPV': np.average(results_df['PPV'], weights=results_df['Samples']),
            'Recall': np.average(results_df['Recall'], weights=results_df['Samples']),
            'F1': np.average(results_df['F1'], weights=results_df['Samples'])
        }

    return global_metrics, weighted, results_df


# --- Compute metrics for all predictors ---
global_bec, weighted_bec, bec_table = compute_all_metrics(
    pred_df=bec_pred,
    true_df=true,
    pred_col='Prediction',
    rxn_col_pred='Reaction',
    rxn_col_true='rxn_smiles',
    true_ec_col='ec'
)

global_gemma, weighted_gemma, gemma_table = compute_all_metrics(
    pred_df=gemma4ec,
    true_df=true,
    pred_col='pred_fragment',
    rxn_col_pred='smiles',
    rxn_col_true='rxn_smiles',
    true_ec_col='ec'
)

global_gemma9b, weighted_gemma9b, gemma9b_table = compute_all_metrics(
    pred_df=gemma4ec_9b,
    true_df=true,
    pred_col='pred_fragment',
    rxn_col_pred='smiles',
    rxn_col_true='rxn_smiles',
    true_ec_col='ec'
)

global_txgemma9b, weighted_txgemma9b, txgemma9b_table = compute_all_metrics(
    pred_df=txgemma_9b,
    true_df=true,
    pred_col='pred_fragment',
    rxn_col_pred='smiles',
    rxn_col_true='rxn_smiles',
    true_ec_col='ec'
)

# --- Merge per-class results for all methods ---
tables = {
    'BEC-Pred': bec_table,
    'Gemma4EC_2b': gemma_table,
    'Gemma4EC_9b': gemma9b_table,
    'TxGemma_9b': txgemma9b_table
}

renamed_tables = {}
for name, df in tables.items():
    renamed_tables[name] = df.rename(columns={
        'MCC': f'{name}_MCC',
        'PPV': f'{name}_PPV',
        'Recall': f'{name}_Recall',
        'F1': f'{name}_F1',
        'Samples': f'{name}_Samples'
    })

# Start with empty DataFrame on EC_class
combined = None
for df in renamed_tables.values():
    if combined is None:
        combined = df.copy()
    else:
        combined = pd.merge(combined, df, on='EC_class', how='outer')

combined = combined.fillna(0).sort_values(by='EC_class')

# --- Print results nicely ---
methods = ['BEC-Pred', 'Gemma4EC_2b', 'Gemma4EC_9b', 'TxGemma_9b']
globals_map = {
    'BEC-Pred': global_bec,
    'Gemma4EC_2b': global_gemma,
    'Gemma4EC_9b': global_gemma9b,
    'TxGemma_9b': global_txgemma9b
}
weighted_map = {
    'BEC-Pred': weighted_bec,
    'Gemma4EC_2b': weighted_gemma,
    'Gemma4EC_9b': weighted_gemma9b,
    'TxGemma_9b': weighted_txgemma9b
}

print("\n================= GLOBAL (Normal) Metrics =================")
print("Metric      | " + " | ".join([f"{m:>12s}" for m in methods]))
print("-" * (14 + 16 * len(methods)))
for metric in ['MCC', 'PPV', 'Recall', 'F1']:
    vals = " | ".join([f"{globals_map[m].get(metric,0.0):12.4f}" for m in methods])
    print(f"{metric:10s} | {vals}")

print("\n================= WEIGHTED (By EC Class) Metrics =================")
print("Metric      | " + " | ".join([f"{m:>12s}" for m in methods]))
print("-" * (14 + 16 * len(methods)))
for metric in ['MCC', 'PPV', 'Recall', 'F1']:
    vals = " | ".join([f"{weighted_map[m].get(metric,0.0):12.4f}" for m in methods])
    print(f"{metric:10s} | {vals}")

print("\n================= PER-CLASS METRICS (EC Class 1–7) =================")
print(combined.to_string(index=False))

# --- Save per-class results (selected cols) ---
per_class_cols = ['EC_class']
for name in methods:
    per_class_cols += [f'{name}_MCC', f'{name}_PPV', f'{name}_Recall']

per_class_metrics = combined[per_class_cols].copy()
per_class_metrics.to_csv('comparison_per_class_metrics_MCC_PPV_Recall.csv', index=False)
print("\nSaved: comparison_per_class_metrics_MCC_PPV_Recall.csv")

# --- Build "Overall" row repeated for each class ---
overall_row = {'EC_class': 'Overall'}
for name in methods:
    gm = globals_map[name]
    overall_row[f'{name}_MCC'] = gm.get('MCC', 0.0)
    overall_row[f'{name}_PPV'] = gm.get('PPV', 0.0)
    overall_row[f'{name}_Recall'] = gm.get('Recall', 0.0)

# Repeat overall row once per EC class
overall_df = pd.DataFrame([overall_row] * len(per_class_metrics))
final_df = pd.concat([overall_df, per_class_metrics], ignore_index=True)

# --- Save to CSV ---
final_df.to_csv('comparison_metrics_with_overall.csv', index=False)
print("\nSaved: comparison_metrics_with_overall.csv")
