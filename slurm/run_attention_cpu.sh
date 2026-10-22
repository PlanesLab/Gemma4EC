#!/bin/bash
# Gemma4EC prediction + attention for reactions in a CSV, on CPU (infer_attention.py CPU fallback).
#   TEST_CSV=attn_small/test_one.csv OUT=attn_small N=1 sbatch --partition=preemption slurm/run_attention_cpu.sh
#SBATCH --job-name=attn_cpu
#SBATCH --cpus-per-task=11
#SBATCH --mem=80G
#SBATCH --time=12:00:00
#SBATCH --output=logs/attn_cpu_%j.out
set -euo pipefail
[[ -f "${PROJECT_ROOT:-$PWD}/config.sh" ]] && source "${PROJECT_ROOT:-$PWD}/config.sh"   # site paths (config.sh.example)
cd "${PROJECT_ROOT:-$PWD}"
export HF_HUB_CACHE=${HF_HUB_CACHE:-$PWD/hfcache} OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-11}
export HF_TOKEN=${HF_TOKEN:-$(cat ~/.huggingface/token 2>/dev/null || true)}
${GEMMA4EC_PY:-python} infer_attention.py --test_csv "$TEST_CSV" --n "${N:-1}" --output_dir "$OUT"
echo "Done: $(date)"
