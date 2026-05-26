
# Large-scale prediction on HPC (SLURM)
This document describes how to run **large-scale EC number prediction with Gemma4EC** on HPC systems using **SLURM** and **multi-GPU distributed inference**.

For simple, local inference on a single GPU, see the Quick Start section in the main README.

---

## Overview
For large reaction datasets (thousands to millions of reactions), Gemma4EC provides SLURM scripts that:

* run **distributed inference** via 🤗 Accelerate,
* automatically detect available GPUs per node,
* load a pretrained TxGemma base model + Gemma4EC LoRA adapter,
* write predictions and logs in a reproducible layout.

This is the **recommended approach** for production-scale annotation.

---

## Prerequisites
Before running predictions on HPC, ensure that:

* A CUDA-capable GPU node is available
* The Conda environment is installed and activated
* The Gemma4EC LoRA adapter is downloaded locally
* Hugging Face authentication is configured

For Hugging Face authentication details, see:
* `docs/huggingface_authentication.md`

---

## Input data
Prediction requires a CSV file containing at least one column:

* `rxn_smiles` — biochemical reaction SMILES

Example:

```text
rxn_smiles
CCO.CC(=O)O>>CCOC(=O)C
```

---

## Adapter and base model
Gemma4EC prediction uses:

* a **TxGemma-Predict base model** (downloaded automatically), and
* a **task-specific Gemma4EC LoRA adapter** (provided locally).

The adapter must be downloaded manually from Hugging Face, for example:

```
https://huggingface.co/PlanesLab/Gemma4EC-9B-Predict
```

The adapter directory must contain:
* `adapter_model.safetensors`
* `adapter_config.json`

---

## Running a SLURM prediction job
A reference SLURM script is provided:

```bash
slurm/run_predict_gemma4ec.sh
```

Submit the job with:

```bash
sbatch slurm/run_predict_gemma4ec.sh
```

---

## Configuring the SLURM script
Before submission, edit `slurm/run_predict_gemma4ec.sh` and set the following variables:

```bash
raw_data_file="/path/to/reactions.csv"
processed_data_folder="/scratch/<user>/gemma4ec/data/predict_run/data"
output_folder="/scratch/<user>/gemma4ec/data/predict_run/results"

# Path to the downloaded Gemma4EC adapter
model_checkpoint_folder="/path/to/Gemma4EC-9B-Predict"

# Base model (downloaded automatically)
model_id="google/txgemma-9b-predict"
```

---

## Execution details
Internally, the SLURM script launches distributed inference using:

```bash
accelerate launch predict.py \
  --raw_data_file $raw_data_file \
  --processed_data_folder $processed_data_folder \
  --output_folder $output_folder \
  --model_checkpoint_folder $model_checkpoint_folder \
  --model_id $model_id \
  --template_key EC_NUMBER_PROMPT_2
```

Key points:
* GPU count is detected automatically by Accelerate
* The TxGemma base model is cached after the first download
* The LoRA adapter defines the EC-number specialization

---

## Prompt selection
Gemma4EC models are trained using a **specific prompt template**.

* **`EC_NUMBER_PROMPT_2`** is the default and **recommended template for prediction**
* This template matches the prompt used during model training

Using a different prompt template for inference is **not recommended** unless a new model is retrained with that template.

Alternative prompt templates used during development are provided in:

```text
prompts/prompts.json
```

These templates are intended for **research and retraining purposes only**.

---

## Output files
A prediction run produces:

* a TSV file containing predicted EC numbers,
* optional logs and runtime statistics,
* intermediate JSONL files used for batching.

Output files are written to the directory specified by `output_folder`.

---

## Notes
* Multi-GPU inference significantly improves throughput for large datasets
* Ensure sufficient disk space for model caching
* For most users, the pretrained adapter is sufficient and retraining is unnecessary
