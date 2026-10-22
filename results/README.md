# results/

Metric tables for the 10-seed benchmark. The per-seed prediction files themselves are not stored
here: they are written to the work directory by the jobs in [`slurm/seeds/`](../slurm/seeds) and
scored by [`seeds/compute_seed_metrics.py`](seeds/compute_seed_metrics.py).

## `seeds_strat_dedup/` — benchmark tables

| File | Description |
|---|---|
| `seed_summary.csv` | **Main table.** Per method: mean ± SD and 95% CI of MCC / precision / recall over the 10 seeds. |
| `seed_metrics.csv` | One row per method and seed (the input to every other table). |
| `per_class_metrics.csv` | MCC per EC class (1–7), per method and seed. |
| `level_metrics.csv` | MCC at EC class, subclass and sub-subclass level. |
| `significance_tests.csv` | All pairwise tests: paired Wilcoxon signed-rank and paired t-test, with Benjamini–Hochberg adjustment. |
| `pairwise_tests.csv`, `vs_gemma4ec_9b.csv` | Pairwise comparisons with Holm adjustment, all pairs and against Gemma4EC-9B. |
| `seed0_ec_class_breakdown.csv` | Train/val/test composition of seed 0 by EC class. |

## Metric

Each EC sub-subclass (`1.1.1`, `2.3.1`, …) is treated as a binary classifier. MCC, precision and
recall are computed per label and averaged weighted by support (the number of true instances).
Within a seed every method shares one label space, so the numbers are directly comparable. A test
reaction with no prediction counts as a miss; `coverage` in `seed_metrics.csv` reports the matched
fraction.

See [`seeds/README.md`](seeds/README.md) for how predictions are located and matched, and
[`../docs/benchmark.md`](../docs/benchmark.md) to reproduce the benchmark.

## Prediction file format

TSVs written by `predict.py` / `predict_zeroshot.py`:

| Column | Description |
|---|---|
| `true_label` | Ground-truth EC (e.g. `1.01.01`) |
| `pred_raw` | Raw model output |
| `pred_fragment` | Extracted EC |
| `pred_well_formed` | `True` if `pred_fragment` is a valid EC pattern |
| `smiles` | Reaction SMILES used as input |
