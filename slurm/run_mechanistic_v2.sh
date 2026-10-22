#!/bin/bash
# Gemma4EC mechanistic explanations v2: facts (RXNMapper/MCS + MetaNetX) -> inputs (candidate ECs, mechanism
# references from M-CSA / class cards, code-written summary and caveats) -> Gemma chat (EC vote, grounded
# explanation, self-check).
#
# Usage:
#   sbatch --partition=preemption-gpu slurm/run_mechanistic_v2.sh                       (TxGemma-9B-Chat)
#   MODEL_ID=/path/to/models/gemma-3-27b-it OUT_PREFIX=chat/prompts/v2_gemma3_27b \
#     sbatch --partition=preemption-gpu --gres=gpu:2 --mem=160G slurm/run_mechanistic_v2.sh
#   STEPS=attn,facts,prepare,explain N=50 ... for new reactions
#SBATCH --job-name=gemma4ec_mech_v2
#SBATCH --partition=general
#SBATCH --gres=gpu:1
#SBATCH --constraint=a100
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=08:00:00
#SBATCH --requeue
#SBATCH --output=logs/mechanistic_v2_%j.out
set -euo pipefail
[[ -f "${PROJECT_ROOT:-$PWD}/config.sh" ]] && source "${PROJECT_ROOT:-$PWD}/config.sh"   # site paths (config.sh.example)
cd "${PROJECT_ROOT:-$PWD}"
PY=${GEMMA4EC_PY:-python}
export HF_HUB_CACHE=${HF_HUB_CACHE:-$PWD/hfcache}
export HF_TOKEN=${HF_TOKEN:-$(cat ~/.huggingface/token 2>/dev/null || true)}
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
ATTN_DIR=${ATTN_DIR:-attn_out}
STEPS=${STEPS:-explain}
MODEL_ID=${MODEL_ID:-google/txgemma-9b-chat}
INPUTS=${INPUTS:-chat/prompts/v2_inputs.json}
OUT_PREFIX=${OUT_PREFIX:-chat/prompts/v2_txgemma9b}
# teacher runs for fine-tuning data: one array task per chunk attn_ft/chunk<N>
if [[ -n "${CHUNKED:-}" && -n "${SLURM_ARRAY_TASK_ID:-}" ]]; then
    ATTN_DIR=attn_ft/chunk${SLURM_ARRAY_TASK_ID}
    INPUTS=$ATTN_DIR/v2_inputs.json
    OUT_PREFIX=chat/ft_data/teacher_chunk${SLURM_ARRAY_TASK_ID}
    mkdir -p chat/ft_data
fi

[[ $STEPS == *attn* ]]    && $PY infer_attention.py --n "${N:-10}" --output_dir "$ATTN_DIR"
[[ $STEPS == *facts* ]]   && ${RXNMAPPER_PY:-python} chat/reaction_facts.py --attn_dir "$ATTN_DIR"
[[ $STEPS == *prepare* ]] && $PY chat/prepare_v2.py --attn_dir "$ATTN_DIR" --out "$INPUTS"
[[ $STEPS == *explain* ]] && $PY chat/explain_v2.py --inputs "$INPUTS" --model_id "$MODEL_ID" --out_prefix "$OUT_PREFIX" \
                               --votes "${VOTES:-5}" --max_retries "${MAX_RETRIES:-2}" ${ADAPTER:+--adapter "$ADAPTER"} ${Q4:+--load_in_4bit} ${CPU:+--cpu}
echo "Done: $(date)"
