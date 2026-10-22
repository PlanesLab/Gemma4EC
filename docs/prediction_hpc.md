# Large-scale prediction on HPC (SLURM)

This document describes how to run **large-scale EC number prediction with Gemma4EC** on HPC systems using **SLURM** and **multi-GPU distributed inference**.

For simple, local inference on a single GPU, see the [Predict EC numbers](../README.md#predict-ec-numbers) section in the main README.

---

## Overview

For large reaction datasets (thousands to millions of reactions), Gemma4EC provides SLURM scripts that:

- run **distributed inference** via 🤗 Accelerate,
- automatically detect available GPUs per node,
- load a pretrained TxGemma base model + Gemma4EC LoRA adapter,
- write predictions and logs in a reproducible layout.

This is the **recommended approach** for production-scale annotation.

---

## Prerequisites

Before running predictions on HPC, ensure that:

- A CUDA-capable GPU node is available
- The Conda environment is installed and activated (`conda activate gemma4ec`)
- The Gemma4EC LoRA adapter is downloaded locally (see [Step 1](#step-1--download-the-adapter))
- Hugging Face authentication is configured (see [`docs/huggingface_authentication.md`](huggingface_authentication.md))

---

## Step 1 — Download the adapter

```bash
git clone https://huggingface.co/PlanesLab/Gemma4EC-9B-Predict models/Gemma4EC-9B-Predict
# or for the 2B variant:
git clone https://huggingface.co/PlanesLab/Gemma4EC-2B-Predict models/Gemma4EC-2B-Predict
```

The adapter directory must contain:
- `adapter_model.safetensors`
- `adapter_config.json`

---

## Step 2 — Prepare your input CSV

The input file must contain at least one column:

| Column | Description |
|---|---|
| `rxn_smiles` | Biochemical reaction SMILES |

Example:

```csv
rxn_smiles
CCO.CC(=O)O>>CCOC(=O)C
OC(=O)CCC(=O)C(=O)O>>OC(=O)CCC(N)C(=O)O
```

---

## Step 3 — Submit the SLURM job

A reference SLURM script is provided at [`slurm/run_predict_gemma4ec.sh`](../slurm/run_predict_gemma4ec.sh).

Before submission, edit the script and set the following variables:

```bash
raw_data_file="/path/to/reactions.csv"
processed_data_folder="/scratch/<user>/gemma4ec/data/predict_run/data"
output_folder="/scratch/<user>/gemma4ec/data/predict_run/results"

# Path to the downloaded Gemma4EC adapter
model_checkpoint_folder="/path/to/Gemma4EC-9B-Predict"

# Base model (downloaded automatically on first run)
model_id="google/txgemma-9b-predict"
```

Then submit:

```bash
sbatch slurm/run_predict_gemma4ec.sh
```

---

## What the script does

Internally, the SLURM script launches distributed inference using:

```bash
accelerate launch predict.py \
  --raw_data_file            $raw_data_file \
  --processed_data_folder    $processed_data_folder \
  --output_folder            $output_folder \
  --model_checkpoint_folder  $model_checkpoint_folder \
  --model_id                 $model_id \
  --template_key             EC_NUMBER_PROMPT_2
```

Key details:
- GPU count is detected automatically by Accelerate
- The TxGemma base model is cached after the first download
- The LoRA adapter defines the EC-number specialisation

---

## Prompt selection

Gemma4EC models are trained with a specific prompt template:

- **`EC_NUMBER_PROMPT_2`** is the default and **recommended template** — it matches the prompt used during training.

Using a different template for inference is **not recommended** unless the model was retrained with that template. Alternative templates (used during development) are available in `prompts/prompts.json`.

---

## Output files

A prediction run writes to `output_folder`:

| File | Description |
|---|---|
| `predictions_*.tsv` | Predicted EC numbers with ground truth (if available) |
| `*.jsonl` | Intermediate batching files |
| Logs | Runtime statistics and error counts |

See [`results/README.md`](../results/README.md) for the full TSV schema.

---

## Notes

- Multi-GPU inference significantly improves throughput for large datasets.
- Ensure sufficient disk space for model caching (`$HF_HOME`).
- For most users, **the pretrained adapters on Hugging Face are sufficient** — retraining is unnecessary.
- For explanations of the predictions, see [`docs/chat.md`](chat.md).
