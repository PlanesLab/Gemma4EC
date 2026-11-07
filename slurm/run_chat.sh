#!/bin/bash
# Chat explanations on a GPU node (wraps chat/explain.sh).
# Usage: IN=reactions.csv OUT=chat_out sbatch slurm/run_chat.sh
#   evaluation set: IN=chat/eval/set/reactions.csv OUT=chat/eval/set/run sbatch slurm/run_chat.sh
#SBATCH --job-name=gemma4ec_chat
#SBATCH --partition=preemption-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=04:00:00
#SBATCH --requeue
#SBATCH --output=logs/chat_%j.out
set -euo pipefail
cd "${PROJECT_ROOT:-$PWD}"
[[ -f config.sh ]] && source config.sh
export HF_HUB_CACHE=${HF_HUB_CACHE:-$PWD/hfcache}
export HF_TOKEN=${HF_TOKEN:-$(cat ~/.huggingface/token 2>/dev/null || true)}
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
mkdir -p logs
bash chat/explain.sh "${IN:?set IN=<reactions.csv>}" "${OUT:-chat_out}"
