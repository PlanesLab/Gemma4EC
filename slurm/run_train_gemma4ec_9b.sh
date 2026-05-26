#!/bin/bash
#SBATCH --job-name=gemma4ec_train_9b
#SBATCH --partition=general
#SBATCH --qos=xlong
#SBATCH --time=5-00:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:4
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=4
#SBATCH --mem=300gb
#SBATCH --output=logs/train_9b_%j.out

set -euo pipefail

echo "Starting Gemma4EC 9B training job: $(date)"
hostname

# =======================
# USER CONFIGURATION
# =======================
PROJECT_ROOT=${PROJECT_ROOT:-$PWD}
SCRATCH_ROOT=${SCRATCH_ROOT:-/scratch/$USER}
CACHE_ROOT=${CACHE_ROOT:-"$SCRATCH_ROOT/.cache/gemma4ec"}

RAW_DATA_FOLDER=${RAW_DATA_FOLDER:-"$PROJECT_ROOT/data/ECReact"}
USE_TEST=${USE_TEST:-True}

PROCESSED_DATA_FOLDER=${PROCESSED_DATA_FOLDER:-"$SCRATCH_ROOT/gemma4ec/train_9b/processed"}
OUTPUT_FOLDER=${OUTPUT_FOLDER:-"$SCRATCH_ROOT/gemma4ec/train_9b/results"}

MODEL_ID=${MODEL_ID:-"google/txgemma-9b-predict"}
SAVE_DIRECTORY=${SAVE_DIRECTORY:-"$SCRATCH_ROOT/gemma4ec/base_models/txgemma_9b"}

PROMPTS_JSON=${PROMPTS_JSON:-"$PROJECT_ROOT/prompts/prompts.json"}
TEMPLATE_KEY="EC_NUMBER_PROMPT_2"
TEMPLATE_ALIAS="EC_NUMBER"

# =======================
# TRAINING HYPERPARAMS
# =======================
BATCH_SIZE=8
EVAL_BATCH_SIZE=30
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

# =======================
# PEFT
# =======================
ADAPTER_METHOD="lora"
LORA_R=16
LORA_ALPHA=16
LORA_DROPOUT=0.1

# =======================
# FEW-SHOT
# =======================
FEW_SHOT_TRAINING=True
FEW_SHOT_RATIO=0.3
FEW_SHOT_K_MIN=1
FEW_SHOT_K_MAX=7

# =======================
# EVAL & CHECKPOINTING
# =======================
EVAL_EVERY_EPOCHS=1
MONITOR_METRIC="mcc"
GREATER_IS_BETTER=True
EARLY_STOPPING_PATIENCE=5
SAVE_BEST=True

# =======================
# ENVIRONMENT
# =======================
module load Miniforge3
conda activate gemma4ec

export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# =======================
# REQUIRED TOKENS
# =======================
if [[ -z "${HUGGINGFACE_TOKEN:-}" ]]; then
  echo "ERROR: HUGGINGFACE_TOKEN not set"
  exit 1
fi

# W&B optional
if [[ -n "${WANDB_API_KEY:-}" ]]; then
  export WANDB_API_KEY
fi

# =======================
# CACHE (OPTIONAL)
# =======================
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

# =======================
# OUTPUT DIRS
# =======================
mkdir -p "$PROCESSED_DATA_FOLDER" "$OUTPUT_FOLDER" logs

# =======================
# LAUNCH TRAINING
# =======================
NUM_GPUS=$(nvidia-smi --list-gpus | wc -l)

accelerate launch \
  --num_processes "$NUM_GPUS" \
  --num_machines 1 \
  --mixed_precision fp16 \
  --dynamo_backend no \
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
    --ddp_find_unused_parameters False

echo "Finished Gemma4EC 9B training job: $(date)"