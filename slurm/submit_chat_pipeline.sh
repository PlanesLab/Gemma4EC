#!/bin/bash
# Submit the full chat pipeline:
#   Job 1 — finetune txgemma-9b-chat (4 GPUs)
#   Job 2 — build BRENDA index + RAG inference (1 GPU, runs after job 1)
#
# Usage:
#   cd Gemma4EC
#   bash slurm/submit_chat_pipeline.sh

set -euo pipefail

PROJECT_ROOT=${PROJECT_ROOT:-$PWD}
SCRATCH_ROOT=${SCRATCH_ROOT:-/scratch/$USER}

# ── Resolve tokens ─────────────────────────────────────────────────────────
if [[ -z "${HUGGINGFACE_TOKEN:-}" ]]; then
  HUGGINGFACE_TOKEN=$(cat ~/.huggingface/token 2>/dev/null || true)
fi
if [[ -z "${HUGGINGFACE_TOKEN:-}" ]]; then
  echo "ERROR: HUGGINGFACE_TOKEN not set and ~/.huggingface/token not found"; exit 1
fi

if [[ -z "${WANDB_API_KEY:-}" ]]; then
  WANDB_API_KEY=$(grep -A2 "api.wandb.ai" ~/.netrc 2>/dev/null \
    | grep password | awk '{print $2}' || true)
fi

# Export so sbatch inherits them via the default --export=ALL
export PROJECT_ROOT HUGGINGFACE_TOKEN WANDB_API_KEY
export ADAPTER_DIR="${SCRATCH_ROOT}/gemma4ec/chat/checkpoints/best_model"

# ── Job 1: finetune ────────────────────────────────────────────────────────
JOB1=$(sbatch --parsable "$PROJECT_ROOT/slurm/run_train_chat.sh")
echo "Submitted finetune job: $JOB1"

# ── Job 2: RAG inference (only if job 1 exits 0) ──────────────────────────
JOB2=$(sbatch --parsable --dependency=afterok:"$JOB1" \
  "$PROJECT_ROOT/slurm/run_rag_infer.sh")
echo "Submitted RAG inference job: $JOB2 (depends on $JOB1)"

echo ""
echo "Monitor with:"
echo "  squeue -u $USER"
echo "  tail -f $PROJECT_ROOT/logs/train_chat_${JOB1}.out"
echo "  tail -f $PROJECT_ROOT/logs/rag_infer_${JOB2}.out"
