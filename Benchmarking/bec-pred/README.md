# BEC-Pred baseline for Gemma4EC

This directory contains the [BEC-Pred](https://github.com/KeeliaQWJ/BEC-Pred) pipeline adapted to run on the Gemma4EC benchmark partitions (Rhea_Scaffold, Rhea_Stratified, Rhea_Time).

BEC-Pred is an EC number prediction model based on reaction fingerprints (rxnfp) and a BERT-style classifier. It is included here as a competitive baseline.

---

## Environment

BEC-Pred requires a separate Conda environment from the main Gemma4EC training environment.

```bash
conda env create -f becpred_gpu.yml
conda activate becpred_gpu
```

---

## Running via SLURM (recommended)

Use the SLURM scripts in `slurm/` from the repository root:

```bash
# All three partitions
bash slurm/submit_all_partitions_becpred.sh

# Single partition
DB_NAME=Rhea_Scaffold sbatch slurm/run_becpred.sh
```

Results are written to `$SCRATCH/gemma4ec/becpred_<DB_NAME>/Results/results_test_ec.csv`.

---

## Running manually

From this directory:

```bash
DB_NAME=Rhea_Scaffold \
PROJECT_ROOT=/path/to/Gemma4EC \
bash run_becpred.sh
```

The script:
1. Generates a BEC-Pred-formatted DB from the partition's `train.csv` and `val.csv`
2. Copies the partition `test.csv` for evaluation
3. Pre-trains the rxnfp BERT backbone
4. Fine-tunes the EC classifier
5. Runs prediction on the test set
6. Assigns EC labels and saves `results_test_ec.csv`

---

## Directory structure

```
src/bec-pred/
├── run_becpred.sh              # Main pipeline script (supports DB_NAME)
├── becpred_gpu.yml             # Conda environment
├── DB/                         # Pre-built DB for the raw partition (train/val/test CSVs)
├── BECPred/
│   ├── generate_becpred_db.py  # Convert partition CSVs to BEC-Pred format
│   ├── pretrain.py             # Pre-train rxnfp BERT backbone
│   ├── finetune_bec.py         # Fine-tune EC classifier
│   └── eval_model.py           # Predict on test set
└── Results/
    ├── label_assigner.py       # Map class indices back to EC numbers
    └── get_metrics.py          # Compute classification metrics
```

---

## Reference

> Wen, Q. et al. BEC-Pred: Bidirectional Encoder Representations from Transformers-Based Enzyme Commission Number Prediction Using Chemical Reaction Fingerprints. *Journal of Chemical Information and Modeling* (2022).
> [https://github.com/KeeliaQWJ/BEC-Pred](https://github.com/KeeliaQWJ/BEC-Pred)
