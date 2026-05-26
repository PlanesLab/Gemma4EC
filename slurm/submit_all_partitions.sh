#!/bin/bash
# ============================================================
# submit_all_partitions.sh
#
# Submit one training job per Rhea partition.
#
# Usage:
#   export HUGGINGFACE_TOKEN=hf_...
#   export WANDB_API_KEY=...
#   export WANDB_ENTITY=your_username   # or set it inside run_train_partition.sh
#   bash slurm/submit_all_partitions.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SLURM_SCRIPT="$SCRIPT_DIR/run_train_partition.sh"

PARTITIONS=(Rhea_Scaffold Rhea_Stratified Rhea_Time)

echo "Submitting ${#PARTITIONS[@]} jobs..."

for DB in "${PARTITIONS[@]}"; do
    JOB_ID=$(sbatch \
        --job-name="gemma4ec_${DB}" \
        --export=ALL,DB_NAME="$DB",PROJECT_ROOT="$PROJECT_ROOT" \
        "$SLURM_SCRIPT" | awk '{print $NF}')
    echo "  Submitted $DB  →  job $JOB_ID"
done

echo "Done. Monitor with: squeue -u $USER"
