#!/bin/bash
# Download the Mechanism and Catalytic Site Atlas (M-CSA, EMBL-EBI; Ribeiro et al., NAR 2018) and build the
# mechanism index used by the chat explanations (chat/data/mcsa_index.json). Run once from anywhere.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -f config.sh ]] && source config.sh
mkdir -p chat/data/mcsa
API="https://www.ebi.ac.uk/thornton-srv/m-csa/api/entries/?format=json&page_size=100"
page=1
while :; do
    f=chat/data/mcsa/entries_p${page}.json
    curl -sf -m 300 "${API}&page=${page}" -o "$f" || { rm -f "$f"; break; }
    grep -q '"next":null' "$f" && break
    page=$((page + 1))
done
"${GEMMA4EC_PY:-python}" chat/build_mcsa_index.py
