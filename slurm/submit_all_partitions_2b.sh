#!/bin/bash
# ============================================================
# submit_all_partitions_2b.sh
#
# Submit one 2B training job per Rhea partition.
#
# Usage:
#   export HUGGINGFACE_TOKEN=hf_...
#   export WANDB_API_KEY=...
#   bash slurm/submit_all_partitions_2b.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SLURM_SCRIPT="$SCRIPT_DIR/run_train_partition_2b.sh"

PARTITIONS=(Rhea_Scaffold Rhea_Stratified Rhea_Time)

echo "Submitting ${#PARTITIONS[@]} 2B jobs..."

for DB in "${PARTITIONS[@]}"; do
    JOB_ID=$(sbatch \
        --job-name="gemma4ec_2b_${DB}" \
        --export=ALL,DB_NAME="$DB",PROJECT_ROOT="$PROJECT_ROOT" \
        "$SLURM_SCRIPT" | awk '{print $NF}')
    echo "  Submitted $DB  →  job $JOB_ID"
done

echo "Done. Monitor with: squeue -u $USER"
