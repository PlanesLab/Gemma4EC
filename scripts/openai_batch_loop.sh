#!/bin/bash
# Drive scripts/openai_batch_pool.py chunk by chunk: wait -> collect -> submit next, until the
# pool is done, a batch fails, or the spend cap refuses. Usage:
#   SPLIT_SET=strat_dedup nohup bash scripts/openai_batch_loop.sh gpt-4.1-mini 8000 > logs/openai_batch_loop.log 2>&1 &
set -uo pipefail
MODEL=${1:-gpt-4.1-mini}; CHUNK=${2:-8000}
cd "$(dirname "$0")/.."
[[ -f config.sh ]] && source config.sh   # site paths (config.sh.example)
source ~/.gemma4ec_api_keys
export SPLIT_SET=${SPLIT_SET:-strat_dedup}
PY=${GEMMA4EC_PY:-python}
O="$PY scripts/openai_batch_pool.py"
for round in $(seq 1 20); do
  while true; do
    S=$($O status --model "$MODEL" 2>&1 | tail -1); echo "$(date '+%F %T') $S"
    ST=$(echo "$S" | awk '{print $2}')   # status word only (the counts contain "failed=0")
    [[ "$ST" == completed ]] && break
    [[ "$ST" =~ ^(failed|expired|cancelled)$ || "$S" =~ Error|Traceback ]] && { echo "batch ended badly - stopping"; exit 1; }
    sleep 120
  done
  $O collect --model "$MODEL" || exit 1
  OUT=$($O submit --model "$MODEL" --limit "$CHUNK" 2>&1); echo "$OUT" | grep -E "^\[submit\]|Nothing|REFUSED|Error"
  echo "$OUT" | grep -q "created" || { echo "no new batch submitted - done/stopped"; break; }
done
$PY scripts/fanout_api_predictions.py --models "${MODEL//./_}"
echo "finished $(date)"
