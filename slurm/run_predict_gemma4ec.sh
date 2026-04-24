#!/bin/bash
#SBATCH --job-name=gemma4ec_predict
#SBATCH --partition=general
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64gb
#SBATCH --time=24:00:00
#SBATCH --output=logs/predict_%j.out

set -euo pipefail

echo "Starting Gemma4EC prediction job: $(date)"
hostname

# =======================
# USER CONFIGURATION
# =======================
PROJECT_ROOT=${PROJECT_ROOT:-$PWD}
SCRATCH_ROOT=${SCRATCH_ROOT:-/scratch/$USER}

RAW_DATA_FILE=${RAW_DATA_FILE:-"$PROJECT_ROOT/data/raw/test.csv"}
PROCESSED_DATA_FOLDER=${PROCESSED_DATA_FOLDER:-"$SCRATCH_ROOT/gemma4ec/predict/processed"}
OUTPUT_FOLDER=${OUTPUT_FOLDER:-"$SCRATCH_ROOT/gemma4ec/predict/results"}

MODEL_CHECKPOINT_FOLDER=${MODEL_CHECKPOINT_FOLDER:?Must set MODEL_CHECKPOINT_FOLDER}
MODEL_ID=${MODEL_ID:-"google/txgemma-9b-predict"}

PROMPTS_JSON=${PROMPTS_JSON:-"$PROJECT_ROOT/prompt_examples/prompts.json"}
TEMPLATE_KEY=${TEMPLATE_KEY:-"EC_NUMBER_PROMPT_2"}
TEMPLATE_ALIAS="EC_NUMBER"

# =======================
# ENVIRONMENT
# =======================
module load Miniforge3
conda activate gemma4ec

export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# =======================
# HUGGING FACE TOKEN
# =======================
if [[ -z "${HUGGINGFACE_TOKEN:-}" ]]; then
  echo "ERROR: HUGGINGFACE_TOKEN not set"
  exit 1
fi

# =======================
# CACHE (OPTIONAL)
# =======================
CACHE_ROOT=${CACHE_ROOT:-"$SCRATCH_ROOT/.cache/gemma4ec"}
mkdir -p "$CACHE_ROOT"

export HF_HOME="$CACHE_ROOT/hf"
export TRANSFORMERS_CACHE="$CACHE_ROOT/hf/transformers"

# =======================
# RUN
# =======================
mkdir -p "$PROCESSED_DATA_FOLDER" "$OUTPUT_FOLDER"

accelerate launch \
  --num_processes 1 \
  "$PROJECT_ROOT/predict.py" \
    --raw_data_file "$RAW_DATA_FILE" \
    --processed_data_folder "$PROCESSED_DATA_FOLDER" \
    --output_folder "$OUTPUT_FOLDER" \
    --model_checkpoint_folder "$MODEL_CHECKPOINT_FOLDER" \
    --model_id "$MODEL_ID" \
    --prompts_json_path "$PROMPTS_JSON" \
    --template_key "$TEMPLATE_KEY" \
    --template_alias "$TEMPLATE_ALIAS" \
    --hf_token "$HUGGINGFACE_TOKEN"

echo "Finished job: $(date)"
