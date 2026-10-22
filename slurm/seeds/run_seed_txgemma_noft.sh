#!/bin/bash
# Base TxGemma-9b-predict (no fine-tuning) on one seed's test set.
# Default prompt = EC_NUMBER_PROMPT_API (same as the API baselines); override with TEMPLATE_KEY.
#
# Usage: SEED=0 sbatch slurm/seeds/run_seed_txgemma_noft.sh
#SBATCH --job-name=seed_txgemma_noft
#SBATCH --partition=general
#SBATCH --qos=long
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --constraint=a100
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=100GB
#SBATCH --output=logs/seed_txgemma_noft_%j.out

source "${PROJECT_ROOT:-$PWD}/slurm/seeds/_common.sh"
TEMPLATE_KEY=${TEMPLATE_KEY:-EC_NUMBER_PROMPT_API}
OUT="$SEED_WORK/txgemma_noft"
mkdir -p "$OUT"

"$ENVS/gemma4ec/bin/python" -u "$PROJECT_ROOT/predict_zeroshot.py" \
    --test_csv "$SEED_DATA/test.csv" \
    --output_folder "$OUT" \
    --prompts_json_path "$PROJECT_ROOT/prompts/prompts.json" \
    --template_key "$TEMPLATE_KEY" \
    --model_id google/txgemma-9b-predict \
    --save_directory "$SCRATCH_ROOT/gemma4ec/base_models/txgemma_9b" \
    --eval_batch_size 8 \
    --max_retries 5 \
    --hf_token "$HUGGINGFACE_TOKEN" \
    --disable_wandb

echo "Done: $(date)"
