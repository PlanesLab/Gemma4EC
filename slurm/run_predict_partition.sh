#!/bin/bash
# ============================================================
# run_predict_partition.sh
#
# Run EC prediction on val + test splits using a saved LoRA adapter.
# Use this to get correct predictions after training without retraining.
#
# Required env vars (pass via --export or set before submitting):
#   DB_NAME            — partition name (Rhea_Scaffold | Rhea_Stratified | Rhea_Time)
#   HUGGINGFACE_TOKEN  — HF access token
#
# Example:
#   sbatch --export=ALL,DB_NAME=Rhea_Time,HUGGINGFACE_TOKEN=$HF_TOKEN \
#          slurm/run_predict_partition.sh
# ============================================================

#SBATCH --job-name=gemma4ec_predict
#SBATCH --partition=general
#SBATCH --qos=long
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --constraint=a100
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=100GB
#SBATCH --output=logs/predict_%x_%j.out

set -euo pipefail

if [[ -z "${DB_NAME:-}" ]]; then
    echo "ERROR: DB_NAME is not set."
    echo "  Valid values: Rhea_Scaffold | Rhea_Stratified | Rhea_Time"
    exit 1
fi

echo "=========================================="
echo "DB_NAME        : $DB_NAME"
echo "Job started    : $(date)"
echo "Host           : $(hostname)"
echo "=========================================="

# ============================================================
# PATHS
# ============================================================
PROJECT_ROOT=${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
SCRATCH_ROOT=${SCRATCH_ROOT:-/scratch/$USER}
CACHE_ROOT=${CACHE_ROOT:-"$SCRATCH_ROOT/.cache/gemma4ec"}

PARTITIONS_ROOT="$PROJECT_ROOT/data/partitions"
ADAPTER_DIR="$SCRATCH_ROOT/gemma4ec/$DB_NAME/results/best"
OUTPUT_FOLDER="$SCRATCH_ROOT/gemma4ec/$DB_NAME/results"

MODEL_ID=${MODEL_ID:-"google/txgemma-9b-predict"}
SAVE_DIRECTORY="$SCRATCH_ROOT/gemma4ec/base_models/txgemma_9b"
PROMPTS_JSON="$PROJECT_ROOT/prompts/prompts.json"
TEMPLATE_KEY="EC_NUMBER_PROMPT_2"
TEMPLATE_ALIAS="EC_NUMBER"
EVAL_BATCH_SIZE=8
MAX_SEQ_LENGTH=1280

# ============================================================
# ENVIRONMENT
# ============================================================
CONDA_ENV=${CONDA_ENV:-/scratch/$USER/conda_envs/gemma4ec}
PYTHON="$CONDA_ENV/bin/python"
export PATH="$CONDA_ENV/bin:$PATH"
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# ============================================================
# REQUIRED TOKENS
# ============================================================
if [[ -z "${HUGGINGFACE_TOKEN:-}" ]]; then
    TOKEN_FILE="$HOME/.huggingface/token"
    if [[ -f "$TOKEN_FILE" ]]; then
        export HUGGINGFACE_TOKEN=$(cat "$TOKEN_FILE")
    else
        echo "ERROR: HUGGINGFACE_TOKEN not set and $TOKEN_FILE not found."
        exit 1
    fi
fi

# ============================================================
# CACHE DIRS
# ============================================================
mkdir -p "$CACHE_ROOT"
export HF_HOME="$CACHE_ROOT/hf"
export TRANSFORMERS_CACHE="$CACHE_ROOT/hf/transformers"
export HF_DATASETS_CACHE="$CACHE_ROOT/hf/datasets"
export TORCH_HOME="$CACHE_ROOT/torch"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
umask 077

export MASTER_PORT=$(python3 -c "import random; print(random.randint(20000, 50000))")

mkdir -p "$OUTPUT_FOLDER" logs

# ============================================================
# VALIDATE ADAPTER EXISTS
# ============================================================
if [[ ! -f "$ADAPTER_DIR/adapter_config.json" ]]; then
    echo "ERROR: Adapter not found at $ADAPTER_DIR"
    echo "  Make sure the training job has completed and saved the best model."
    exit 1
fi

# ============================================================
# RUN PREDICTION ON VAL + TEST
# ============================================================
for SPLIT in val test; do
    DATA_FILE="$PARTITIONS_ROOT/$DB_NAME/${SPLIT}.csv"
    if [[ ! -f "$DATA_FILE" ]]; then
        echo "[skip] $SPLIT split not found: $DATA_FILE"
        continue
    fi

    echo ""
    echo "[predict] Running on $SPLIT split: $DATA_FILE"

    "$PYTHON" "$PROJECT_ROOT/predict.py" \
        --raw_data_file "$DATA_FILE" \
        --processed_data_folder "$CACHE_ROOT/predict/${DB_NAME}/${SPLIT}" \
        --output_folder "$OUTPUT_FOLDER" \
        --model_checkpoint_folder "$ADAPTER_DIR" \
        --model_id "$MODEL_ID" \
        --save_directory "$SAVE_DIRECTORY" \
        --cache_dir "$CACHE_ROOT/hf" \
        --prompts_json_path "$PROMPTS_JSON" \
        --template_key "$TEMPLATE_KEY" \
        --template_alias "$TEMPLATE_ALIAS" \
        --eval_batch_size "$EVAL_BATCH_SIZE" \
        --hf_token "$HUGGINGFACE_TOKEN"
done

echo "=========================================="
echo "DB_NAME        : $DB_NAME"
echo "Job finished   : $(date)"
echo "=========================================="
