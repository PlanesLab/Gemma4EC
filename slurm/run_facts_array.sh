#!/bin/bash
# Reaction facts (chat/reaction_facts.py) for fine-tuning chunks attn_ft/chunk<N>, one array task per chunk (CPU).
#   sbatch --array=0-7 slurm/run_facts_array.sh
#SBATCH --job-name=facts_ft
#SBATCH --partition=general
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --time=12:00:00
#SBATCH --output=logs/facts_ft_%A_%a.out
set -euo pipefail
[[ -f "${PROJECT_ROOT:-$PWD}/config.sh" ]] && source "${PROJECT_ROOT:-$PWD}/config.sh"   # site paths (config.sh.example)
cd "${PROJECT_ROOT:-$PWD}"
export OMP_NUM_THREADS=4
${RXNMAPPER_PY:-python} chat/reaction_facts.py --attn_dir "attn_ft/chunk${SLURM_ARRAY_TASK_ID}"
