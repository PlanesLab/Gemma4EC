#!/bin/bash
# ============================================================
# launch_jupyter_gpu.sh
#
# Submit a JupyterLab session on a GPU node and print the
# SSH tunnel command for your laptop.
#
# Run from the repo root on the login node:
#   bash launch_jupyter_gpu.sh
#
# Options (env vars):
#   PARTITION    SLURM partition (default: general)
#   GPU_TYPE     GPU type hint, e.g. a100, a6000 (default: any)
#   TIME         Wall-clock limit (default: 8:00:00)
#   MEM          Memory request  (default: 48GB)
# ============================================================

set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$PROJECT_ROOT"

mkdir -p logs

# ── Overrideable defaults ─────────────────────────────────────────────────────
PARTITION=${PARTITION:-general}
GPU_TYPE=${GPU_TYPE:-}          # e.g. "a100" → --gres=gpu:a100:1; empty → gpu:1
TIME=${TIME:-8:00:00}
MEM=${MEM:-48GB}

GRES="gpu:1"
[[ -n "$GPU_TYPE" ]] && GRES="gpu:${GPU_TYPE}:1"

# ── Submit ────────────────────────────────────────────────────────────────────
echo "[launch] Submitting JupyterLab job on partition=$PARTITION gres=$GRES ..."

JOB_ID=$(sbatch \
    --partition="$PARTITION" \
    --gres="$GRES" \
    --time="$TIME" \
    --mem="$MEM" \
    slurm/run_jupyter_gpu.sh \
  | awk '{print $4}')

LOG="logs/jupyter_${JOB_ID}.out"
echo "[launch] Job ID : $JOB_ID"
echo "[launch] Log    : $LOG"
echo ""
echo "[launch] Waiting for the job to start (this may take a few minutes) ..."

# ── Wait for log file ─────────────────────────────────────────────────────────
TIMEOUT=300   # seconds
ELAPSED=0
while [[ ! -f "$LOG" ]]; do
    sleep 3
    ELAPSED=$((ELAPSED + 3))
    STATE=$(squeue --job "$JOB_ID" --noheader --format="%T" 2>/dev/null || echo "UNKNOWN")
    printf "\r  Job state: %-12s  waited: %ds" "$STATE" "$ELAPSED"
    if [[ "$STATE" == "FAILED" || "$STATE" == "CANCELLED" || "$STATE" == "TIMEOUT" ]]; then
        echo ""
        echo "[ERROR] Job ended unexpectedly with state: $STATE"
        exit 1
    fi
    if [[ $ELAPSED -ge $TIMEOUT ]]; then
        echo ""
        echo "[ERROR] Timed out waiting for log file after ${TIMEOUT}s."
        echo "        Check job status with:  squeue --job $JOB_ID"
        exit 1
    fi
done
echo ""

# ── Tail log until the connection info appears ────────────────────────────────
echo "[launch] Job started — waiting for Jupyter URL ..."
echo ""
grep -m1 "http://127.0.0.1" <(tail -f "$LOG") 2>/dev/null || true

# Show the full connection block
echo ""
echo "── Full connection info from the log ──────────────────────────────────"
grep -A 10 "JupyterLab is starting" "$LOG" 2>/dev/null || \
    echo "(run: tail -f $LOG  for full output)"
echo "───────────────────────────────────────────────────────────────────────"
echo ""
echo "To cancel the session:"
echo "  scancel $JOB_ID"
