#!/bin/bash
# SIMMER with its reference database built from this seed's TRAIN split (as ECNumberPrediction
# Case 2), via scripts/simmer_scaled.py — a vectorized re-implementation of SIMMER2_generic that
# reproduces the original exactly on the Rhea Case 2 split (--exact mode, 734/734 identical) and is
# run here in its batch-independent mode (96% identical top-1 vs exact on Rhea, 14x faster).
#
# Usage: SPLIT_SET=strat_dedup sbatch --array=0-9 slurm/seeds/run_seed_simmer_traindb.sh
#   NULL_MODE=per_class -> per-class significance null (sensitivity analysis, not the published
#   method); outputs simmer_traindb_perclass_raw.tsv / SIMMER_trainDB_perclass_predictions.tsv
#SBATCH --job-name=seed_simmer_traindb
#SBATCH --partition=general
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=110G
#SBATCH --output=logs/seed_simmer_traindb_%A_%a.out

source "${PROJECT_ROOT:-$PWD}/slurm/seeds/_common.sh"
PY="$ENVS/SIMMERenv/bin/python3"
OUT="$SEED_WORK/tools"
mkdir -p "$OUT"
NULL_MODE=${NULL_MODE:-modal}
DB_SPLITS=${DB_SPLITS:-train}     # train | trainval (reference DB = train + val)
TAG=""; [[ "$NULL_MODE" == "per_class" ]] && TAG="_perclass"
REF="$SEED_DATA/train.csv"; DBTAG="trainDB"; RAW="simmer_traindb"
if [[ "$DB_SPLITS" == "trainval" ]]; then
  REF="$OUT/simmer_trainval${TAG}_ref.csv"; DBTAG="trainvalDB"; RAW="simmer_trainvaldb"
  "$PY" -c "import pandas as pd,sys; pd.concat([pd.read_csv(f, dtype=str) for f in sys.argv[1:3]]).to_csv(sys.argv[3], index=False)" \
    "$SEED_DATA/train.csv" "$SEED_DATA/val.csv" "$REF"
fi

"$PY" -u "$PROJECT_ROOT/scripts/simmer_scaled.py" \
    --train "$REF" --queries "$SEED_DATA/test.csv" \
    --smiles_col rxn_smiles --ec_col ec --seed "$SEED" \
    --null "$NULL_MODE" --workers "${SLURM_CPUS_PER_TASK:-8}" --out "$OUT/${RAW}${TAG}_raw.tsv"

# scoring format: true_label, pred, smiles (row-aligned with test.csv)
"$PY" - "$SEED_DATA/test.csv" "$OUT/${RAW}${TAG}_raw.tsv" "$OUT/SIMMER_${DBTAG}${TAG}_predictions.tsv" <<'PY'
import sys, pandas as pd
t = pd.read_csv(sys.argv[1], dtype=str)
p = pd.read_csv(sys.argv[2], sep="\t", dtype=str, keep_default_na=False)
pd.DataFrame({"true_label": t["ec"], "pred": p["pred"], "smiles": t["rxn_smiles"]}).to_csv(sys.argv[3], sep="\t", index=False)
PY
echo "Done: $(date)"
