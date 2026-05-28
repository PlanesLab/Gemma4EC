#!/bin/bash
# ============================================================
# run_becpred.sh
#
# SLURM wrapper for the BEC-Pred pipeline on the ECReact benchmark.
#
# Usage:
#   sbatch benchmarking/bec-pred/slurm/run_becpred.sh
# ============================================================

#SBATCH --job-name=becpred
#SBATCH --partition=general
#SBATCH --qos=xlong
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --constraint=a100
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64GB
#SBATCH --output=logs/becpred_%x_%j.out

set -euo pipefail

PROJECT_ROOT=${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
SCRATCH_ROOT=${SCRATCH_ROOT:-/scratch/$USER}

echo "============================================"
echo "==== BEC-Pred: $DB_NAME"
echo "==== $(date)  |  $(hostname)"
echo "============================================"

# ── Environment ───────────────────────────────────────────────
CONDA_ENV="$SCRATCH_ROOT/Envs/becpred_gpu"
PYTHON="$CONDA_ENV/bin/python"
export PATH="$CONDA_ENV/bin:$PATH"

"$PYTHON" -c 'import sys; print(sys.version_info[:])'
"$PYTHON" -c 'import torch; print(f"GPU: {torch.cuda.is_available()}, count={torch.cuda.device_count()}")'

# ── Partition-specific working directory ──────────────────────
WORK_DIR="$SCRATCH_ROOT/gemma4ec/becpred/$DB_NAME"
mkdir -p "$WORK_DIR/DB" "$WORK_DIR/model" "$WORK_DIR/Results"

# Link static assets (vocab + MLM pretraining text files)
ln -sfn "$PROJECT_ROOT/src/bec-pred/data" "$WORK_DIR/data"

PARTITION_DIR="$PROJECT_ROOT/data/ECReact"
BEC_SRC="$PROJECT_ROOT/src/bec-pred"
RESULTS_DIR="$PROJECT_ROOT/results/BECPred"
mkdir -p "$RESULTS_DIR"

# ── Generate DB from partition train/val CSVs ─────────────────
echo "=== Generate BEC-Pred DB ==="
"$PYTHON" "$BEC_SRC/BECPred/generate_becpred_db.py" \
    --train_file "$PARTITION_DIR/train.csv" \
    --val_file   "$PARTITION_DIR/val.csv" \
    --output_dir "$WORK_DIR/DB"

# Copy partition test.csv so eval_model.py can read ./DB/test.csv
cp "$PARTITION_DIR/test.csv" "$WORK_DIR/DB/test.csv"

# ── Run pipeline from working dir (scripts use relative paths) ─
cd "$WORK_DIR"

echo "=== Pretrain ==="
start=$(date +%s)
"$PYTHON" "$BEC_SRC/BECPred/pretrain.py"
echo "Pretrain completed in $(($(date +%s) - start))s"

echo "=== Finetune ==="
start=$(date +%s)
"$PYTHON" "$BEC_SRC/BECPred/finetune_bec.py"
echo "Finetune completed in $(($(date +%s) - start))s"

echo "=== Eval ==="
start=$(date +%s)
"$PYTHON" "$BEC_SRC/BECPred/eval_model.py"
echo "Eval completed in $(($(date +%s) - start))s"

echo "=== Label Assigner ==="
"$PYTHON" "$BEC_SRC/Results/label_assigner.py" \
    --input_csv  "$WORK_DIR/Results/results_test.csv" \
    --labels     "$WORK_DIR/DB/ec_class_labels_ecreact.csv" \
    --output_csv "$WORK_DIR/Results/results_test_ec.csv"

# ── Save results to shared results dir ───────────────────────
cp "$WORK_DIR/Results/results_test_ec.csv" "$RESULTS_DIR/becpred_${DB_NAME}_results.csv"
echo "Results saved to $RESULTS_DIR/becpred_${DB_NAME}_results.csv"

echo "============================================"
echo "=== BEC-Pred $DB_NAME finished: $(date) ==="
echo "============================================"
