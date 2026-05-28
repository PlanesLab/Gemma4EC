# BEC-Pred baseline

This directory contains the [BEC-Pred](https://github.com/KeeliaQWJ/BEC-Pred) pipeline adapted to run on the Gemma4EC ECReact benchmark.

BEC-Pred is an EC number prediction model based on reaction fingerprints ([rxnfp](https://github.com/rxn4chemistry/rxnfp)) and a BERT-style classifier. It is included here as a competitive baseline against Gemma4EC.

> For a full benchmarking guide, see [`docs/becpred_benchmarking.md`](../../docs/becpred_benchmarking.md).

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

## What the script does

1. **Database generation** — converts partition CSVs into BEC-Pred format.
2. **Backbone pre-training** — pre-trains the rxnfp BERT backbone on USPTO data.
3. **EC classifier fine-tuning** — fine-tunes on train/val splits.
4. **Prediction** — runs inference on the test set.
5. **Label assignment** — maps class indices back to EC numbers and saves `results_test_ec.csv`.

---

## Directory structure

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

## Reference

> Wen, Q. et al. BEC-Pred: Bidirectional Encoder Representations from Transformers-Based Enzyme Commission Number Prediction Using Chemical Reaction Fingerprints. *Journal of Chemical Information and Modeling* (2022).
> [https://doi.org/10.1021/acs.jcim.3c01757](https://doi.org/10.1021/acs.jcim.3c01757) · [GitHub](https://github.com/KeeliaQWJ/BEC-Pred)
