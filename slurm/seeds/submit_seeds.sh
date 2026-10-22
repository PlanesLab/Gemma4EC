#!/bin/bash
# Submit the ECReact 10-seed benchmark. Run from the repo root.
#
#   bash slurm/seeds/submit_seeds.sh
#   (API keys are read from ~/.gemma4ec_api_keys, chmod 600 — see results/seeds/README.md)
#
# Env overrides:
#   SEEDS="0 1 2 3 4 5 6 7 8 9"
#   METHODS="gemma4ec_9b gemma4ec_2b txgemma_noft theia becpred claire api"
#   API_MODELS="gemini-2.5-flash"   (one pool job per model; OpenAI models need a paid key)
#   DRY_RUN=1   (print sbatch commands only)
set -euo pipefail
[[ -f "${PROJECT_ROOT:-$PWD}/config.sh" ]] && source "${PROJECT_ROOT:-$PWD}/config.sh"   # site paths (config.sh.example)

SEEDS=${SEEDS:-"0 1 2 3 4 5 6 7 8 9"}
METHODS=${METHODS:-"gemma4ec_9b gemma4ec_2b txgemma_noft theia becpred claire api"}
API_MODELS=${API_MODELS:-"gemini-2.5-flash"}
D=slurm/seeds

: "${SPLIT_SET:=strat_dedup}"
export SPLIT_SET
[[ -d data/ECReact_seeds_${SPLIT_SET}/seed0 ]] || { echo "ERROR: data/ECReact_seeds_${SPLIT_SET} missing"; exit 1; }

if [[ " $METHODS " == *" api "* && -z "${DRY_RUN:-}" ]]; then
  KEYS=${API_KEYS_FILE:-$HOME/.gemma4ec_api_keys}
  [[ -f "$KEYS" ]] && source "$KEYS"
  echo "Checking API model IDs against your keys ..."
  ${GEMMA4EC_PY:-python} scripts/check_api_models.py $API_MODELS \
    || { echo "Fix API_MODELS (see: python scripts/check_api_models.py --list)"; exit 1; }
fi

sub() {  # sub <job-name> <script> [VAR=val ...]
  local name=$1 script=$2; shift 2
  local cmd=(sbatch --parsable --job-name="$name" --export="ALL,$(IFS=,; echo "$*")" "$D/$script")
  if [[ -n "${DRY_RUN:-}" ]]; then echo "${cmd[*]}"; else echo "$name -> $("${cmd[@]}")"; fi
}

# API models: one job per model on the deduplicated pool of all seed test sets
if [[ " $METHODS " == *" api "* ]]; then
  if [[ -z "${DRY_RUN:-}" ]]; then
    ${CLEAN_EC_PY:-python3} scripts/make_api_pool.py --prefill
  fi
  for A in $API_MODELS; do sub "api_${A}" run_api_pool.sh MODEL_NAME=$A; done
fi

# Local models: one SLURM job array per method (task id = seed), with a cap on
# concurrently running tasks (xlong allows 20 running jobs per user).
SEED_LIST=$(echo $SEEDS | tr ' ' ',')
arr() {  # arr <method> <script> <max-concurrent> [VAR=val ...]
  local m=$1 script=$2 lim=$3; shift 3
  # EXTRA_SBATCH: extra sbatch options for this submission (e.g. "-p preemption-gpu" or "--gres=gpu:2 ...")
  local cmd=(sbatch --parsable ${EXTRA_SBATCH:-} --job-name="${SPLIT_SET}_$m" --array="${SEED_LIST}%${ARRAY_LIMIT:-$lim}"
             --output="logs/${SPLIT_SET}_${m}_%A_%a.out" --export="ALL${*:+,$(IFS=,; echo "$*")}" "$D/$script")
  if [[ -n "${DRY_RUN:-}" ]]; then echo "${cmd[*]}"; else echo "$m -> array $("${cmd[@]}")"; fi
}

for M in $METHODS; do
  case $M in
    gemma4ec_9b)  arr gemma4ec_9b  run_seed_gemma4ec.sh     3 MODEL_SIZE=9b ;;
    gemma4ec_2b)  arr gemma4ec_2b  run_seed_gemma4ec.sh     2 MODEL_SIZE=2b ;;
    txgemma_noft) arr txgemma_noft run_seed_txgemma_noft.sh 3 ;;
    theia)        arr theia        run_seed_theia.sh        4 ;;
    becpred)      arr becpred      run_seed_becpred.sh      3 ;;
    claire)       arr claire       run_seed_claire.sh       4 ;;
    api) ;;
    *) echo "Unknown method: $M"; exit 1 ;;
  esac
done
