#!/bin/bash
# ============================================================
# run_eval_theia.sh
#
# Evaluate the pre-trained Theia MLP baseline on all data splits
# (train, val, test) using data/ECReact_seeds_strat_dedup/seed0/*.csv.
#
# Usage:
#   sbatch slurm/run_eval_theia.sh
# ============================================================

#SBATCH --job-name=theia_eval
#SBATCH --partition=general
#SBATCH --qos=regular
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32GB
#SBATCH --output=logs/theia_eval_%j.out

set -euo pipefail
[[ -f "${PROJECT_ROOT:-$PWD}/config.sh" ]] && source "${PROJECT_ROOT:-$PWD}/config.sh"   # site paths (config.sh.example)

echo "=========================================="
echo "Theia MLP evaluation"
echo "Job started    : $(date)"
echo "Host           : $(hostname)"
echo "=========================================="

# ============================================================
# PATHS
# ============================================================
PROJECT_ROOT=${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
SCRATCH_ROOT=${SCRATCH_ROOT:-$PWD/work}
CACHE_ROOT=${CACHE_ROOT:-"$SCRATCH_ROOT/.cache/gemma4ec"}

DATA_ROOT="$PROJECT_ROOT/data/ECReact_seeds_strat_dedup/seed0"
OUTPUT_DIR=${OUTPUT_DIR:-"$SCRATCH_ROOT/gemma4ec/theia/results"}

# Path to model.pt and label_encoder.pkl saved by run_train_theia.sh
THEIA_MODEL=${THEIA_MODEL:-"$SCRATCH_ROOT/gemma4ec/theia_raw/results/model.pt"}
THEIA_LE=${THEIA_LE:-"$SCRATCH_ROOT/gemma4ec/theia_raw/results/label_encoder.pkl"}

# ============================================================
# ENVIRONMENT
# ============================================================
CONDA_ENV=${CONDA_ENV:-gemma4ec}
PYTHON="$CONDA_ENV/bin/python"
export PATH="$CONDA_ENV/bin:$PATH"
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

mkdir -p "$OUTPUT_DIR" logs

# ============================================================
# RUN ON EACH SPLIT
# ============================================================
for SPLIT in test val train; do
    INPUT_CSV="$DATA_ROOT/${SPLIT}.csv"
    if [[ ! -f "$INPUT_CSV" ]]; then
        echo "[skip] $SPLIT split not found: $INPUT_CSV"
        continue
    fi

    OUTPUT_TSV="$OUTPUT_DIR/theia_${SPLIT}.tsv"
    echo ""
    echo "[theia] Evaluating $SPLIT split: $INPUT_CSV"

    "$PYTHON" "$PROJECT_ROOT/eval_theia.py" \
        --input_csv   "$INPUT_CSV" \
        --output_tsv  "$OUTPUT_TSV" \
        --model_pt    "$THEIA_MODEL" \
        --labelenc_pkl "$THEIA_LE" \
        --batch_size  256
done

echo ""
echo "=========================================="
echo "Job finished   : $(date)"
echo "=========================================="
