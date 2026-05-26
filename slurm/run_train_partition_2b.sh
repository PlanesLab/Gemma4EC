#!/bin/bash
# ============================================================
# run_train_partition_2b.sh
#
# Fine-tune Gemma4EC on a single Rhea partition using the 2B model.
# Driven by the DB_NAME env var (set via sbatch --export or
# directly when calling sbatch).
#
# Example — submit one job:
#   sbatch --export=ALL,DB_NAME=Rhea_Scaffold slurm/run_train_partition_2b.sh
#
# Example — submit all three partitions:
#   slurm/submit_all_partitions_2b.sh
# ============================================================

#SBATCH --job-name=gemma4ec_2b_%x
#SBATCH --partition=general
#SBATCH --qos=xlong
#SBATCH --time=5-00:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:4
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=4
#SBATCH --mem=200GB
#SBATCH --output=logs/train_2b_%x_%j.out

set -euo pipefail

# ============================================================
# REQUIRED: set DB_NAME before running
# ============================================================
if [[ -z "${DB_NAME:-}" ]]; then
    echo "ERROR: DB_NAME is not set."
    echo "  Valid values: Rhea_Scaffold | Rhea_Stratified | Rhea_Time"
    echo "  Usage: sbatch --export=ALL,DB_NAME=Rhea_Scaffold slurm/run_train_partition_2b.sh"
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

PARTITIONS_ROOT=${PARTITIONS_ROOT:-"$PROJECT_ROOT/data/partitions"}
RAW_DATA_FOLDER="$PARTITIONS_ROOT/$DB_NAME"

PROCESSED_DATA_FOLDER="$SCRATCH_ROOT/gemma4ec/2b/$DB_NAME/processed"
OUTPUT_FOLDER="$SCRATCH_ROOT/gemma4ec/2b/$DB_NAME/results"

MODEL_ID=${MODEL_ID:-"google/txgemma-2b-predict"}
SAVE_DIRECTORY=${SAVE_DIRECTORY:-"$SCRATCH_ROOT/gemma4ec/base_models/txgemma_2b"}

PROMPTS_JSON="$PROJECT_ROOT/prompts/prompts.json"

# ============================================================
# W&B
# ============================================================
WANDB_PROJECT=${WANDB_PROJECT:-"Gemma4EC-partitions"}
WANDB_ENTITY=${WANDB_ENTITY:-"miramon_team"}
WANDB_GROUP="2b_${DB_NAME}"
WANDB_RUN_NAME="2b_${DB_NAME}_$(date +%m%d_%H%M)"

# ============================================================
# TRAINING HYPERPARAMS
# ============================================================
TEMPLATE_KEY="EC_NUMBER_PROMPT_2"
TEMPLATE_ALIAS="EC_NUMBER"

BATCH_SIZE=8
EVAL_BATCH_SIZE=16
GRAD_ACCUM_STEPS=4
WARMUP_STEPS=2
EPOCHS=30
LR=5e-4
LOGGING_STEPS=10
MAX_SEQ_LENGTH=1280

OPTIMIZER="adamw_torch"
LR_SCHEDULER="cosine"
WEIGHT_DECAY=0.001
TRAINER_MODE="manual"

# ============================================================
# PEFT
# ============================================================
ADAPTER_METHOD="lora"
LORA_R=16
LORA_ALPHA=16
LORA_DROPOUT=0.1

# ============================================================
# FEW-SHOT
# ============================================================
FEW_SHOT_TRAINING=True
FEW_SHOT_RATIO=0.3
FEW_SHOT_K_MIN=1
FEW_SHOT_K_MAX=7

# ============================================================
# EVAL & CHECKPOINTING
# ============================================================
EVAL_EVERY_EPOCHS=1
MONITOR_METRIC="mcc"
GREATER_IS_BETTER=True
EARLY_STOPPING_PATIENCE=5
SAVE_BEST=True
USE_TEST=True

# ============================================================
# ENVIRONMENT
# ============================================================
CONDA_ENV=${CONDA_ENV:-/scratch/$USER/Envs/gemma4ec}
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
# W&B API KEY
# ============================================================
if [[ -z "${WANDB_API_KEY:-}" ]]; then
    echo "WARNING: WANDB_API_KEY not set — W&B logging will be disabled."
    DISABLE_WANDB_FLAG="--disable_wandb"
else
    export WANDB_API_KEY
    DISABLE_WANDB_FLAG=""
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
export TRITON_CACHE_DIR="$CACHE_ROOT/triton"
export NUMBA_CACHE_DIR="$CACHE_ROOT/numba"
export MPLCONFIGDIR="$CACHE_ROOT/matplotlib"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
umask 077

