# BEC-Pred benchmarking

This document explains how to train and evaluate [BEC-Pred](https://github.com/KeeliaQWJ/BEC-Pred) as a baseline model within the Gemma4EC benchmark.

BEC-Pred is an EC number prediction model based on reaction fingerprints ([rxnfp](https://github.com/rxn4chemistry/rxnfp)) and a BERT-style classifier. It serves as a competitive baseline against Gemma4EC.

> Training and evaluation scripts were sourced from the [original BEC-Pred repository](https://github.com/KeeliaQWJ/BEC-Pred) and adapted to run on the Gemma4EC ECReact benchmark.

---

## Requirements

- 1 CUDA-enabled GPU
- 128 GB RAM (required for the rxnfp pre-training step)
- Conda installed

---

## Environment setup

BEC-Pred requires a **separate Conda environment** from the main Gemma4EC training environment.

From the project root:

```bash
conda env create -f benchmarking/bec-pred/becpred_gpu.yml
conda activate becpred_gpu
```

---

## Running via SLURM (recommended)

Use the SLURM scripts in `slurm/` from the repository root:

```bash
sbatch benchmarking/bec-pred/slurm/run_becpred.sh
```

Results are written to `$SCRATCH/gemma4ec/becpred/Results/results_test_ec.csv`.

---

## Running manually

From the project root:

```bash
chmod +x benchmarking/bec-pred/run_becpred.sh
PROJECT_ROOT=$(pwd) bash benchmarking/bec-pred/run_becpred.sh
```

---

## What the pipeline does

The script runs the following steps automatically:

1. **Database generation** — converts the partition's `train.csv`, `val.csv`, and `test.csv` into BEC-Pred format using `generate_becpred_db.py`.
2. **Backbone pre-training** — pre-trains the rxnfp BERT backbone on the USPTO reaction dataset.
3. **EC classifier fine-tuning** — fine-tunes the EC number classifier on train/val splits.
4. **Prediction** — runs inference on the test set and saves raw predictions.
5. **Label assignment** — maps class indices back to EC number strings and saves `results_test_ec.csv`.

---

## Output

Results are saved in:

```
$SCRATCH/gemma4ec/becpred_<DB_NAME>/Results/results_test_ec.csv
```

The output file uses a two-column format compatible with the Gemma4EC evaluation pipeline:

| Column | Description |
|---|---|
| `Reaction` | Reaction SMILES used as input |
| `Prediction` | Predicted EC number |

A pre-computed copy of the BEC-Pred predictions on the standard ECReact test set is included in this repository at:

```
results/bec-pred/results_test_ec.csv
```

---

## Directory layout

```
benchmarking/bec-pred/
├── becpred_gpu.yml             # Conda environment
├── run_becpred.sh              # Main pipeline script (supports DB_NAME)
├── DB/                         # Pre-built DB for the raw partition (train/val/test CSVs)
└── BECPred/
    ├── generate_becpred_db.py  # Convert partition CSVs to BEC-Pred format
    ├── pretrain.py             # Pre-train rxnfp BERT backbone
    ├── finetune_bec.py         # Fine-tune EC classifier
    ├── eval_model.py           # Predict on test set
    ├── Results/
    │   ├── label_assigner.py   # Map class indices back to EC numbers
    │   └── get_metrics.py      # Compute classification metrics
    └── model/
        ├── ecreact_model/      # Fine-tuned model checkpoint
        └── pretrained/         # Pre-trained rxnfp backbone
```

---

## Reproducing the benchmark metrics

Once `results_test_ec.csv` is available, compute the benchmark metrics from the project root:

```bash
cd results/
python compute_weighted_metrics.py
python compute_per_class.py
```

See [`results/README.md`](../results/README.md) for a full description of the metric computation pipeline.

---

## Reference

> Wen, Q. et al. BEC-Pred: Bidirectional Encoder Representations from Transformers-Based Enzyme Commission Number Prediction Using Chemical Reaction Fingerprints. *Journal of Chemical Information and Modeling* (2022).
> [https://doi.org/10.1021/acs.jcim.3c01757](https://doi.org/10.1021/acs.jcim.3c01757)
> [GitHub repository](https://github.com/KeeliaQWJ/BEC-Pred)
