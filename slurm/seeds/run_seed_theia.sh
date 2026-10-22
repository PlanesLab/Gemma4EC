#!/bin/bash
# Train + evaluate the Theia DRFP-MLP baseline on one seed split.
#
# Usage: SEED=0 sbatch slurm/seeds/run_seed_theia.sh
#SBATCH --job-name=seed_theia
#SBATCH --partition=general
#SBATCH --qos=long
#SBATCH --time=06:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64GB
#SBATCH --output=logs/seed_theia_%j.out

source "${PROJECT_ROOT:-$PWD}/slurm/seeds/_common.sh"
OUT="$SEED_WORK/theia"
mkdir -p "$OUT"

"$ENVS/gemma4ec/bin/python" -u "$PROJECT_ROOT/benchmarking/theia/train_theia.py" \
    --train_csv  "$SEED_DATA/train.csv" \
    --val_csv    "$SEED_DATA/val.csv" \
    --test_csv   "$SEED_DATA/test.csv" \
    --output_dir "$OUT"

echo "Done: $(date)"
