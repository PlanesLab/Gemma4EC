#!/bin/bash
#SBATCH --job-name=gemma4ec_rag_infer
#SBATCH --partition=general
#SBATCH --qos=long
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=80gb
#SBATCH --output=logs/rag_infer_%j.out

set -euo pipefail

echo "Starting Gemma4EC RAG inference: $(date)"
hostname

# =======================
# USER CONFIGURATION
# =======================
PROJECT_ROOT=${PROJECT_ROOT:-$PWD}
SCRATCH_ROOT=${SCRATCH_ROOT:-/scratch/$USER}
CACHE_ROOT=${CACHE_ROOT:-"$SCRATCH_ROOT/.cache/gemma4ec"}

# Path to the LoRA adapter produced by run_train_chat.sh
ADAPTER_DIR=${ADAPTER_DIR:?Must set ADAPTER_DIR (path to best_model/ checkpoint)}

MODEL_ID=${MODEL_ID:-"google/txgemma-9b-chat"}

BRENDA_FILE=${BRENDA_FILE:-"/data/jarcagniriv/BRENDA/brenda_2026_1.txt"}
BRENDA_INDEX=${BRENDA_INDEX:-"$PROJECT_ROOT/chat/data/brenda_index.json"}

INPUT_CSV=${INPUT_CSV:-"$PROJECT_ROOT/data/ECReact/test.csv"}
OUTPUT_FILE=${OUTPUT_FILE:-"$SCRATCH_ROOT/gemma4ec/chat/results/rag_predictions.tsv"}

BATCH_SIZE=${BATCH_SIZE:-8}

# =======================
# ENVIRONMENT
# =======================
CONDA_ENV=${CONDA_ENV:-/scratch/$USER/conda_envs/gemma4ec}
export PATH="$CONDA_ENV/bin:$PATH"
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# =======================
# TOKENS
# =======================
if [[ -z "${HUGGINGFACE_TOKEN:-}" ]]; then
  HUGGINGFACE_TOKEN=$(cat ~/.huggingface/token 2>/dev/null || true)
fi
if [[ -z "${HUGGINGFACE_TOKEN:-}" ]]; then
  echo "ERROR: HUGGINGFACE_TOKEN not set"
  exit 1
fi

# =======================
# CACHE
# =======================
mkdir -p "$CACHE_ROOT" "$(dirname "$OUTPUT_FILE")" logs

export HF_HOME="$CACHE_ROOT/hf"
export TRANSFORMERS_CACHE="$CACHE_ROOT/hf/transformers"
export TORCH_HOME="$CACHE_ROOT/torch"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
umask 077

# =======================
# STEP 1 — Build BRENDA index (skip if already exists)
# =======================
if [[ ! -f "$BRENDA_INDEX" ]]; then
  echo "Building BRENDA index from $BRENDA_FILE …"
  python "$PROJECT_ROOT/chat/build_brenda_index.py" \
    --brenda_file "$BRENDA_FILE" \
    --output_file "$BRENDA_INDEX"
  echo "BRENDA index saved to $BRENDA_INDEX"
else
  echo "BRENDA index already exists: $BRENDA_INDEX (skipping build)"
fi

# =======================
# STEP 2 — RAG inference
# =======================
echo "Running RAG inference …"
python "$PROJECT_ROOT/chat/rag_infer.py" \
  --adapter_dir    "$ADAPTER_DIR" \
  --base_model_id  "$MODEL_ID" \
  --brenda_index   "$BRENDA_INDEX" \
  --input_csv      "$INPUT_CSV" \
  --output_file    "$OUTPUT_FILE" \
  --batch_size     "$BATCH_SIZE" \
  --hf_token       "$HUGGINGFACE_TOKEN"

echo "Finished RAG inference: $(date)"
echo "Results → $OUTPUT_FILE"
