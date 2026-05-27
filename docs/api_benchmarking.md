# Benchmarking with external LLM APIs

This document describes how to **benchmark EC number prediction using external large language model (LLM) APIs** and compare their performance against Gemma4EC.

This workflow is intended for:
- reproducibility studies,
- comparative evaluation against frontier models (GPT, Gemini, etc.).

---

## Overview

In addition to local inference with TxGemma + Gemma4EC adapters, this repository provides a **unified pipeline** to run EC-number prediction using external LLM APIs.

The API pipeline:
- uses the same reaction datasets as Gemma4EC,
- applies standardised prompt templates,
- handles batching, retries, and rate limiting,
- produces TSV outputs in the same format as the local pipeline for direct comparison.

---

## Supported providers and models

### [OpenAI](https://platform.openai.com/)

Examples include:
- `gpt-4.1`
- `gpt-4.1-mini`
- `gpt-5.1`
- `gpt-5-mini`

### [Google Gemini](https://ai.google.dev/gemini-api/docs)

Examples include:
- `gemini-2.5-flash`
- `gemini-3-pro-preview`

Any model compatible with the `openai` or `google-genai` Python clients can be used.

---

## Prompting strategy

API-based benchmarking uses a **dedicated prompt template** optimised for chat-style LLMs, distinct from the Gemma4EC training prompt:

| Setting | Value |
|---|---|
| `template_key` | `EC_NUMBER_PROMPT_API` |
| `template_alias` | `EC_NUMBER` |

This separation prevents prompt mismatch between locally trained models and API-based chat models. All templates are defined in `prompts/prompts.json`.

---

## Running an API prediction batch

### Via SLURM (recommended for large datasets)

```bash
sbatch slurm/run_predict_api.sh <model_name> <split_or_csv>
```

**Examples:**
```bash
sbatch slurm/run_predict_api.sh gpt-5.1 test
sbatch slurm/run_predict_api.sh gemini-2.5-flash val
sbatch slurm/run_predict_api.sh gemini-3-pro-preview /path/to/custom.csv
```

If the second argument is omitted, the script defaults to `data/ECReact/test.csv`:

```bash
sbatch slurm/run_predict_api.sh gpt-4.1-mini
```

### Via command line (small datasets)

```bash
python predict_api.py \
  --model_name        gemini-2.5-flash \
  --raw_data_file     data/ECReact/test.csv \
  --output_folder     outputs/api_results \
  --template_key      EC_NUMBER_PROMPT_API \
  --template_alias    EC_NUMBER
```

---

## Script configuration

Inside `slurm/run_predict_api.sh`, the following parameters are defined:

```bash
MODEL_NAME="gemini-2.5-flash"          # model to benchmark
raw_data_file="/path/to/raw/test.csv"

processed_data_folder="/path/to/predict_run/api_processed"
output_folder="/path/to/predict_run/api_results"

prompts_json_path="prompts/prompts.json"
template_key="EC_NUMBER_PROMPT_API"
template_alias="EC_NUMBER"
```

The script automatically:
- activates the Conda environment,
- validates API credentials,
- builds JSONL batches,
- executes `predict_api.py`,
- writes predictions to TSV format.

---

## API authentication

Valid credentials must be provided via environment variables **before** submitting the job.

### OpenAI

```bash
export OPENAI_API_KEY="your_openai_key"
```

### Google Gemini

```bash
export GEMINI_API_KEY="your_gemini_key"
# or alternatively:
export GOOGLE_API_KEY="your_google_key"
```

For HPC usage, store credentials in a private file and source it in the SLURM script:

```bash
# ~/.secrets_apis.sh  (not tracked by git)
export OPENAI_API_KEY="..."
export GEMINI_API_KEY="..."
```

```bash
# In your SLURM script:
source ~/.secrets_apis.sh
```

> **Security:** Never commit API keys to the repository. See [`.gitignore`](../.gitignore).

---

## Output format

API prediction runs produce the same TSV format as local Gemma4EC inference:

| Column | Description |
|---|---|
| `true_label` | Ground-truth EC (if available) |
| `pred_raw` | Raw model output string |
| `pred_fragment` | Extracted EC fragment |
| `pred_well_formed` | `True` if `pred_fragment` is a valid EC pattern |
| `smiles` | Reaction SMILES used as input |

This format enables **direct comparison** with Gemma4EC and baseline results using the scripts in `results/`.

---

## Computing benchmark metrics

Once predictions are available:

```bash
cd results/
python compute_weighted_metrics.py
python compute_per_class_and_splits.py
```

See [`results/README.md`](../results/README.md) for details.

---

## Notes on fair benchmarking

- API models are **not fine-tuned** on the Gemma4EC training data — results reflect zero-shot / prompt-based reasoning.
- API outputs may change over time as models are updated; log model versions when available.
- Cost, latency, and rate limits vary significantly across providers.
- For reproducibility, fix prompt templates and report inference cost alongside accuracy metrics.

---

## Related documentation

- Local and HPC prediction: [`docs/prediction_hpc.md`](prediction_hpc.md)
- Training and fine-tuning: [`docs/training.md`](training.md)
- Prompt templates: [`prompts/prompts.json`](../prompts/prompts.json)
- Results: [`results/README.md`](../results/README.md)
