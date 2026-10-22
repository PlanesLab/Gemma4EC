#!/bin/bash
# Drive scripts/gemini_batch_pool.py chunk by chunk: wait → collect → submit next,
# until the pool is done, a batch fails, or the budget guard refuses.
# Usage: nohup bash scripts/gemini_batch_loop.sh gemini-3.1-flash-lite 15000 > logs/gemini_batch_loop.log 2>&1 &
set -uo pipefail
MODEL=${1:-gemini-3.1-flash-lite}; CHUNK=${2:-15000}
cd "$(dirname "$0")/.."
[[ -f config.sh ]] && source config.sh   # site paths (config.sh.example)
source ~/.gemma4ec_api_keys
PY=${GEMMA4EC_PY:-python}
G="$PY scripts/gemini_batch_pool.py"
for round in $(seq 1 8); do
  while true; do
    S=$($G status --model "$MODEL" 2>&1 | tail -1); echo "$(date '+%F %T') $S"
    [[ "$S" == *SUCCEEDED* ]] && break
    [[ "$S" =~ FAILED|CANCELLED|EXPIRED|Error ]] && { echo "batch ended badly — stopping"; exit 1; }
    sleep 120
  done
  $G collect --model "$MODEL" || exit 1
  OUT=$($G submit --model "$MODEL" --limit "$CHUNK" 2>&1); echo "$OUT" | grep -E "^\[submit\]|Nothing|REFUSED|Error"
  echo "$OUT" | grep -q "created" || { echo "no new batch submitted — done/stopped"; break; }
done
$PY scripts/fanout_api_predictions.py --models "${MODEL//./_}"
echo "finished $(date)"
