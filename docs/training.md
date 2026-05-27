# Training Gemma4EC

This document describes the **data preparation, training strategy, and available training modes** for Gemma4EC. It is intended for users who wish to **retrain or fine-tune** the model on custom biochemical reaction datasets.

For inference-only usage, this document is **not required** — see the main [README](../README.md) and [`docs/prediction_hpc.md`](prediction_hpc.md).

---

## Overview

Gemma4EC is trained by fine-tuning a **TxGemma-Predict** base model using **parameter-efficient fine-tuning (PEFT)** adapters (LoRA / DoRA / AdaLoRA). The training pipeline is designed to be:

- reproducible,
- scalable to large datasets,
- compatible with HPC and SLURM environments,
- flexible with respect to prompt design and few-shot strategies.

Training operates on **reaction-level supervision**, where each reaction SMILES string is paired with a target EC number.

---

## Data format

### Raw input

Training starts from a CSV file with at least the following columns:

| Column | Description |
|---|---|
| `rxn_smiles` | Biochemical reaction in SMILES format |
| `ec` | EC number label (e.g. `2.7.8`) |

Example:

```text
rxn_smiles,ec
CCO.CC(=O)O>>CCOC(=O)C,2.7.8
```

Place the raw file in:

```
data/ECReact/raw_data.csv
```

---

## Stratified dataset splitting

Before training, the raw dataset is split into train / validation / test partitions using **hierarchical EC stratification**.

Supported stratification levels:

| Level | Granularity | Example |
|---|---|---|
| 1 | EC class | `2` |
| 2 | Class.subclass | `2.7` |
| 3 | Class.subclass.subsubclass | `2.7.8` |

Run the split via:

```bash
python scripts/prepare_db.py \
  --db Rhea_Stratified \
  --db_root /path/to/raw/database \
  --out_root data/partitions \
  --val_frac 0.10 \
  --strat_level 2 \
  --seed 42
```

### Edge-case handling

To ensure robust splits, the following rules are applied per EC group:

| Group size | Assignment |
|---|---|
| n = 1 | Training only |
| n = 2 | One to train, one to validation |
| n ≥ 3 | At least one sample in each of train, validation, and test |

For most use cases, **stratification at level 2** offers the best balance between granularity and stability.

---

## Prompt construction

Gemma4EC frames EC prediction as a **text-generation task** using instruction-style prompts.

Prompt templates are defined in:

```
prompts/prompts.json
```

During preprocessing, CSV data are converted into model-ready JSONL files:

```
train.<ALIAS>.<TEMPLATE>.jsonl
val.<ALIAS>.<TEMPLATE>.jsonl
```

Prompt selection is controlled via `--template_key` at runtime. The **recommended template for training and inference** is `EC_NUMBER_PROMPT_2`.

---

## Training pipeline

### Minimal run

```bash
python main.py \
  --raw_data_folder       data/ECReact \
  --processed_data_folder data/processed \
  --prompts_json_path     prompts/prompts.json \
  --template_key          EC_NUMBER_PROMPT_2 \
  --template_alias        EC_NUMBER \
  --disable_wandb
```

### Key arguments

| Category | Argument | Default | Description |
|---|---|---|---|
| **Training** | `--batch_size` | `8` | Per-device batch size |
| | `--learning_rate` | `5e-4` | Learning rate |
| | `--num_train_epochs` | `30` | Training epochs |
| | `--max_seq_length` | `512` | Max token length (increase for few-shot) |
| | `--gradient_accumulation_steps` | `4` | Effective batch = batch × accum × n_gpus |
| | `--optimizer` | `adamw_torch` | Optimiser |
| | `--lr_scheduler_type` | `cosine` | LR scheduler |
| **Adapter (PEFT)** | `--adapter_method` | `lora` | `lora`, `dora`, or `adalora` |
| | `--lora_r` | `16` | LoRA rank |
| | `--lora_alpha` | `16` | LoRA alpha |
| | `--lora_dropout` | `0.0` | LoRA dropout |
| **Model** | `--model_id` | `google/txgemma-9b-predict` | Base model |
| | `--save_directory` | `./local_txgemma_model` | Local base model cache |
| **Evaluation** | `--monitor_metric` | `mcc` | `accuracy`, `mcc`, or `f1_macro` |
| | `--eval_every_epochs` | `1` | Evaluation frequency |
| | `--save_best` | `false` | Save best checkpoint |
| | `--early_stopping_patience` | `5` | Early stopping patience |
| | `--use_test` | `false` | Evaluate on test after training |
| **Few-shot** | `--few_shot_training` | `false` | Enable few-shot prompt mixing |
| | `--few_shot_ratio` | `0.3` | Fraction of training samples with few-shot prompts |
| | `--few_shot_k_min` | `1` | Minimum number of in-context examples |
| | `--few_shot_k_max` | `10` | Maximum number of in-context examples |
| **W&B** | `--wandb_project` | — | Weights & Biases project name |
| | `--wandb_entity` | — | Weights & Biases team/entity |
| | `--log_decoded_batches` | `false` | Log decoded prompts to W&B |
| | `--disable_wandb` | — | Disable W&B logging entirely |

