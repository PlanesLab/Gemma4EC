# SLURM scripts for Gemma4EC

This directory contains **SLURM job templates** for running Gemma4EC and the baseline models on HPC systems.

> Theia and BEC-Pred baseline scripts live in their own subdirectories:
> `benchmarking/theia/slurm/` and `benchmarking/bec-pred/slurm/`.

The scripts are designed to be:
- portable across clusters,
- free of user-specific paths,
- configurable via environment variables.

They are intended as **templates**, not drop-in one-click scripts — adjust
`PROJECT_ROOT`, `SCRATCH_ROOT`, `CONDA_ENV`, and resource directives
(`--partition`, `--qos`, `--constraint`) to match your cluster.

---

## Available scripts

### Gemma4EC fine-tuning (TxGemma-9B)

| Script | Purpose |
|---|---|
| `run_train_gemma4ec_9b.sh` | Fine-tune [TxGemma](https://deepmind.google/models/gemma/txgemma/)-9B + LoRA on ECReact |
| `run_predict_gemma4ec.sh` | Large-scale EC prediction with a saved local adapter |

### Gemma4EC fine-tuning (TxGemma-2B)

| Script | Purpose |
|---|---|
| `run_train_gemma4ec_2b.sh` | Fine-tune [TxGemma](https://deepmind.google/models/gemma/txgemma/)-2B + LoRA on ECReact |

### Zero-shot and API evaluation

| Script | Purpose |
|---|---|
| `run_predict_zeroshot.sh` | Zero-shot EC prediction with base TxGemma (no adapter) |
| `run_predict_api.sh` | Benchmark via external LLM APIs (OpenAI / Gemini) |

### Chat fine-tuning and mechanistic explanation (RAG)

| Script | Purpose |
|---|---|
| `run_train_chat.sh` | Fine-tune [TxGemma-9B-Chat](https://huggingface.co/google/txgemma-9b-chat) on mechanistic explanation prompts |
| `run_rag_infer.sh` | Run RAG-based mechanistic inference using the BRENDA knowledge base |
| `submit_chat_pipeline.sh` | Submit the full pipeline (fine-tune → RAG inference, chained via `--dependency`) |

### Theia MLP baseline (`benchmarking/theia/slurm/`)

| Script | Purpose |
|---|---|
| `run_train_theia.sh` | Train the [Theia](https://github.com/daenuprobst/theia) MLP on ECReact |
| `run_eval_theia.sh` | Evaluate a pre-trained Theia MLP |
| `run_theia_full.sh` | Full Theia pipeline (train + eval + summaries) |

### BEC-Pred baseline (`benchmarking/bec-pred/slurm/`)

| Script | Purpose |
|---|---|
| `run_becpred.sh` | Run the full [BEC-Pred](https://github.com/KeeliaQWJ/BEC-Pred) pipeline on ECReact |

---

## Required environment variables

### Hugging Face (required for TxGemma)
```bash
export HUGGINGFACE_TOKEN=hf_...
```
All scripts fall back to `~/.huggingface/token` if the variable is not set
(written by `huggingface-cli login`). See [`docs/huggingface_authentication.md`](../docs/huggingface_authentication.md).

### Weights & Biases (optional, training only)
```bash
export WANDB_API_KEY=...
```
If not set, training runs without W&B logging.

### External LLM APIs (API benchmarking only)
```bash
export OPENAI_API_KEY=...
export GEMINI_API_KEY=...   # or GOOGLE_API_KEY
```

### RAG inference (chat pipeline only)
```bash
export BRENDA_FILE=/path/to/brenda_2026_1.txt   # required for run_rag_infer.sh
```

Never commit API keys or tokens to the repository.

---

## Zero-shot evaluation
```bash
sbatch slurm/run_predict_zeroshot.sh
```

---

## Theia MLP baseline
```bash
sbatch benchmarking/theia/slurm/run_train_theia.sh
sbatch benchmarking/theia/slurm/run_eval_theia.sh
```

---

## BEC-Pred baseline
```bash
sbatch benchmarking/bec-pred/slurm/run_becpred.sh
```

Results are written to `$SCRATCH/gemma4ec/becpred/Results/`.

---

## Chat fine-tuning + RAG mechanistic inference
```bash
export HUGGINGFACE_TOKEN=hf_...
export BRENDA_FILE=/path/to/brenda_2026_1.txt

# Full pipeline (fine-tune → RAG inference, chained jobs)
bash slurm/submit_chat_pipeline.sh

# Or submit individually:
sbatch slurm/run_train_chat.sh
ADAPTER_DIR=/path/to/best_model sbatch slurm/run_rag_infer.sh
```

For interactive mechanistic explanation without fine-tuning, see
[`notebooks/mechanistic_explanation.ipynb`](../notebooks/mechanistic_explanation.ipynb).

---

## Reproducing all results (paper)

```bash
# 0. Canonicalize SMILES in all data splits (run once)
python scripts/canonicalize_smiles.py

# 1. Fine-tune Gemma4EC-9B and 2B on all partitions
export HUGGINGFACE_TOKEN=hf_...
export WANDB_API_KEY=...
bash slurm/submit_all_partitions.sh
bash slurm/submit_all_partitions_2b.sh

# 2. Theia and BEC-Pred baselines
bash benchmarking/theia/slurm/submit_all_partitions_theia.sh
bash benchmarking/bec-pred/slurm/submit_all_partitions_becpred.sh

# 3. Zero-shot and API baselines
sbatch slurm/run_predict_zeroshot.sh
# (API baselines require OPENAI_API_KEY / GEMINI_API_KEY)
sbatch slurm/run_predict_api.sh gpt-4.1-mini

# 4. Aggregate metrics
cd results/
python compute_weighted_metrics.py
python compute_per_class_and_splits.py
```

---

## Notes
- Scripts assume a Conda environment at `CONDA_ENV` (default: `/scratch/$USER/Envs/gemma4ec`)
- Resource requests (`--gres`, `--mem`, `--time`, `--constraint`) may need adjustment for your cluster
- Multi-GPU training uses Accelerate (`--num_processes` auto-detected from `nvidia-smi`)
- For detailed workflow documentation see [`docs/training.md`](../docs/training.md) and [`docs/prediction_hpc.md`](../docs/prediction_hpc.md)
