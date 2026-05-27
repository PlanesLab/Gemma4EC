#!/bin/bash
# ============================================================
# run_theia_full.sh
#
# 1. Train Theia MLP on raw partition (train+val, evaluate on test)
# 2. Evaluate on train split
# 3. Copy test predictions to results/Theia/
# 4. Recompute summary CSVs in results/summary/
#
# Usage:
#   sbatch slurm/run_theia_full.sh
# ============================================================

#SBATCH --job-name=theia_full
#SBATCH --partition=general
#SBATCH --qos=long
#SBATCH --time=06:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --constraint=a100
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64GB
#SBATCH --output=logs/theia_full_%j.out

set -euo pipefail

echo "=========================================="
echo "Theia full pipeline (train + eval + summary)"
echo "Job started : $(date)"
echo "Host        : $(hostname)"
echo "=========================================="

PROJECT_ROOT=${PROJECT_ROOT:-$PWD}
PYTHON=${PYTHON:-python}
THEIA_OUTPUT_DIR=${THEIA_OUTPUT_DIR:-$SCRATCH_ROOT/gemma4ec/theia/results}
THEIA_RESULTS_DIR=$PROJECT_ROOT/results/Theia
DATA_ROOT=$PROJECT_ROOT/data/ECReact

export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

mkdir -p "$THEIA_OUTPUT_DIR" "$THEIA_RESULTS_DIR" "$PROJECT_ROOT/logs"

# ── 1. Train ────────────────────────────────────────────────
echo ""
echo "[1/4] Training Theia MLP on raw partition ..."
"$PYTHON" "$PROJECT_ROOT/train_theia.py" \
    --train_csv  "$DATA_ROOT/train.csv" \
    --val_csv    "$DATA_ROOT/val.csv" \
    --test_csv   "$DATA_ROOT/test.csv" \
    --output_dir "$THEIA_OUTPUT_DIR"

# ── 2. Eval on train split ──────────────────────────────────
echo ""
echo "[2/4] Evaluating on train split ..."
"$PYTHON" "$PROJECT_ROOT/eval_theia.py" \
    --input_csv    "$DATA_ROOT/train.csv" \
    --output_tsv   "$THEIA_RESULTS_DIR/theia_train_predictions.tsv" \
    --model_pt     "$THEIA_OUTPUT_DIR/model.pt" \
    --labelenc_pkl "$THEIA_OUTPUT_DIR/label_encoder.pkl" \
    --batch_size   256

# ── 3. Copy test predictions ────────────────────────────────
echo ""
echo "[3/4] Copying test predictions to results/Theia/ ..."
cp "$THEIA_OUTPUT_DIR/test_predictions.tsv" \
   "$THEIA_RESULTS_DIR/theia_test_predictions.tsv"
cp "$THEIA_OUTPUT_DIR/val_predictions.tsv" \
   "$THEIA_RESULTS_DIR/theia_val_predictions.tsv"

echo "  test  → $THEIA_RESULTS_DIR/theia_test_predictions.tsv"
echo "  val   → $THEIA_RESULTS_DIR/theia_val_predictions.tsv"
echo "  train → $THEIA_RESULTS_DIR/theia_train_predictions.tsv"

# ── 4. Update summary ───────────────────────────────────────
echo ""
echo "[4/4] Recomputing summary tables ..."
cd "$PROJECT_ROOT/results"
"$PYTHON" compute_weighted_metrics.py
"$PYTHON" compute_per_class_and_splits.py

echo ""
echo "=========================================="
echo "Summary updated in: $PROJECT_ROOT/results/summary/"
echo "Job finished : $(date)"
echo "=========================================="
