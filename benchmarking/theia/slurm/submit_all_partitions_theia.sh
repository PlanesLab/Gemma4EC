#!/bin/bash
# Submit one Theia training job per Rhea partition.
# Usage: bash slurm/submit_all_partitions_theia.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SLURM_SCRIPT="$SCRIPT_DIR/run_train_theia.sh"

PARTITIONS=(Rhea_Scaffold Rhea_Stratified Rhea_Time)

echo "Submitting ${#PARTITIONS[@]} Theia jobs..."

for DB in "${PARTITIONS[@]}"; do
    JOB_ID=$(sbatch \
        --job-name="theia_${DB}" \
        --export=ALL,DB_NAME="$DB",PROJECT_ROOT="$PROJECT_ROOT" \
        "$SLURM_SCRIPT" | awk '{print $NF}')
    echo "  Submitted $DB  →  job $JOB_ID"
done

echo "Done. Monitor with: squeue -u $USER"
