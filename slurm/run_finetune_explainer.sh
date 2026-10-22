#!/bin/bash
# LoRA fine-tuning of TxGemma-9B-Chat on teacher explanations (chat/finetune_explainer.py).
#SBATCH --job-name=ft_explainer
#SBATCH --partition=preemption-gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=10:00:00
#SBATCH --requeue
#SBATCH --output=logs/ft_explainer_%j.out
set -euo pipefail
[[ -f "${PROJECT_ROOT:-$PWD}/config.sh" ]] && source "${PROJECT_ROOT:-$PWD}/config.sh"   # site paths (config.sh.example)
cd "${PROJECT_ROOT:-$PWD}"
export HF_HUB_CACHE=${HF_HUB_CACHE:-$PWD/hfcache}
export HF_TOKEN=${HF_TOKEN:-$(cat ~/.huggingface/token 2>/dev/null || true)}
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
${GEMMA4EC_PY:-python} chat/finetune_explainer.py --teacher 'chat/ft_data/teacher_chunk*.json' --out_dir chat/ft_adapter
echo "Done: $(date)"
