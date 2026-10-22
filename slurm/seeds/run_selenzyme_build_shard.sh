#!/bin/bash
# Build Selenzyme compound + reacting-fragment fingerprints for one shard of ECReact reactions,
# with Selenzyme's own data_update/make_fingerprint_atomMap.py inside its Apptainer image.
# Usage: sbatch --array=0-19 slurm/seeds/run_selenzyme_build_shard.sh
#SBATCH --job-name=selenzyme_build
#SBATCH --partition=general
#SBATCH --time=08:00:00
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=24G
#SBATCH --output=logs/selenzyme_build_%A_%a.out
set -euo pipefail
K=${SLURM_ARRAY_TASK_ID:?}
W=${GEMMA4EC_WORK:-$PWD/work}/selenzyme_traindb
CODE=${ECN_ROOT:?set ECN_ROOT in config.sh}/methods/SelenzymeRF/SelenzymeRF_code
module load Apptainer 2>/dev/null || true
mkdir -p "$W/built/shard$K"
cd "$CODE"
apptainer exec --bind /scratch build/selenzyme.sif \
    python data_update/make_fingerprint_atomMap.py "$W/built/shard$K" "$W/raw/shard$K"
echo "Done: $(date)"
