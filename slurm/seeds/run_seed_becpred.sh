#!/bin/bash
# Fine-tune + evaluate BEC-Pred on one seed split.
# Reuses the label-free MLM-pretrained BERT (benchmarking/bec-pred/BECPred/model/pretrained);
# only the supervised EC fine-tune depends on the split.
#
# Usage: SEED=0 sbatch slurm/seeds/run_seed_becpred.sh
#SBATCH --job-name=seed_becpred
#SBATCH --partition=general
#SBATCH --qos=xlong
#SBATCH --time=3-00:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64GB
#SBATCH --output=logs/seed_becpred_%j.out

source "${PROJECT_ROOT:-$PWD}/slurm/seeds/_common.sh"
BEC_SRC="$PROJECT_ROOT/benchmarking/bec-pred"
PYTHON="$ENVS/becpred_gpu/bin/python"
export PATH="$ENVS/becpred_gpu/bin:$PATH"
WORK="$SEED_WORK/becpred"
mkdir -p "$WORK/DB" "$WORK/model" "$WORK/Results"

# RDKit-canonicalize reaction SMILES (scripts/canonicalize_smiles.py) before BEC-Pred sees them.
# Row order and count are preserved (failures fall back to the input SMILES), so
# results_test_ec.csv stays positionally aligned with the seed test.csv.
# becpred_gpu is Python 3.6 without a usable RDKit → use clean_ec for this step only.
mkdir -p "$WORK/canon"
"$ENVS/clean_ec/bin/python3" - "$PROJECT_ROOT/scripts" "$SEED_DATA" "$WORK/canon" <<'PY'
import sys
import pandas as pd
sys.path.insert(0, sys.argv[1])
from canonicalize_smiles import canon_rxn
for split in ("train", "val", "test"):
    df = pd.read_csv(f"{sys.argv[2]}/{split}.csv", dtype=str)
    before = df["rxn_smiles"].copy()
    df["rxn_smiles"] = df["rxn_smiles"].apply(canon_rxn)
    df.to_csv(f"{sys.argv[3]}/{split}.csv", index=False)
    print(f"[canon] {split}: {(before != df.rxn_smiles).sum()}/{len(df)} SMILES changed")
PY

"$PYTHON" "$BEC_SRC/BECPred/generate_becpred_db.py" \
    --train_file "$WORK/canon/train.csv" \
    --val_file   "$WORK/canon/val.csv" \
    --output_dir "$WORK/DB"
cp "$WORK/canon/test.csv" "$WORK/DB/test.csv"
ln -sfn "$BEC_SRC/data" "$WORK/data"
ln -sfn "$BEC_SRC/BECPred/model/pretrained" "$WORK/model/pretrained"

# BEC-Pred scripts use paths relative to the working directory
cd "$WORK"
"$PYTHON" "$BEC_SRC/BECPred/finetune_bec.py"
"$PYTHON" "$BEC_SRC/BECPred/eval_model.py"
"$PYTHON" "$BEC_SRC/Results/label_assigner.py" \
    --input_csv  "$WORK/Results/results_test.csv" \
    --labels     "$WORK/DB/ec_class_labels_ecreact.csv" \
    --output_csv "$WORK/Results/results_test_ec.csv"

# Intermediate checkpoints are ~44 GB per seed; keep only the final model + predictions
rm -rf "$WORK/model/ecreact_model"/checkpoint-*

echo "Done: $(date)"
