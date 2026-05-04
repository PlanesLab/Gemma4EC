# results/

Prediction outputs and evaluation metrics for all models benchmarked in Gemma4EC.

---

## Key output files

| File | Description |
|---|---|
| `summary/weighted_metrics.csv` | **Main benchmark table.** Overall support-weighted MCC, PPV, and Recall for every model at the sub-subclass level. |
| `summary/per_class_mcc.csv` | Per-EC-class weighted MCC for all models (EC classes 1–7 plus overall). |
| `summary/splits_weighted_mcc.csv` | Gemma4EC-9b vs [Theia](https://github.com/daenuprobst/theia) vs [BEC-Pred](https://github.com/KeeliaQWJ/BEC-Pred) across the three [Rhea](https://www.rhea-db.org/) partition splits (Scaffold, Stratified, Time). |

---

## Reproducing the metrics

Two scripts in this directory compute the benchmark tables from raw prediction TSVs.

### `compute_weighted_metrics.py` — main benchmark

Each EC sub-subclass (e.g. `1.1.1`, `2.3.1`) is treated as a binary classifier. MCC is computed per label then averaged **weighted by support** (number of true instances). This is the methodology used in the paper.

```bash
cd results/
python compute_weighted_metrics.py
# writes summary/weighted_metrics.csv
```

No extra arguments needed — all paths are resolved relative to this folder.

### `compute_per_class_and_splits.py` — per-class and partition comparison

Produces two tables using the same weighted-MCC methodology:
- `summary/per_class_mcc.csv` — weighted MCC broken down by EC class (1–7) for all models
- `summary/splits_weighted_mcc.csv` — weighted MCC for Gemma4EC-9b on each [Rhea](https://www.rhea-db.org/) split, alongside pre-computed [BEC-Pred](https://github.com/KeeliaQWJ/BEC-Pred) and [Theia](https://github.com/daenuprobst/theia) values

```bash
cd results/
python compute_per_class_and_splits.py
# writes summary/per_class_mcc.csv
#         summary/splits_weighted_mcc.csv
```

For a simpler per-split summary that scans any prediction directory, see [`scripts/summarize_results.py`](../scripts/summarize_results.py).

---

## Folder layout

```
results/
├── compute_weighted_metrics.py       # Main benchmark — weighted MCC across all models
├── compute_per_class_and_splits.py   # Per-class MCC + partition split comparison
│
├── summary/
│   ├── weighted_metrics.csv          # All models — overall weighted MCC/PPV/Recall
│   ├── per_class_mcc.csv             # All models — MCC per EC class (1–7)
│   └── splits_weighted_mcc.csv       # Rhea splits — Gemma4EC / BEC-Pred / Theia
│
├── bec-pred/
│   └── results_test_ec.csv           # BEC-Pred predictions on the standard test set
│
├── Rhea_Scaffold/                    # Gemma4EC-9b fine-tuned on Rhea_Scaffold
│   ├── processed/                    # Intermediate JSONL files (gitignored)
│   └── results/
│       ├── best/                     # Saved LoRA adapter (weights gitignored)
│       └── predictions_*.tsv         # Prediction TSVs (gitignored)
│
├── Rhea_Stratified/                  # Same structure as Rhea_Scaffold
│
├── Rhea_Time/                        # Same structure as Rhea_Scaffold
│
└── zeroshot/
    └── results/
        └── zeroshot_test_*.tsv       # Zero-shot prediction TSV (gitignored)
```

> **Note:** Large TSV prediction files and adapter weights are gitignored.
> Raw model predictions used in the paper are available in the HuggingFace repository.

---

## Prediction file format

All TSV files produced by `predict.py` / `predict_zeroshot.py` share this schema:

| Column | Description |
|---|---|
| `true_label` | Ground-truth EC (e.g. `1.01.01`) |
| `pred_raw` | Raw model output string |
| `pred_fragment` | Extracted EC fragment |
| `pred_well_formed` | `True` if `pred_fragment` is a valid EC pattern |
| `smiles` | Reaction SMILES used as input |

BEC-Pred predictions (`bec-pred/results_test_ec.csv`) use a two-column format: `Reaction` (SMILES) and `Prediction` (EC).
