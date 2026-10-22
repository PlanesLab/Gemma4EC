#!/bin/bash
# Predict a seed's test set with the best adapter saved during training — for runs
# killed after their best checkpoint was written (same eval code as main.py's test run).
#
# Usage: SEED=8 MODEL_SIZE=9b sbatch slurm/seeds/run_seed_gemma4ec_predict_best.sh
#SBATCH --job-name=seed_g4ec_predbest
#SBATCH --partition=general
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --constraint=a100
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=100GB
#SBATCH --output=logs/seed_g4ec_predbest_%j.out

source "${PROJECT_ROOT:-$PWD}/slurm/seeds/_common.sh"
MODEL_SIZE=${MODEL_SIZE:-9b}
RUN="$SEED_WORK/gemma4ec_${MODEL_SIZE}"
TMP="$RUN/predict_best"
[[ -d "$RUN/results/best" ]] || { echo "ERROR: no best adapter in $RUN/results/best"; exit 1; }
mkdir -p "$TMP"

"$ENVS/gemma4ec/bin/accelerate" launch --num_processes 1 --main_process_port "$MASTER_PORT" \
  "$PROJECT_ROOT/predict.py" \
    --raw_data_file "$SEED_DATA/test.csv" \
    --processed_data_folder "$TMP/processed" \
    --output_folder "$TMP" \
    --model_checkpoint_folder "$RUN/results/best" \
    --model_id "google/txgemma-${MODEL_SIZE}-predict" \
    --save_directory "$SCRATCH_ROOT/gemma4ec/base_models/txgemma_${MODEL_SIZE}" \
    --prompts_json_path "$PROJECT_ROOT/prompts/prompts.json" \
    --template_key EC_NUMBER_PROMPT_2 \
    --eval_batch_size 8 \
    --hf_token "$HUGGINGFACE_TOKEN"

OUT=$(ls -t "$TMP"/predictions_pred.*.tsv | head -1)
cp "$OUT" "$RUN/results/predictions_test.EC_NUMBER.EC_NUMBER_PROMPT_2.from_best.tsv"
echo "Saved → $RUN/results/predictions_test.EC_NUMBER.EC_NUMBER_PROMPT_2.from_best.tsv ($(wc -l < "$OUT") lines)"