# ============================================================
# DATA PREPARATION (if not already done)
# ============================================================
if [[ ! -f "$RAW_DATA_FOLDER/train.csv" ]]; then
    echo "[data] Prepared CSVs not found. Running prepare_db.py for $DB_NAME ..."
    CASE1_DB_ROOT=${CASE1_DB_ROOT:-"$SCRATCH_ROOT/Case1-Rhea/Database"}
    "$PYTHON" "$PROJECT_ROOT/scripts/prepare_db.py" \
        --db "$DB_NAME" \
        --db_root "$CASE1_DB_ROOT" \
        --out_root "$PARTITIONS_ROOT" \
        --val_frac 0.10 \
        --strat_level 2 \
        --seed 42
else
    echo "[data] Using existing CSVs in $RAW_DATA_FOLDER"
fi

# ============================================================
# OUTPUT DIRS
# ============================================================
mkdir -p "$PROCESSED_DATA_FOLDER" "$OUTPUT_FOLDER" logs

# ============================================================
# LAUNCH TRAINING
# ============================================================
if [[ -n "${SLURM_GPUS_ON_NODE:-}" ]]; then
    NUM_GPUS="$SLURM_GPUS_ON_NODE"
elif command -v nvidia-smi &>/dev/null; then
    NUM_GPUS=$(nvidia-smi --list-gpus | wc -l)
else
    NUM_GPUS=4  # fallback: matches --gres=gpu:4
fi
echo "[train] Launching on $NUM_GPUS GPUs"

"$PYTHON" -m accelerate.commands.launch \
    --num_processes "$NUM_GPUS" \
    --num_machines 1 \
    --mixed_precision fp16 \
    --dynamo_backend no \
    --main_process_port 0 \
    "$PROJECT_ROOT/main.py" \
        --raw_data_folder "$RAW_DATA_FOLDER" \
        --use_test "$USE_TEST" \
        --processed_data_folder "$PROCESSED_DATA_FOLDER" \
        --output_folder "$OUTPUT_FOLDER" \
        --model_id "$MODEL_ID" \
        --save_directory "$SAVE_DIRECTORY" \
        --prompts_json_path "$PROMPTS_JSON" \
        --template_key "$TEMPLATE_KEY" \
        --template_alias "$TEMPLATE_ALIAS" \
        --batch_size "$BATCH_SIZE" \
        --eval_batch_size "$EVAL_BATCH_SIZE" \
        --gradient_accumulation_steps "$GRAD_ACCUM_STEPS" \
        --warmup_steps "$WARMUP_STEPS" \
        --num_train_epochs "$EPOCHS" \
        --learning_rate "$LR" \
        --fp16 True \
        --logging_steps "$LOGGING_STEPS" \
        --max_seq_length "$MAX_SEQ_LENGTH" \
        --optimizer "$OPTIMIZER" \
        --lr_scheduler_type "$LR_SCHEDULER" \
        --weight_decay "$WEIGHT_DECAY" \
        --trainer_mode "$TRAINER_MODE" \
        --adapter_method "$ADAPTER_METHOD" \
        --lora_r "$LORA_R" \
        --lora_alpha "$LORA_ALPHA" \
        --lora_dropout "$LORA_DROPOUT" \
        --few_shot_training "$FEW_SHOT_TRAINING" \
        --few_shot_ratio "$FEW_SHOT_RATIO" \
        --few_shot_k_min "$FEW_SHOT_K_MIN" \
        --few_shot_k_max "$FEW_SHOT_K_MAX" \
        --eval_every_epochs "$EVAL_EVERY_EPOCHS" \
        --monitor_metric "$MONITOR_METRIC" \
        --greater_is_better "$GREATER_IS_BETTER" \
        --early_stopping_patience "$EARLY_STOPPING_PATIENCE" \
        --save_best "$SAVE_BEST" \
        --hf_token "$HUGGINGFACE_TOKEN" \
        --gradient_checkpointing True \
        --ddp_find_unused_parameters False \
        --wandb_project "$WANDB_PROJECT" \
        --wandb_entity "$WANDB_ENTITY" \
        --wandb_run_name "$WANDB_RUN_NAME" \
        --wandb_group "$WANDB_GROUP" \
        --wandb_tags "TxGemma-2B" "EC" "$DB_NAME" \
        --job_type "finetune" \
        ${DISABLE_WANDB_FLAG}

echo "=========================================="
echo "DB_NAME        : $DB_NAME"
echo "Job finished   : $(date)"
echo "=========================================="
