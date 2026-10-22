#!/bin/bash
# Fine-tune Gemma4EC (TxGemma + LoRA) on one ECReact seed split and predict its test set.
# Same hyperparameters as slurm/run_train_gemma4ec_9b.sh (2b differs only in eval batch size).
#
# Usage: SEED=0 MODEL_SIZE=9b sbatch slurm/seeds/run_seed_gemma4ec.sh
#SBATCH --job-name=seed_gemma4ec
#SBATCH --partition=general
#SBATCH --qos=xlong
#SBATCH --time=5-00:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:4
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=4
#SBATCH --mem=300gb
#SBATCH --output=logs/seed_gemma4ec_%j.out

source "${PROJECT_ROOT:-$PWD}/slurm/seeds/_common.sh"
MODEL_SIZE=${MODEL_SIZE:-9b}

export RAW_DATA_FOLDER="$SEED_DATA"
export USE_TEST=True
export PROCESSED_DATA_FOLDER="$SEED_WORK/gemma4ec_${MODEL_SIZE}/processed"
export OUTPUT_FOLDER="$SEED_WORK/gemma4ec_${MODEL_SIZE}/results"
export MODEL_ID="google/txgemma-${MODEL_SIZE}-predict"
export SAVE_DIRECTORY="$SCRATCH_ROOT/gemma4ec/base_models/txgemma_${MODEL_SIZE}"
export WANDB_RUN_NAME="seed${SEED}_${MODEL_SIZE}"
export WANDB_GROUP="ECReact_${SPLIT_SET}_${MODEL_SIZE}"
[[ -n "${WANDB_ENTITY:-}" ]] && export WANDB_ENTITY   # set in config.sh to log to a W&B team
export WANDB_PROJECT=${WANDB_PROJECT:-Gemma4EC-partitions}
[[ "$MODEL_SIZE" == "2b" ]] && export EVAL_BATCH_SIZE=16
# Keep the effective batch at 128 (8 per GPU x GPUs x accumulation) whatever GPU count the job got,
# so runs on 2 GPUs train identically to the 4-GPU runs.
N_GPU=$(nvidia-smi --list-gpus | wc -l)
export GRAD_ACCUM_STEPS=$((16 / N_GPU))
echo "GPUs: $N_GPU -> grad accumulation $GRAD_ACCUM_STEPS (effective batch $((8 * N_GPU * GRAD_ACCUM_STEPS)))"

bash "$PROJECT_ROOT/slurm/run_train_gemma4ec_9b.sh"
