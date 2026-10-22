#!/bin/bash
# Train + query CLAIRE on one seed split (code from the ECNumberPrediction repo,
# same pipeline as its Rhea-splits block in methods/CLAIRE/run_claire.sh).
#
# Usage: SEED=0 sbatch slurm/seeds/run_seed_claire.sh
#SBATCH --job-name=seed_claire
#SBATCH --partition=general
#SBATCH --qos=long
#SBATCH --time=1-00:00:00
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=128GB
#SBATCH --output=logs/seed_claire_%j.out

source "${PROJECT_ROOT:-$PWD}/slurm/seeds/_common.sh"
# CLAIRE was removed from ECNumberPrediction on 2026-09-25; the code lives in the backup copy (moved to /data on 2026-10-06)
CLAIRE_ROOT=${CLAIRE_ROOT:?set CLAIRE_ROOT in config.sh}
CODE="$CLAIRE_ROOT/CLAIRE_code/CLAIRE"
SCRIPTS="$CLAIRE_ROOT/CLAIRE_scripts"
EPOCHS=${CLAIRE_EPOCHS:-2000}   # upstream default; 200 was unstable across seeds
RXNFP_PY="$ENVS/rxnfp-env/bin/python"
CLAIRE_PY="$ENVS/claire/bin/python"

WORK="$SEED_WORK/claire"
DB_DIR="$WORK/db"
MODEL_DIR="$WORK/model"
mkdir -p "$WORK" "$DB_DIR" "$MODEL_DIR"

# CLAIRE inputs: reaction_id / reaction_smiles / ec (tsv) + one query SMILES per line
"$CLAIRE_PY" - "$SEED_DATA" "$WORK" <<'PY'
import sys, pandas as pd
src, out = sys.argv[1:]
for split in ("train", "test"):
    df = pd.read_csv(f"{src}/{split}.csv", dtype=str)
    df = pd.DataFrame({"reaction_id": range(len(df)), "reaction_smiles": df.rxn_smiles, "ec": df.ec})
    df.to_csv(f"{out}/{split}.tsv", sep="\t", index=False)
    if split == "test":
        df.reaction_smiles.to_csv(f"{out}/queries.txt", index=False, header=False)
PY

export LD_LIBRARY_PATH="$ENVS/rxnfp-env/lib:${LD_LIBRARY_PATH:-}"
# REUSE_MODEL=1 skips DB building + training when this seed's model already exists
if [[ "${REUSE_MODEL:-0}" == 1 && -f "$MODEL_DIR/train_final_remapped.pth" ]]; then
  echo "Reusing trained model $MODEL_DIR/train_final_remapped.pth"
else
  "$RXNFP_PY" "$CODE/rxnfp_create.py" --train_file "$WORK/train.tsv" --output_dir "$DB_DIR"
  "$CLAIRE_PY" "$CODE/create_claire_db.py" --db_dir "$DB_DIR"
  "$CLAIRE_PY" "$CODE/dev/training/train-pred_rxn_EC.py" \
      --db_dir "$DB_DIR" --output_dir "$MODEL_DIR" --epoch "$EPOCHS" --seed "$SEED"
  "$CLAIRE_PY" "$SCRIPTS/remap_checkpoint.py" \
      --input "$MODEL_DIR/train_final.pth" --output "$MODEL_DIR/train_final_remapped.pth"
fi

# Query DRFP must match the training DB (create_claire_db.py: DrfpEncoder.encode(..., n_folded_length=256)
# with library defaults). The drfp CLI uses different defaults (~21% bit overlap), which put
# queries in a different feature space and cut top-1 accuracy roughly in half.
"$CLAIRE_PY" - "$WORK/queries.txt" "$WORK/query_drfp.pkl" <<'PY'
import pickle, sys
from drfp import DrfpEncoder
q = [l.strip() for l in open(sys.argv[1]) if l.strip()]
pickle.dump(DrfpEncoder.encode(q, n_folded_length=256), open(sys.argv[2], "wb"))
PY
"$RXNFP_PY" "$SCRIPTS/create_fps.py" "$WORK/queries.txt" "$WORK/query_drfp.pkl" "$WORK/query_fps.npz"
"$CLAIRE_PY" "$SCRIPTS/query_claire.py" \
    --test_data_path "$WORK/query_fps.npz" \
    --train_data_path "$DB_DIR/lookup_array_ec3.pkl" \
    --train_labels_path "$DB_DIR/labels_train_ec3.pkl" \
    --test_csv_path "$WORK/test.tsv" \
    --reaction_id_col reaction_id \
    --model_path "$MODEL_DIR/train_final_remapped.pth" \
    --gmm_path "$CODE/dev/gmm/gmm_ensumble.pkl" \
    --out_filename "$WORK/results"
"$CLAIRE_PY" "$SCRIPTS/get_ec_predictions.py" \
    --input "$WORK/results_prediction.csv" --output "$WORK/CLAIRE.csv"

echo "Done: $(date)"
