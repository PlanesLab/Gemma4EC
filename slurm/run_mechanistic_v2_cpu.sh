#!/bin/bash
# CPU variant of run_mechanistic_v2.sh (explain step only), for when no GPU is free. Same env variables.
#   CPU=1 VOTES=3 MAX_RETRIES=1 sbatch slurm/run_mechanistic_v2_cpu.sh
#SBATCH --job-name=mech_v2_cpu
#SBATCH --partition=general
#SBATCH --cpus-per-task=48
#SBATCH --mem=120G
#SBATCH --time=24:00:00
#SBATCH --output=logs/mechanistic_v2_cpu_%j.out
[[ -f "${PROJECT_ROOT:-$PWD}/config.sh" ]] && source "${PROJECT_ROOT:-$PWD}/config.sh"   # site paths (config.sh.example)
export CPU=1 OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-48}
exec bash slurm/run_mechanistic_v2.sh
