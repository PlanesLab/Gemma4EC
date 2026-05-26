#!/bin/bash
#SBATCH --job-name=gemma4ec_chat_train
#SBATCH --partition=general
#SBATCH --qos=xlong
#SBATCH --time=5-00:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:4
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=4
#SBATCH --mem=300gb
#SBATCH --output=logs/train_chat_%j.out

set -euo pipefail

echo "Starting Gemma4EC-chat training: $(date)"
hostname

# =======================
# USER CONFIGURATION
# =======================
PROJECT_ROOT=${PROJECT_ROOT:-$PWD}
SCRATCH_ROOT=${SCRATCH_ROOT:-/scratch/$USER}
CACHE_ROOT=${CACHE_ROOT:-"$SCRATCH_ROOT/.cache/gemma4ec"}

TRAIN_CSV=${TRAIN_CSV:-"$PROJECT_ROOT/data/ECReact/train.csv"}
VAL_CSV=${VAL_CSV:-"$PROJECT_ROOT/data/ECReact/val.csv"}

MODEL_ID=${MODEL_ID:-"google/txgemma-9b-chat"}
SAVE_DIR=${SAVE_DIR:-"$SCRATCH_ROOT/gemma4ec/chat/base_model"}
OUTPUT_DIR=${OUTPUT_DIR:-"$SCRATCH_ROOT/gemma4ec/chat/checkpoints"}

# =======================
# TRAINING HYPERPARAMS
# =======================
BATCH_SIZE=4
GRAD_ACCUM=4
EPOCHS=5
LR=5e-5
MAX_SEQ_LEN=1024
PATIENCE=3

# =======================
# PEFT
# =======================
LORA_R=8
LORA_ALPHA=16
LORA_DROPOUT=0.05

# =======================
# W&B (optional)
# =======================
WANDB_PROJECT=${WANDB_PROJECT:-"Gemma4EC-chat"}
WANDB_ENTITY=${WANDB_ENTITY:-"miramon_team"}

# =======================
# ENVIRONMENT
# =======================
CONDA_ENV=${CONDA_ENV:-/scratch/$USER/conda_envs/gemma4ec}
export PATH="$CONDA_ENV/bin:$PATH"
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# =======================
# REQUIRED TOKENS
# =======================
if [[ -z "${HUGGINGFACE_TOKEN:-}" ]]; then
  HUGGINGFACE_TOKEN=$(cat ~/.huggingface/token 2>/dev/null || true)
fi
if [[ -z "${HUGGINGFACE_TOKEN:-}" ]]; then
  echo "ERROR: HUGGINGFACE_TOKEN not set and ~/.huggingface/token not found"
  exit 1
fi

# W&B
if [[ -z "${WANDB_API_KEY:-}" ]]; then
  WANDB_API_KEY=$(grep -A2 "api.wandb.ai" ~/.netrc 2>/dev/null | grep password | awk '{print $2}' || true)
fi
export WANDB_API_KEY

# =======================
# CACHE DIRS
# =======================
mkdir -p "$CACHE_ROOT" "$OUTPUT_DIR" logs

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
# LAUNCH
# =======================
NUM_GPUS=$(nvidia-smi --list-gpus | wc -l)

accelerate launch \
  --num_processes "$NUM_GPUS" \
  --num_machines 1 \
  --mixed_precision bf16 \
  --dynamo_backend no \
  "$PROJECT_ROOT/chat/finetune_chat.py" \
    --train_csv   "$TRAIN_CSV" \
    --val_csv     "$VAL_CSV" \
    --model_id    "$MODEL_ID" \
    --save_dir    "$SAVE_DIR" \
    --output_dir  "$OUTPUT_DIR" \
    --hf_token    "$HUGGINGFACE_TOKEN" \
    --lora_r      "$LORA_R" \
    --lora_alpha  "$LORA_ALPHA" \
    --lora_dropout "$LORA_DROPOUT" \
    --batch_size  "$BATCH_SIZE" \
    --grad_accum  "$GRAD_ACCUM" \
    --epochs      "$EPOCHS" \
    --lr          "$LR" \
    --max_seq_len "$MAX_SEQ_LEN" \
    --patience    "$PATIENCE" \
    --wandb_project "$WANDB_PROJECT" \
    --wandb_entity  "$WANDB_ENTITY"

echo "Finished Gemma4EC-chat training: $(date)"
