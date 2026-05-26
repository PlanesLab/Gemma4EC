
# Benchmarking with external LLM APIs
This document describes how to **benchmark EC number prediction using external large language model (LLM) APIs** and compare their performance against Gemma4EC.

This workflow is intended for:
* reproducibility studies,
* comparative evaluation against frontier models.

---

## Overview
In addition to local inference with TxGemma + Gemma4EC adapters, this repository provides a **unified pipeline** to run EC-number prediction using external LLM APIs.

The API pipeline:
* uses the same reaction datasets as Gemma4EC,
* applies standardized prompt templates,
* handles batching, retries, and rate limiting,
* produces comparable TSV outputs for downstream analysis.

---

## Supported providers and models
The benchmarking pipeline supports any model accessible through the official API clients.

### [OpenAI](https://openai.com/es-ES/api/)
Examples include:
* `gpt-4.1`
* `gpt-4.1-mini`
* `gpt-5.1`
* `gpt-5-mini`

### [Google Gemini](https://ai.google.dev/gemini-api/docs?hl=es-419)
Examples include:

* `gemini-2.5-flash`
* `gemini-3-pro-preview`

Additional models may be supported as long as they are compatible with the `openai` or `google-genai` Python clients.

---

## Prompting strategy
API-based benchmarking uses a **dedicated prompt template** optimized for chat-style LLMs.
* The API prompt is distinct from the Gemma4EC training prompt
* Prompt templates are defined in:

```text
prompts/prompts.json
```

The API pipeline typically uses:
* `template_key = EC_NUMBER_PROMPT_API`
* `template_alias = EC_NUMBER`

This separation avoids prompt mismatch between locally trained models and API-based chat models.

---

## Running an API prediction batch
API-based predictions are launched via a SLURM batch script:

```bash
sbatch slurm/run_predict_api.sh <model_name> <split_or_csv>
```

### Examples
```bash
sbatch slurm/run_predict_api.sh gpt-5.1 test
sbatch slurm/run_predict_api.sh gemini-2.5-flash val
sbatch slurm/run_predict_api.sh gemini-3-pro-preview /path/to/custom.csv
```

If the second argument is omitted:

```bash
sbatch slurm/run_predict_api.sh gpt-5-mini
```

The script defaults to using:

```text
data/ECReact/test.csv
```

---

## Script configuration
Inside `slurm/run_predict_api.sh`, the following parameters are defined:

```bash
MODEL_NAME="gemini-3-pro-preview"     # or gpt-5.1, gpt-4.1-mini, gemini-2.5-flash, etc.
raw_data_file="/path/to/raw/test.csv"

processed_data_folder="/path/to/predict_run/api_processed"
output_folder="/path/to/predict_run/api_results"

prompts_json_path="prompts/prompts.json"
template_key="EC_NUMBER_PROMPT_API"
template_alias="EC_NUMBER"
```

The script automatically:
* activates the Conda environment,
* validates API credentials,
* builds JSONL batches,
* executes `predict_api.py`,
* writes predictions to TSV format.

---

## API authentication
Valid API credentials must be provided via environment variables.

### OpenAI
```bash
export OPENAI_API_KEY="your_openai_key"
```

### Google Gemini
```bash
export GEMINI_API_KEY="your_gemini_key"
```

For HPC usage, it is recommended to place these variables in a private file and source it in the job script:

```bash
source ~/.secrets_apis.sh
```

Never commit API keys to the repository.

---

## Output format
API-based prediction runs produce:

* a TSV file with predicted EC numbers,
* runtime and request statistics,
* optional logs for error analysis.

The output format is aligned with the local Gemma4EC prediction pipeline to enable direct comparison.

---

## Notes on benchmarking
* API models are **not fine-tuned** on the Gemma4EC training data
* Results reflect prompt-based reasoning performance
* Cost, latency, and rate limits vary across providers
* API outputs may change over time as models are updated

For fair comparisons, we recommend:
* fixing prompt templates,
* logging model versions when available,
* reporting inference cost and runtime alongside accuracy metrics.

---

## Related documentation
* Local and HPC prediction: `docs/prediction_hpc.md`
* Training and fine-tuning: `docs/training.md`
* Prompt templates: `prompts/prompts.json`