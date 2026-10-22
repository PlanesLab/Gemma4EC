#!/bin/bash
# SIMMER with its published reference DB (SIMMER_files) on one chunk of the deduplicated
# seed test pool (data/ECReact_seeds/api_pool.csv). No training: answers depend only on the
# reaction, so each unique test reaction is queried once and fanned out to all seeds
# (scripts/collect_tool_pool.py). Chunked because SIMMER appends every query to its
# reference Tanimoto matrix.
#
# Usage: sbatch --array=0-75 slurm/seeds/run_tool_simmer.sh      (CHUNK_SIZE=500)
#SBATCH --job-name=tool_simmer
#SBATCH --partition=general
#SBATCH --time=08:00:00
#SBATCH --nodes=1
#SBATCH --cpus-per-task=3
#SBATCH --mem=48G
#SBATCH --output=logs/tool_simmer_%A_%a.out

POOL_JOB=1 source "${PROJECT_ROOT:-$PWD}/slurm/seeds/_common.sh"
K=${SLURM_ARRAY_TASK_ID:?run as an array}
CHUNK_SIZE=${CHUNK_SIZE:-500}
ECN=${ECN_ROOT:?set ECN_ROOT in config.sh}
PY="$ENVS/SIMMERenv/bin/python3"
OUT="$WORK_ROOT/tools/simmer"
RES="$OUT/chunk_${K}"
mkdir -p "$RES"

"$PY" - "${POOL_CSV:-$SPLITS_DIR/api_pool.csv}" "$K" "$CHUNK_SIZE" "$OUT/query_${K}.csv" <<'PY'
import sys, pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import rdChemReactions
RDLogger.DisableLog("rdApp.*")
pool, k, n, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
df = pd.read_csv(pool, dtype=str).iloc[k * n:(k + 1) * n]
# ~11% of ECReact reactions end the reactant side with a dangling "-" ("...[H+]->>..."),
# which RDKit rejects; SIMMER.py exits on the first unparsable query, so drop the stray
# bond and pre-check each query with SIMMER's own parsing (R->* then SMARTS). Queries that
# still fail are skipped and scored as misses.
df["rxn_smiles"] = df["rxn_smiles"].str.replace("->>", ">>", regex=False)
def simmer_parses(rxn):
    try:
        sm = [".".join(Chem.MolToSmarts(Chem.MolFromSmiles(f.replace("R", "*")), isomericSmiles=True)
                       for f in side.split(".")) for side in rxn.split(">>", 1)]
        rdChemReactions.CreateDifferenceFingerprintForReaction(rdChemReactions.ReactionFromSmarts(sm[0] + ">>" + sm[1]))
        return True
    except Exception:
        return False
okm = df["rxn_smiles"].map(simmer_parses)
print(f"chunk {k}: skipping {(~okm).sum()} unparsable queries")
df = df[okm]
left, right = zip(*df["rxn_smiles"].str.split(">>", n=1))
pd.DataFrame({
    "reaction": [f"Q{i}" for i in df.index],
    "left_comp": [l.replace(".", "//") for l in left],
    "right_comp": [r.replace(".", "//") for r in right],
    "left_smiles": left, "right_smiles": right,
}).to_csv(out, index=False)
print(f"chunk {k}: {len(df)} queries")
PY

cd "$ECN"
"$PY" methods/SIMMER/SIMMER_code/SIMMER/SIMMER.py \
    -i methods/SIMMER/SIMMER_code/SIMMER/SIMMER_files -o "$RES" -q "$OUT/query_${K}.csv"
"$PY" methods/SIMMER/SIMMER_scripts/ec_predictions.py --input_dir "$RES" --output_file "$OUT/chunk_${K}.csv"
echo "Done: $(date)"
