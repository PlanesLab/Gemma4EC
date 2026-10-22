#!/bin/bash
# Merge the Selenzyme fingerprint shards and assemble one train-only reference DB per seed.
# Fingerprints are (un)pickled inside build/selenzyme.sif so the server's RDKit can read them;
# train reaction IDs come from clean_ec (same RDKit as `prepare`, which keyed the reactions).
#SBATCH --job-name=selenzyme_dbs
#SBATCH --partition=general
#SBATCH --time=03:00:00
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --output=logs/selenzyme_dbs_%j.out
set -euo pipefail
cd "${PROJECT_ROOT:-$PWD}"
PY=${CLEAN_EC_PY:-python3}
SIF=${ECN_ROOT:?set ECN_ROOT in config.sh}/methods/SelenzymeRF/SelenzymeRF_code/build/selenzyme.sif
module load Apptainer 2>/dev/null || true
SEL() { apptainer exec --bind /scratch "$SIF" python scripts/selenzyme_traindb.py "$@"; }
DB_SPLITS=${DB_SPLITS:-train}   # train | train,val
[[ "${SKIP_MERGE:-0}" == 1 ]] || SEL merge
for S in 0 1 2 3 4 5 6 7 8 9; do
  $PY scripts/selenzyme_traindb.py seed_rids --seed $S --splits "$DB_SPLITS"
  SEL seed_db --seed $S --splits "$DB_SPLITS"
done
echo "Done: $(date)"
