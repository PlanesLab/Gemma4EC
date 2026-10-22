# BEC-Pred baseline

This directory contains the [BEC-Pred](https://github.com/KeeliaQWJ/BEC-Pred) pipeline adapted to run on the Gemma4EC ECReact benchmark.

BEC-Pred is an EC number prediction model based on reaction fingerprints ([rxnfp](https://github.com/rxn4chemistry/rxnfp)) and a BERT-style classifier. It is included here as a competitive baseline against Gemma4EC.

> In the Gemma4EC benchmark this pipeline is run per seed by [`slurm/seeds/run_seed_becpred.sh`](../../slurm/seeds/run_seed_becpred.sh); see [`docs/benchmark.md`](../../docs/benchmark.md).

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

## Pre-training corpus

`pretrain.py` expects `data/mlm_train.txt` and `data/mlm_test.txt`: one reaction SMILES per line,
from the training and validation splits. They are not shipped (large and fully derived); build them
with, for a given seed,

```bash
python - <<'EOF'
import pandas as pd
for src, dst in (("train", "mlm_train"), ("val", "mlm_test")):
    df = pd.read_csv(f"data/ECReact_seeds_strat_dedup/seed0/{src}.csv")
    open(f"benchmarking/bec-pred/data/{dst}.txt", "w").write("\n".join(df.rxn_smiles) + "\n")
EOF
```

In the Gemma4EC benchmark this step is run once; every seed then reuses the same label-free
backbone in `BECPred/model/pretrained/`.

---

## Directory structure

```
benchmarking/bec-pred/
├── becpred_gpu.yml             # Conda environment
├── run_becpred.sh              # Main pipeline script (supports DB_NAME)
├── data/vocab.txt              # SMILES tokenizer vocabulary
├── Results/label_assigner.py   # Map class indices back to EC numbers
└── BECPred/
    ├── generate_becpred_db.py  # Convert split CSVs to BEC-Pred format
    ├── pretrain.py             # Label-free MLM pre-training of the BERT backbone
    ├── finetune_bec.py         # Fine-tune the EC classifier
    ├── eval_model.py           # Predict on the test set
    └── model/pretrained/       # Config of the pretrained backbone (weights are not in git)
```

---

## Reference

> Wen, Q. et al. BEC-Pred: Bidirectional Encoder Representations from Transformers-Based Enzyme Commission Number Prediction Using Chemical Reaction Fingerprints. *Journal of Chemical Information and Modeling* (2022).
> [https://doi.org/10.1021/acs.jcim.3c01757](https://doi.org/10.1021/acs.jcim.3c01757) · [GitHub](https://github.com/KeeliaQWJ/BEC-Pred)
