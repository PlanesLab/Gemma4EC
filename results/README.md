# results/

Prediction outputs and evaluation metrics for all models benchmarked in Gemma4EC.

---

## Key output files

| File | Description |
|---|---|
| `summary/weighted_metrics.csv` | **Main benchmark table.** Overall support-weighted MCC, PPV, and Recall for every model at the sub-subclass level. |
| `summary/per_class_mcc.csv` | Per-EC-class weighted MCC for all models (EC classes 1–7 plus overall). |

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

### `compute_per_class.py` — per-class comparison

Produces one table using the same weighted-MCC methodology:
- `summary/per_class_mcc.csv` — weighted MCC broken down by EC class (1–7) for all models

```bash
cd results/
python compute_per_class.py
# writes summary/per_class_mcc.csv
```

---

## Folder layout

```
results/
├── compute_weighted_metrics.py       # Main benchmark — weighted MCC across all models
├── compute_per_class.py              # Per-class MCC comparison
│
├── summary/
│   ├── weighted_metrics.csv          # All models — overall weighted MCC/PPV/Recall
│   └── per_class_mcc.csv             # All models — MCC per EC class (1–7)
│
├── bec-pred/
│   └── results_test_ec.csv           # BEC-Pred predictions on the standard test set
│
└── zeroshot/
    └── results/
        └── zeroshot_test_*.tsv       # Zero-shot prediction TSV (gitignored)
```

> **Note:** Large TSV prediction files and adapter weights are gitignored. Raw model predictions used in the paper are available in the HuggingFace repository.

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

---

## Attention outputs

For reaction-level attention visualisations (not stored here), see:

- [`infer_attention.py`](../infer_attention.py) — batch script that writes BertViz HTML and attention heatmap PNGs to `attn_out/`
- [`notebooks/mechanistic_explanation.ipynb`](../notebooks/mechanistic_explanation.ipynb) — interactive notebook combining attention maps with a 4-turn TxGemma-Chat mechanistic dialogue
