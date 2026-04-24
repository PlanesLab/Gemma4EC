#!/bin/bash
# ============================================================
# run_train_theia.sh
#
# Train the Theia MLP baseline on the Raw partition
# (data/raw/train.csv + data/raw/val.csv), then evaluate on test.
#
# Usage:
#   sbatch slurm/run_train_theia.sh
# ============================================================

#SBATCH --job-name=theia_train
#SBATCH --partition=general
#SBATCH --qos=long
#SBATCH --time=06:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --constraint=a100
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64GB
#SBATCH --output=logs/theia_train_%j.out

set -euo pipefail

echo "=========================================="
echo "Theia MLP training (Raw partition)"
echo "Job started    : $(date)"
echo "Host           : $(hostname)"
echo "=========================================="

# ============================================================
# PATHS
# ============================================================
PROJECT_ROOT=${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
SCRATCH_ROOT=${SCRATCH_ROOT:-/scratch/$USER}

DATA_ROOT="$PROJECT_ROOT/data/raw"
OUTPUT_DIR="$SCRATCH_ROOT/gemma4ec/theia_raw/results"

# ============================================================
# ENVIRONMENT
# ============================================================
CONDA_ENV=${CONDA_ENV:-/scratch/$USER/conda_envs/gemma4ec}
PYTHON="$CONDA_ENV/bin/python"
export PATH="$CONDA_ENV/bin:$PATH"
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

mkdir -p "$OUTPUT_DIR" logs

# ============================================================
# RUN
# ============================================================
"$PYTHON" "$PROJECT_ROOT/train_theia.py" \
    --train_csv  "$DATA_ROOT/train.csv" \
    --val_csv    "$DATA_ROOT/val.csv" \
    --test_csv   "$DATA_ROOT/test.csv" \
    --output_dir "$OUTPUT_DIR"

echo "=========================================="
echo "Job finished   : $(date)"
echo "=========================================="
