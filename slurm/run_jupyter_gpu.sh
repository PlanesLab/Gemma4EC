#!/bin/bash
# ============================================================
# run_jupyter_gpu.sh
#
# Starts a JupyterLab server on a GPU compute node.
# Do NOT run this directly — use launch_jupyter_gpu.sh instead.
#
# Usage (via wrapper):
#   bash launch_jupyter_gpu.sh
#
# Or manually:
#   sbatch slurm/run_jupyter_gpu.sh
#   # then check logs/jupyter_<JOBID>.out for the SSH tunnel command
# ============================================================

#SBATCH --job-name=jupyter_gemma4ec
#SBATCH --partition=general
#SBATCH --gres=gpu:1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48GB
#SBATCH --time=8:00:00
#SBATCH --output=logs/jupyter_%j.out

set -euo pipefail

# ============================================================
# PATHS
# ============================================================
PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CONDA_ENV=${CONDA_ENV:-/scratch/$USER/Envs/gemma4ec}
PYTHON="$CONDA_ENV/bin/python"
JUPYTER="$CONDA_ENV/bin/jupyter"

export PATH="$CONDA_ENV/bin:$PATH"
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# ============================================================
# CACHE DIRS  (reuse the shared HF cache already populated)
# ============================================================
CACHE_ROOT=${CACHE_ROOT:-/scratch/$USER/.cache/gemma4ec}
mkdir -p "$CACHE_ROOT"

export HF_HOME="$CACHE_ROOT/hf"
export TRANSFORMERS_CACHE="$CACHE_ROOT/hf/transformers"
export HF_DATASETS_CACHE="$CACHE_ROOT/hf/datasets"
export TORCH_HOME="$CACHE_ROOT/torch"
export TRITON_CACHE_DIR="$CACHE_ROOT/triton"
export NUMBA_CACHE_DIR="$CACHE_ROOT/numba"
export MPLCONFIGDIR="$CACHE_ROOT/matplotlib"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

# ============================================================
# HF TOKEN
# ============================================================
if [[ -z "${HUGGINGFACE_TOKEN:-}" ]]; then
    TOKEN_FILE="$HOME/.huggingface/token"
    if [[ -f "$TOKEN_FILE" ]]; then
        export HUGGINGFACE_TOKEN=$(cat "$TOKEN_FILE")
    else
        echo "WARNING: HUGGINGFACE_TOKEN not set and $HOME/.huggingface/token not found."
        echo "         Gated models (txgemma-9b-predict/chat) will fail to download."
    fi
fi
export HF_TOKEN="${HUGGINGFACE_TOKEN:-}"

# ============================================================
# PICK A FREE PORT
# ============================================================
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()")
NODE=$(hostname -s)
LOGIN_NODE="hyperion.unavcloud.unav.es"   # adjust if your login node differs

# ============================================================
# PRINT CONNECTION INFO  (captured by launch_jupyter_gpu.sh)
# ============================================================
echo "============================================================"
echo "  JupyterLab is starting on : $NODE:$PORT"
echo "  Job ID                    : $SLURM_JOB_ID"
echo ""
echo "  1. Open a NEW terminal on your laptop and run:"
echo "     ssh -N -L ${PORT}:${NODE}:${PORT} ${LOGIN_NODE}"
echo ""
echo "  2. Then open in your browser:"
echo "     http://127.0.0.1:${PORT}"
echo "     (the token will appear in this log below)"
echo "============================================================"

# ============================================================
# LAUNCH JUPYTERLAB
# ============================================================
echo "[jupyter] GPU info:"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null || echo "  (nvidia-smi not available)"
echo ""

cd "$PROJECT_ROOT"

"$JUPYTER" lab \
    --no-browser \
    --ip=0.0.0.0 \
    --port="$PORT" \
    --notebook-dir="$PROJECT_ROOT/notebooks" \
    --ServerApp.token='' \
    --ServerApp.password='' \
    --ServerApp.allow_origin='*'
