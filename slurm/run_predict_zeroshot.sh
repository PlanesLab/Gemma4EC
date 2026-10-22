#!/bin/bash
# ============================================================
# run_predict_zeroshot.sh
#
# Zero-shot EC prediction with base TxGemma (no adapter).
# Evaluates on the ECReact test set.
#
# Usage:
#   sbatch slurm/run_predict_zeroshot.sh
# ============================================================

#SBATCH --job-name=gemma4ec_zeroshot
#SBATCH --partition=general
#SBATCH --qos=long
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --constraint=a100
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=100GB
#SBATCH --output=logs/predict_zeroshot_%j.out

set -euo pipefail
[[ -f "${PROJECT_ROOT:-$PWD}/config.sh" ]] && source "${PROJECT_ROOT:-$PWD}/config.sh"   # site paths (config.sh.example)

echo "=========================================="
echo "Zero-shot prediction"
echo "Job started    : $(date)"
echo "Host           : $(hostname)"
echo "=========================================="

# ============================================================
# PATHS
# ============================================================
PROJECT_ROOT=${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
SCRATCH_ROOT=${SCRATCH_ROOT:-$PWD/work}
CACHE_ROOT=${CACHE_ROOT:-"$SCRATCH_ROOT/.cache/gemma4ec"}

TEST_CSV="$PROJECT_ROOT/data/ECReact_seeds_strat_dedup/seed0/test.csv"
OUTPUT_FOLDER="$SCRATCH_ROOT/gemma4ec/zeroshot/results"

MODEL_ID=${MODEL_ID:-"google/txgemma-9b-predict"}
SAVE_DIRECTORY="$SCRATCH_ROOT/gemma4ec/base_models/txgemma_9b"

# ============================================================
# W&B
# ============================================================
WANDB_PROJECT="Gemma4EC-partitions"
WANDB_ENTITY=${WANDB_ENTITY:-}   # optional W&B team (config.sh)

# ============================================================
# INFERENCE SETTINGS
# ============================================================
EVAL_BATCH_SIZE=8
MAX_RETRIES=5

# ============================================================
# ENVIRONMENT
# ============================================================
CONDA_ENV=${CONDA_ENV:-gemma4ec}
PYTHON="$CONDA_ENV/bin/python"
export PATH="$CONDA_ENV/bin:$PATH"
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# ============================================================
# TOKENS
# ============================================================
if [[ -z "${HUGGINGFACE_TOKEN:-}" ]]; then
    # Fall back to stored token file (set by huggingface-cli login)
    TOKEN_FILE="$HOME/.huggingface/token"
    if [[ -f "$TOKEN_FILE" ]]; then
        export HUGGINGFACE_TOKEN=$(cat "$TOKEN_FILE")
    else
        echo "ERROR: HUGGINGFACE_TOKEN not set and $TOKEN_FILE not found."
        exit 1
    fi
fi

if [[ -z "${WANDB_API_KEY:-}" ]]; then
    echo "WARNING: WANDB_API_KEY not set — disabling W&B."
    DISABLE_WANDB="--disable_wandb"
else
    export WANDB_API_KEY
    DISABLE_WANDB=""
fi

# ============================================================
# CACHE DIRS
# ============================================================
mkdir -p "$CACHE_ROOT"
export HF_HOME="$CACHE_ROOT/hf"
export TRANSFORMERS_CACHE="$CACHE_ROOT/hf/transformers"
export HF_DATASETS_CACHE="$CACHE_ROOT/hf/datasets"
export WANDB_DIR="$CACHE_ROOT/wandb"
export WANDB_CONFIG_DIR="$CACHE_ROOT/wandb"
export TORCH_HOME="$CACHE_ROOT/torch"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
umask 077

export MASTER_PORT=$(python3 -c "import random; print(random.randint(20000, 50000))")

mkdir -p "$OUTPUT_FOLDER" logs

# ============================================================
# RUN — PROMPT_2 (batch_size=4 to avoid OOM)
# ============================================================
"$PYTHON" "$PROJECT_ROOT/predict_zeroshot.py" \
    --test_csv "$TEST_CSV" \
    --output_folder "$OUTPUT_FOLDER" \
    --prompts_json_path "$PROJECT_ROOT/prompts/prompts.json" \
    --template_key "EC_NUMBER_PROMPT_2" \
    --template_alias "EC_NUMBER" \
    --model_id "$MODEL_ID" \
    --save_directory "$SAVE_DIRECTORY" \
    --cache_dir "$CACHE_ROOT/hf" \
    --eval_batch_size 4 \
    --max_retries "$MAX_RETRIES" \
    --hf_token "$HUGGINGFACE_TOKEN" \
    --wandb_project "$WANDB_PROJECT" \
    ${WANDB_ENTITY:+--wandb_entity "$WANDB_ENTITY"} \
    $DISABLE_WANDB

echo "=========================================="
echo "Job finished   : $(date)"
echo "=========================================="
