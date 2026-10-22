#!/bin/bash
# Zero-shot API model on the deduplicated reaction pool of all seed test sets
# (data/ECReact_seeds/api_pool.csv), then fan the answers out to every seed.
# Each unique reaction is queried once per model; reactions already answered
# (this pool TSV, or reused from the original test run) are skipped.
#
# Free tier: when the daily quota (Gemini) or free token allowance (OpenAI) is used up, the job stops, and if it made progress
# it re-submits itself for after the quota reset (also when another job used up a shared allowance) (09:05 local ≈ midnight Pacific).
#
# Usage: MODEL_NAME=gemini-2.5-flash sbatch slurm/seeds/run_api_pool.sh
#   API_WORKERS (default 1), API_MIN_INTERVAL seconds between requests (default 6 = 10 RPM),
#   AUTO_RESUBMIT (default 1), MAX_RESUBMITS (default 90)
#SBATCH --job-name=api_pool
#SBATCH --partition=general
#SBATCH --qos=long
#SBATCH --time=1-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16gb
#SBATCH --output=logs/api_pool_%j.out

POOL_JOB=1 source "${PROJECT_ROOT:-$PWD}/slurm/seeds/_common.sh"
: "${MODEL_NAME:?Set MODEL_NAME}"
# OpenAI: stay inside the data-sharing complimentary daily tokens (ledger shared by all jobs;
# OPENAI_DAILY_CAP_LARGE / _MINI override the defaults of 950K / 9.5M tokens per UTC day).
export OPENAI_FREE_ONLY=${OPENAI_FREE_ONLY:-1}
PY="$ENVS/gemma4ec/bin/python"
POOL_DIR="$WORK_ROOT/api_pool"
POOL_CSV="${POOL_CSV:-$SPLITS_DIR/api_pool.csv}"
SAFE=${MODEL_NAME//./_}
TSV="$POOL_DIR/predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API.${SAFE}.tsv"

if [[ "$MODEL_NAME" == gemini-* ]]; then
  [[ -n "${GEMINI_API_KEYS:-}${GEMINI_API_KEY:-}${GOOGLE_API_KEY:-}" ]] || { echo "ERROR: no Gemini key (see $API_KEYS_FILE)"; exit 1; }
else
  [[ -n "${OPENAI_API_KEY:-}" ]] || { echo "ERROR: OPENAI_API_KEY not set (see $API_KEYS_FILE)"; exit 1; }
fi
[[ -f "$POOL_CSV" ]] || { echo "ERROR: $POOL_CSV missing — run scripts/make_api_pool.py --prefill"; exit 1; }

n_done() { [[ -f "$TSV" ]] && "$PY" -c "import pandas as pd,sys; print(int(pd.read_csv(sys.argv[1],sep='\t').pred_well_formed.astype(str).str.lower().eq('true').sum()))" "$TSV" || echo 0; }
BEFORE=$(n_done)

RC=0
"$PY" -u "$PROJECT_ROOT/predict_api.py" \
    --raw_data_file "$POOL_CSV" \
    --processed_data_folder "$POOL_DIR/processed" \
    --output_folder "$POOL_DIR" \
    --prompts_json_path "$PROJECT_ROOT/prompts/prompts.json" \
    --template_key EC_NUMBER_PROMPT_API \
    --template_alias EC_NUMBER \
    --model_name "$MODEL_NAME" \
    --workers "${API_WORKERS:-1}" \
    --min_interval "${API_MIN_INTERVAL:-6}" || RC=$?
[[ $RC == 0 || $RC == 3 ]] || { echo "predict_api failed (exit $RC)"; exit $RC; }

"$PY" "$PROJECT_ROOT/scripts/fanout_api_predictions.py" --models "$SAFE"

AFTER=$(n_done); TOTAL=$(($(wc -l < "$POOL_CSV") - 1))
echo "[api_pool] $MODEL_NAME: $BEFORE → $AFTER / $TOTAL well-formed"

N=${RESUBMIT_N:-0}
if [[ "${AUTO_RESUBMIT:-1}" == 1 && $AFTER -lt $TOTAL && ( $AFTER -gt $BEFORE || $RC == 3 ) && $N -lt ${MAX_RESUBMITS:-90} ]]; then
  BEGIN=$(date -d "tomorrow 09:05" +%Y-%m-%dT%H:%M)
  sbatch --job-name="api_${MODEL_NAME}" --begin="$BEGIN" \
    --export="ALL,MODEL_NAME=$MODEL_NAME,RESUBMIT_N=$((N + 1))" "$PROJECT_ROOT/slurm/seeds/run_api_pool.sh"
  echo "[api_pool] re-submitted for $BEGIN (resubmit $((N + 1)))"
fi
echo "Done: $(date)"
