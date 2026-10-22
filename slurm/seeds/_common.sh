# Sourced by every slurm/seeds/run_seed_*.sh script. Submit from the repo root.
set -euo pipefail
[[ -f "${PROJECT_ROOT:-$PWD}/config.sh" ]] && source "${PROJECT_ROOT:-$PWD}/config.sh"   # site paths (config.sh.example)

: "${SEED:=${SLURM_ARRAY_TASK_ID:-}}"   # array jobs: one task per seed
: "${SEED:=${POOL_JOB:+pool}}"
: "${SEED:?Set SEED (0-9)}"
PROJECT_ROOT=${PROJECT_ROOT:-$PWD}
SCRATCH_ROOT=${SCRATCH_ROOT:-$PWD/work}
CACHE_ROOT=${CACHE_ROOT:-"$SCRATCH_ROOT/.cache/gemma4ec"}

# Split set (data/ECReact_seeds_<SPLIT_SET>); the benchmark uses the stratified, deduplicated splits
SPLIT_SET=${SPLIT_SET:-strat_dedup}
SPLITS_DIR="$PROJECT_ROOT/data/ECReact_seeds_${SPLIT_SET}"
WORK_ROOT="${GEMMA4EC_WORK:-$SCRATCH_ROOT/gemma4ec}/seeds_${SPLIT_SET}"
SEED_DATA="$SPLITS_DIR/seed${SEED}"
SEED_WORK="$WORK_ROOT/seed${SEED}"
ENVS=${ENVS:-"$SCRATCH_ROOT/Envs"}   # conda envs of the competing methods (theia, becpred, claire, clean_ec)

[[ -n "${POOL_JOB:-}" || -f "$SEED_DATA/test.csv" ]] || { echo "ERROR: $SEED_DATA missing — run scripts/make_seed_splits.py"; exit 1; }
[[ -n "${POOL_JOB:-}" ]] || mkdir -p "$SEED_WORK"
mkdir -p "$PROJECT_ROOT/logs"

export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"
# Several jobs can share one GPU node: give each its own torch.distributed port
export MASTER_PORT=${MASTER_PORT:-$((20000 + ${SLURM_JOB_ID:-0} % 30000))}
export HF_HOME="$CACHE_ROOT/hf"
export HF_DATASETS_CACHE="$CACHE_ROOT/hf/datasets"
export WANDB_DIR="$CACHE_ROOT/wandb"
export WANDB_CONFIG_DIR="$CACHE_ROOT/wandb"
export TORCH_HOME="$CACHE_ROOT/torch"
export MPLCONFIGDIR="$CACHE_ROOT/matplotlib"

if [[ -z "${HUGGINGFACE_TOKEN:-}" && -f "$HOME/.huggingface/token" ]]; then
  export HUGGINGFACE_TOKEN=$(cat "$HOME/.huggingface/token")
fi

# API keys: private env file (chmod 600) with lines like `export GEMINI_API_KEYS=k1,k2`.
# Never paste keys into chat or commit them.
API_KEYS_FILE=${API_KEYS_FILE:-$HOME/.gemma4ec_api_keys}
if [[ -f "$API_KEYS_FILE" ]]; then
  if [[ "$(stat -c %a "$API_KEYS_FILE")" != 600 ]]; then
    echo "ERROR: $API_KEYS_FILE must be chmod 600"; exit 1
  fi
  set +x
  # shellcheck disable=SC1090
  source "$API_KEYS_FILE"
fi

echo "=========================================="
echo "Seed benchmark | seed=$SEED | $(basename "$0")"
echo "Data : $SEED_DATA"
echo "Work : $SEED_WORK"
echo "Host : $(hostname) | $(date)"
echo "=========================================="
