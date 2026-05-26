#!/bin/bash
#SBATCH --job-name=gemma4ec_api_predict
#SBATCH --partition=general
#SBATCH --qos=regular
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16gb
#SBATCH --time=04:00:00
#SBATCH --output=logs/api_predict_%j.out

set -euo pipefail

echo "Starting API prediction job: $(date)"
hostname

# =======================
# USER CONFIGURATION
# =======================
PROJECT_ROOT=${PROJECT_ROOT:-$PWD}
SCRATCH_ROOT=${SCRATCH_ROOT:-/scratch/$USER}

# Positional arguments:
# 1) model name (default: gpt-5-mini)
# 2) split name (test/val/train) OR path to CSV
MODEL_NAME=${1:-"gpt-5-mini"}
ARG2=${2:-""}

DATA_ROOT=${DATA_ROOT:-"$PROJECT_ROOT/data/ECReact"}

# =======================
# RESOLVE INPUT CSV
# =======================
if [[ -z "$ARG2" ]]; then
  SPLIT_NAME="test"
  RAW_DATA_FILE="$DATA_ROOT/${SPLIT_NAME}.csv"
elif [[ "$ARG2" == *.csv ]] || [[ "$ARG2" == */* ]]; then
  RAW_DATA_FILE="$ARG2"
  SPLIT_NAME="$(basename "$RAW_DATA_FILE" .csv)"
else
  SPLIT_NAME="$ARG2"
  RAW_DATA_FILE="$DATA_ROOT/${SPLIT_NAME}.csv"
fi

# =======================
# OUTPUT PATHS
# =======================
PROCESSED_DATA_FOLDER=${PROCESSED_DATA_FOLDER:-"$SCRATCH_ROOT/gemma4ec/api_predict/processed_${SPLIT_NAME}"}
OUTPUT_FOLDER=${OUTPUT_FOLDER:-"$SCRATCH_ROOT/gemma4ec/api_predict/results_${SPLIT_NAME}"}

PROMPTS_JSON=${PROMPTS_JSON:-"$PROJECT_ROOT/prompts/prompts.json"}
TEMPLATE_KEY="EC_NUMBER_PROMPT_API"
TEMPLATE_ALIAS="EC_NUMBER"

mkdir -p "$PROCESSED_DATA_FOLDER" "$OUTPUT_FOLDER" logs

# =======================
# ENVIRONMENT
# =======================
module load Miniforge3
conda activate gemma4ec

export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "=== Environment ==="
which python
python -V
pip show openai google-genai || true
echo "==================="

# =======================
# API KEY CHECKS
# =======================
if [[ "$MODEL_NAME" == gemini-* ]]; then
  if [[ -z "${GEMINI_API_KEY:-}" && -z "${GOOGLE_API_KEY:-}" ]]; then
    echo "ERROR: GEMINI_API_KEY or GOOGLE_API_KEY must be set for model $MODEL_NAME"
    exit 1
  fi
else
  if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "ERROR: OPENAI_API_KEY must be set for model $MODEL_NAME"
    exit 1
  fi
fi

# =======================
# INFO
# =======================
echo "Using model:        $MODEL_NAME"
echo "Input CSV:          $RAW_DATA_FILE"
echo "Split name:         $SPLIT_NAME"
echo "Processed folder:  $PROCESSED_DATA_FOLDER"
echo "Output folder:     $OUTPUT_FOLDER"

# =======================
# EXECUTION
# =======================
python -u "$PROJECT_ROOT/predict_api.py" \
  --raw_data_file "$RAW_DATA_FILE" \
  --processed_data_folder "$PROCESSED_DATA_FOLDER" \
  --output_folder "$OUTPUT_FOLDER" \
  --prompts_json_path "$PROMPTS_JSON" \
  --template_key "$TEMPLATE_KEY" \
  --template_alias "$TEMPLATE_ALIAS" \
  --model_name "$MODEL_NAME"

echo "Finished API prediction job: $(date)"
