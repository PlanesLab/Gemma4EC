#!/bin/bash
# SelenzymeRF with its published reference DB (data_2023) on one chunk of the deduplicated
# seed test pool. One local Apptainer server per task, on its own port and mount dir.
#
# Usage: sbatch --array=0-9 slurm/seeds/run_tool_selenzyme.sh   (CHUNK_SIZE=3761)
#SBATCH --job-name=tool_selenzyme
#SBATCH --partition=general
#SBATCH --time=16:00:00
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --output=logs/tool_selenzyme_%A_%a.out

POOL_JOB=1 source "${PROJECT_ROOT:-$PWD}/slurm/seeds/_common.sh"
K=${SLURM_ARRAY_TASK_ID:?run as an array}
CHUNK_SIZE=${CHUNK_SIZE:-3761}
ECN=${ECN_ROOT:?set ECN_ROOT in config.sh}
PY="$ENVS/clean_ec/bin/python3"
OUT="$WORK_ROOT/tools/selenzyme"
RES="$OUT/chunk_${K}"
PORT=$((5200 + (SLURM_JOB_ID % 400) * 10 + K % 10))
MOUNT="selenzyme2_ecreact_${SLURM_JOB_ID}_${K}_m"  # trailing _m: pkill -f on task 3 must not match tasks 30-39
mkdir -p "$RES"
module load Apptainer 2>/dev/null || true

"$PY" - "${POOL_CSV:-$SPLITS_DIR/api_pool.csv}" "$K" "$CHUNK_SIZE" "$OUT/query_${K}.csv" <<'PY'
import sys, pandas as pd
pool, k, n, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
df = pd.read_csv(pool, dtype=str).iloc[k * n:(k + 1) * n]
pd.DataFrame({"Reaction": [f"Q{i}" for i in df.index], "reaction_smiles": df["rxn_smiles"]}).to_csv(out, index=False)
print(f"chunk {k}: {len(df)} queries")
PY

cd "$ECN"
CODE=methods/SelenzymeRF/SelenzymeRF_code
cleanup() { pkill -f "$MOUNT" 2>/dev/null || true; rm -rf "$CODE/$MOUNT"; }
trap cleanup EXIT
SELENZYME2_DIR="$MOUNT" SELENZYME_PORT="$PORT" bash "$CODE/start_server_noninteractive.sh" &

echo "waiting for server on :$PORT"
for i in $(seq 1 120); do
  curl -s -o /dev/null "http://localhost:$PORT/" && break
  sleep 15
done
curl -s -o /dev/null "http://localhost:$PORT/" || { echo "ERROR: server did not come up"; exit 1; }
echo "server up after ~$((i * 15)) s"

"$PY" methods/SelenzymeRF/SelenzymeRF_scripts/query_selenzyme.py \
    --csv_file "$OUT/query_${K}.csv" --results_folder "$RES" \
    --server_url "http://localhost:$PORT" \
    --reaction_name_column Reaction --reaction_smiles_column reaction_smiles
"$PY" methods/SelenzymeRF/SelenzymeRF_scripts/get_results.py \
    --folder "$RES" --ec_column "EC Number" --output "$OUT/chunk_${K}.csv"
echo "Done: $(date)"
