#!/bin/bash
# SelenzymeRF with a reference database built from this seed's TRAIN split
# (scripts/selenzyme_traindb.py seed_db), queried with the seed's test reactions.
# Array task -> (seed, chunk): seed = id / CHUNKS, chunk = id % CHUNKS.
#
# Usage: SPLIT_SET=strat_dedup CHUNKS=4 sbatch --array=0-39 slurm/seeds/run_seed_selenzyme_traindb.sh
#SBATCH --job-name=seed_selenzyme_traindb
#SBATCH --partition=general
#SBATCH --time=16:00:00
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --output=logs/seed_selenzyme_traindb_%A_%a.out

CHUNKS=${CHUNKS:-4}
TASK=${SLURM_ARRAY_TASK_ID:?run as an array}
export SEED=$((TASK / CHUNKS))
K=$((TASK % CHUNKS))
source "${PROJECT_ROOT:-$PWD}/slurm/seeds/_common.sh"
ECN=${ECN_ROOT:?set ECN_ROOT in config.sh}
PY="$ENVS/clean_ec/bin/python3"
DB_SPLITS=${DB_SPLITS:-train}   # train | trainval (reference DB = train + val)
SUF=""; [[ "$DB_SPLITS" == "trainval" ]] && SUF="_trainval"
DB="$SCRATCH_ROOT/gemma4ec/selenzyme_traindb/db/seed${SEED}${SUF}"
OUT="$SEED_WORK/tools/selenzyme_traindb${SUF}"
RES="$OUT/chunk_${K}"
PORT=$((5200 + (SLURM_JOB_ID % 300) * 40 + TASK % 40))
MOUNT="selenzyme2_traindb${SUF}_${SLURM_JOB_ID}_${TASK}_m"  # trailing _m: pkill -f on task 3 must not match tasks 30-39
[[ -f "$DB/reac_prop.tsv" ]] || { echo "ERROR: $DB missing — run selenzyme_traindb.py seed_db --seed $SEED"; exit 1; }
mkdir -p "$RES"
module load Apptainer 2>/dev/null || true

"$PY" - "$SEED_DATA/test.csv" "$K" "$CHUNKS" "$OUT/query_${K}.csv" <<'PY'
import sys, numpy as np, pandas as pd
t = pd.read_csv(sys.argv[1], dtype=str)
k, n = int(sys.argv[2]), int(sys.argv[3])
idx = np.array_split(np.arange(len(t)), n)[k]
# ECReact has a stray '->>' arrow in ~11% of SMILES; Selenzyme answers those with its help page
smi = t["rxn_smiles"].iloc[idx].str.replace("->>", ">>", regex=False).values
pd.DataFrame({"Reaction": [f"Q{i}" for i in idx], "reaction_smiles": smi}).to_csv(sys.argv[4], index=False)
print(f"seed chunk {k}: {len(idx)} queries")
PY

cd "$ECN"
CODE=methods/SelenzymeRF/SelenzymeRF_code
cleanup() { pkill -f "$MOUNT" 2>/dev/null || true; rm -rf "$CODE/$MOUNT"; }
trap cleanup EXIT
SELENZYME2_DIR="$MOUNT" SELENZYME_PORT="$PORT" DATA_SOURCE_DIR="$DB" bash "$CODE/start_server_noninteractive.sh" &
for i in $(seq 1 160); do curl -s -o /dev/null "http://localhost:$PORT/" && break; sleep 15; done
curl -s -o /dev/null "http://localhost:$PORT/" || { echo "ERROR: server did not come up"; exit 1; }
echo "server up on :$PORT after ~$((i * 15)) s"

"$PY" methods/SelenzymeRF/SelenzymeRF_scripts/query_selenzyme.py \
    --csv_file "$OUT/query_${K}.csv" --results_folder "$RES" \
    --server_url "http://localhost:$PORT" \
    --reaction_name_column Reaction --reaction_smiles_column reaction_smiles
"$PY" methods/SelenzymeRF/SelenzymeRF_scripts/get_results.py \
    --folder "$RES" --ec_column "EC Number" --output "$OUT/chunk_${K}.csv"
echo "Done: $(date)"
