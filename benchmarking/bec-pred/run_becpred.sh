#!/bin/bash
###################################################################################
### Run BEC-Pred Pipeline
###################################################################################

echo "============================================"
echo "==== BEC-Pred Training and Prediction ======"
echo "============================================"
echo $(date)

# Activate conda environment
source activate becpred_gpu

python -c 'import sys; print(sys.version_info[:])'
python -c 'import torch; print(f"GPU Available: {torch.cuda.is_available()}"); print(f"GPU Count: {torch.cuda.device_count()}")'

BASE=.
# --- Generate DB ---
echo "=== Generate BEC-Pred DB ==="
python $BASE/BECPred/generate_becpred_db.py

# --- Pretrain ---
echo "=== Pretrain ==="
start=$(date +%s)
python $BASE/BECPred/pretrain.py
echo "Pretrain completed in $(($(date +%s) - start))s"

# --- Finetune ---
echo "=== Finetune ==="
start=$(date +%s)
python $BASE/BECPred/finetune_bec.py
echo "Finetune completed in $(($(date +%s) - start))s"

# --- Eval ---
echo "=== Eval ==="
start=$(date +%s)
python $BASE/BECPred/eval_model.py
echo "Eval completed in $(($(date +%s) - start))s"


# --- Label Assigner ---
echo "=== Label Assigner ==="
python $BASE/Results/label_assigner.py \
    --input_csv $BASE/Results/results_test.csv \
    --labels $BASE/DB/ec_class_labels_ecreact.csv \
    --output_csv $BASE/Results/results_test_ec.csv

echo "==================================="
echo "=== Pipeline Finished           ==="
echo "==================================="
echo $(date)