---

## Training modes

### 1. Standard SFT (default)

Standard supervised fine-tuning without in-context examples:

```bash
python main.py --trainer_mode sft --disable_wandb
```

- Fastest and most memory-efficient
- Sequence length typically ≤ 512 tokens
- Recommended as the baseline configuration

### 2. Manual training loop

Uses a custom loop with synchronised metric computation and enhanced logging:

```bash
python main.py --trainer_mode manual
```

Features:
- Explicit EC-level metrics (Accuracy, F1, MCC) computed at each epoch
- Early stopping and best-checkpoint saving based on validation MCC
- Optional decoded-prompt logging to W&B

### 3. Few-shot training

Enables **on-the-fly few-shot prompt construction** during training:

```bash
python main.py \
  --trainer_mode manual \
  --few_shot_training true \
  --few_shot_ratio 0.3 \
  --few_shot_k_min 1 \
  --few_shot_k_max 8 \
  --max_seq_length 1280
```

Few-shot prompts concatenate randomly sampled reaction–EC examples to the main query.

| Mode | Typical max length | Relative compute |
|---|---|---|
| Zero-shot SFT | 512 | 1× |
| Few-shot (safe) | 1024 | ~2× |
| Few-shot (full) | 1280–1408 | ~2.5–3× |

Increase `--max_seq_length` accordingly to avoid truncation.

---

## PEFT adapters

Training keeps the base TxGemma weights **frozen** and only updates the adapter parameters.

Supported methods:

| Method | Flag | Notes |
|---|---|---|
| LoRA | `--adapter_method lora` | Default; lightweight and stable |
| DoRA | `--adapter_method dora` | Weight decomposition variant; used in paper |
| AdaLoRA | `--adapter_method adalora` | Adaptive rank allocation |

The resulting adapter is saved independently of the base model, enabling lightweight distribution on Hugging Face and reuse at inference time.

---

## Evaluation and logging

During training, Gemma4EC can compute:
- loss curves (train and validation),
- EC-level classification metrics (Accuracy, F1-macro, MCC),
- decoded prompt and prediction examples.

Logging is performed via **Weights & Biases (optional)**. Enable it by providing `--wandb_project` and `--wandb_entity`. Omit them (or pass `--disable_wandb`) to run without logging.

---

## Running on HPC (SLURM)

Gemma4EC provides example SLURM scripts for large-scale training on multi-GPU systems. See [`slurm/README.md`](../slurm/README.md) for the full list.

**Fine-tune on all three Rhea partitions:**

```bash
export HUGGINGFACE_TOKEN=hf_...
export WANDB_API_KEY=...
bash slurm/submit_all_partitions.sh       # 9B model
bash slurm/submit_all_partitions_2b.sh    # 2B model
```

**Single partition:**

```bash
DB_NAME=Rhea_Time sbatch slurm/run_train_partition.sh
```

The scripts configure GPU and memory resources and launch distributed training via 🤗 Accelerate. For authentication details, see [`docs/huggingface_authentication.md`](huggingface_authentication.md).

---

## Output artifacts

A training run produces:

| Artifact | Description |
|---|---|
| `adapter_model.safetensors` | PEFT adapter weights |
| `adapter_config.json` | Adapter configuration |
| Training logs | Loss, metric curves, decoded samples |
| W&B run (optional) | Full experiment tracked on wandb.ai |

The adapter directory can be used directly for inference as described in the main README.

---

## Notes

- Training the 9B model requires substantial GPU memory and is recommended only on HPC systems (e.g. A100 80 GB or 4× A100 40 GB).
- Few-shot training significantly increases compute cost due to longer sequences.
- For most users, **the pretrained adapters on Hugging Face are sufficient** — retraining is only necessary for custom datasets or ablation studies.
