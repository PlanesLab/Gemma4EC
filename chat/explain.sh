#!/bin/bash
# Explain Gemma4EC predictions in natural language: the whole chat pipeline in one command.
#
#   bash chat/explain.sh reactions.csv [out_dir]
#
# reactions.csv needs a column `rxn_smiles` (an optional `ec` column with the true EC is shown for comparison).
# Output: <out_dir>/explanations.md (readable report) and explanations.json.
#
# Steps: 1 Gemma4EC prediction + attention  2 reaction facts (atom mapping, names)  3 candidate enzymes and
# mechanism references  4 TxGemma-9B-Chat explanation. Paths and interpreters come from config.sh.
# Options (environment): CHAT_MODEL (default google/txgemma-9b-chat), ADAPTER (default GEMMA4EC_ADAPTER from config.sh),
# CPU=1 to run the chat model on CPU, VOTES / MAX_RETRIES (default 5 / 2), MARGIN (ranking lead above which no vote is
# taken, default 0.2), DROP_BROKEN=1 to skip records that fail the record check (fragments, no bond change).
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -f config.sh ]] && source config.sh

IN=${1:?usage: bash chat/explain.sh reactions.csv [out_dir]}
OUT=${2:-chat_out}
PY=${GEMMA4EC_PY:-python}
RX=${RXNMAPPER_PY:-python}
mkdir -p "$OUT"

ADAPTER=${ADAPTER:-${GEMMA4EC_ADAPTER:-}}
# peft falls back to the Hub when the path is missing, so a typo surfaces as an auth or download
# error four minutes into a GPU job. Check it here instead.
if [[ -z "$ADAPTER" ]]; then
    echo "error: set GEMMA4EC_ADAPTER in config.sh, or pass ADAPTER=..." >&2; exit 1
fi
if [[ ! -f "$ADAPTER/adapter_config.json" ]]; then
    echo "error: no adapter_config.json in '$ADAPTER'" >&2; exit 1
fi

echo "[1/4] Gemma4EC prediction and attention"
"$PY" infer_attention.py --test_csv "$IN" --n 0 --adapter_path "$ADAPTER" \
    --output_dir "$OUT" ${LOAD_IN_4BIT:+--load_in_4bit}

echo "[2/4] Reaction facts"
"$RX" chat/reaction_facts.py --attn_dir "$OUT"

echo "[3/4] Candidate enzymes and mechanism references"
"$PY" chat/prepare_chat.py --attn_dir "$OUT" --out "$OUT/chat_inputs.json" ${DROP_BROKEN:+--drop_broken}

echo "[4/4] Chat explanation"
"$PY" chat/explain_chat.py --inputs "$OUT/chat_inputs.json" --out_prefix "$OUT/explanations" \
    --model_id "${CHAT_MODEL:-google/txgemma-9b-chat}" --votes "${VOTES:-5}" --max_retries "${MAX_RETRIES:-2}" --margin "${MARGIN:-0.2}" \
    ${CPU:+--cpu}

echo "Done: $OUT/explanations.md"
