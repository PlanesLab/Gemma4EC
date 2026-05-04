# SLURM scripts for Gemma4EC

This directory contains **SLURM job templates** for running Gemma4EC on
high-performance computing (HPC) systems.

The scripts are designed to be:
- portable across clusters,
- free of user-specific paths,
- configurable via environment variables.

They are intended as **templates**, not drop-in one-click scripts — adjust
`PROJECT_ROOT`, `SCRATCH_ROOT`, `CONDA_ENV`, and resource directives
(`--partition`, `--qos`, `--constraint`) to match your cluster.

---

## Available scripts

| Script | Purpose |
|---|---|
| `run_train_partition.sh` | Fine-tune [TxGemma](https://deepmind.google/models/gemma/txgemma/)-9B + LoRA on a single [Rhea](https://www.rhea-db.org/) partition |
| `run_predict_partition.sh` | Re-evaluate a saved adapter on val + test (without retraining) |
| `run_predict_zeroshot.sh` | Zero-shot EC prediction with base TxGemma (no adapter) |
| `run_train_theia.sh` | Train the [Theia](https://github.com/daenuprobst/theia) MLP baseline from scratch |
| `run_eval_theia.sh` | Evaluate a pre-trained [Theia](https://github.com/daenuprobst/theia) MLP on all splits |
| `submit_all_partitions.sh` | Submit all three Rhea partition training jobs at once |
| `run_train_gemma4ec_9b.sh` | Fine-tune on the raw (non-partitioned) dataset |
| `run_predict_gemma4ec.sh` | Large-scale EC prediction with a local adapter |
| `run_predict_api.sh` | Benchmark via external LLM APIs (OpenAI / Gemini) |

---

## Required environment variables

### Hugging Face (required for TxGemma)
```bash
export HUGGINGFACE_TOKEN=hf_...
```
All scripts fall back to `~/.huggingface/token` if the variable is not set
(written by `huggingface-cli login`). See `docs/huggingface_authentication.md`.

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
Never commit API keys to the repository.

---

## Partition fine-tuning workflow

Submit all three Rhea partitions (Scaffold / Stratified / Time) in one go:
```bash
export HUGGINGFACE_TOKEN=hf_...
export WANDB_API_KEY=...

bash slurm/submit_all_partitions.sh
```

Or submit a single partition:
```bash
sbatch --export=ALL,DB_NAME=Rhea_Time slurm/run_train_partition.sh
```

After training completes, re-run evaluation on val + test with the best checkpoint:
```bash
sbatch --export=ALL,DB_NAME=Rhea_Time slurm/run_predict_partition.sh
```

---

## Zero-shot evaluation
```bash
sbatch slurm/run_predict_zeroshot.sh
```

---

## [Theia](https://github.com/daenuprobst/theia) MLP baseline

Train from scratch on the raw partition:
```bash
sbatch slurm/run_train_theia.sh
```

Evaluate a pre-trained Theia model:
```bash
sbatch slurm/run_eval_theia.sh
```

---

## Notes
- Scripts assume a Conda environment at `CONDA_ENV` (default: `/scratch/$USER/conda_envs/gemma4ec`)
- Resource requests (`--gres`, `--mem`, `--time`, `--constraint`) may need adjustment for your cluster
- Multi-GPU training uses 🤗 Accelerate with `--num_processes $(nvidia-smi --list-gpus | wc -l)`
- For detailed workflow documentation see `docs/training.md` and `docs/prediction_hpc.md`
