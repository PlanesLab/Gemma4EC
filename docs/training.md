
# Training Gemma4EC
This document describes the **data preparation, training strategy, and available training modes** for Gemma4EC. It is intended for users who wish to **retrain or fine-tune** the model on custom biochemical reaction datasets.

For inference-only usage, this document is **not required**.

---

## Overview
Gemma4EC is trained by fine-tuning a **TxGemma-Predict** base model using **parameter-efficient fine-tuning (PEFT)** adapters (LoRA / DoRA). The training pipeline is designed to be:

* reproducible,
* scalable to large datasets,
* compatible with HPC and SLURM environments,
* flexible with respect to prompt design and few-shot strategies.

Training operates on **reaction-level supervision**, where each reaction SMILES string is paired with a target EC number.

---

## Data format
### Raw input data
Training starts from a single CSV file with at least the following columns:
* `rxn_smiles` — biochemical reaction SMILES
* `ec` — EC number label (e.g. `2.7.8`)

Example:

```text
rxn_smiles,ec
CCO.CC(=O)O>>CCOC(=O)C,2.7.8
```

Place the raw file in:

```text
data/ECReact/raw_data.csv
```

---

## Stratified dataset splitting
Before training, the raw dataset is split into train / validation / test partitions using **hierarchical EC stratification**.

Supported stratification levels:

* **Level 1** — EC class (e.g. `2`)
* **Level 2** — class.subclass (e.g. `2.7`)
* **Level 3** — class.subclass.subsubclass (e.g. `2.7.8`)

Splitting is performed using the provided CLI:

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

* **n = 1** → assigned to training only
* **n = 2** → one sample to train, one to validation
* **n ≥ 3** → at least one sample in train, validation, and test

For most use cases, **stratification at level 2** offers the best balance between granularity and stability.

---

## Prompt construction
Gemma4EC uses **instruction-style prompts** to frame EC prediction as a text-generation task.

Prompt templates are defined in:

```text
prompts/prompts.json
```

During preprocessing, CSV data are converted into model-ready JSONL files of the form:

* `train.<ALIAS>.<TEMPLATE>.jsonl`
* `val.<ALIAS>.<TEMPLATE>.jsonl`

Prompt selection is controlled via the `--template_key` argument at runtime.

---

## Training pipeline

### Quick training run
A minimal training invocation requires only a few arguments:

```bash
python main.py \
  --raw_data_folder       data/ECReact \
  --processed_data_folder data/processed \
  --prompts_json_path     prompts/prompts.json \
  --template_key          EC_NUMBER_PROMPT_2 \
  --template_alias        EC_NUMBER
```

All other parameters have sensible defaults and can be overridden as needed.

| Category              | Main args                                                                                     | Default                      | **Used in `run_main.sh`**                                                                                                                                                                                                      |
| --------------------- | --------------------------------------------------------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Training**          | `--batch_size 16` `--learning_rate 5e-6` `--num_train_epochs 5` `--max_seq_length 512`        | Zero-shot baseline           | **`batch_size=8`**, `learning_rate=2e-4`, `epochs=40`, `max_seq_length=1280`, `gradient_accumulation_steps=9`, `warmup_steps=2`, `optimizer=adamw_torch`, `lr_scheduler_type=cosine`, `weight_decay=0.001`, `logging_steps=50` |
| **Adapter (PEFT)**    | `--adapter_method lora` `--lora_r 8` `--lora_alpha 16` `--lora_dropout 0.0`                   | LoRA                         | **`adapter_method=dora`**, `lora_r=16`, `lora_alpha=16`, `lora_dropout=0.1`                                                                                                                                                    |
| **Model**             | `--model_id google/txgemma-2b-predict` `--save_directory ./local_txgemma_model`               | TxGemma-2B                   | `model_id=google/txgemma-2b-predict`, `save_directory=$SCRATCH/gemma4ec/local_txgemma_model`                                                                                                                                   |
| **Evaluation**        | `--monitor_metric mcc` `--eval_every_epochs 1` `--save_best True`                             | Early stop + best checkpoint | `eval_every_epochs=1`, `monitor_metric=mcc`, `early_stopping_patience=5`, `save_best=True`, `greater_is_better=True`                                                                                                           |
| **Few-shot training** | `--few_shot_training False` `--few_shot_ratio 0.3` `--few_shot_k_min 1` `--few_shot_k_max 10` | Disabled by default          | **`few_shot_training=True`**, `few_shot_ratio=0.3`, `few_shot_k_min=1`, **`few_shot_k_max=8`**                                                                                                                                 |
| **Trainer mode**      | `--trainer_mode sft`                                                                          | HuggingFace SFTTrainer       | **`trainer_mode=manual`** *(custom loop with EC metrics, decoded logs, early stop)*                                                                                                                                            |
| **W&B Logging**       | `--wandb_project` `--wandb_entity` `--log_decoded_batches False`                              | Optional                     | **`log_decoded_batches=True`**, project=`Gemma4ec`, entity=`miramon_team`, tags=`["main","txgemma2b"]`                                                                                                                         |
| **Hardware**          | —                                                                                             | —                            | GPUs=`4×A100-SXM4`, RAM=`200GB`, CPUs per task=`4`, gradient checkpointing=`True`, `fp16=True`                                                                                                                                 |
| **Prompts**           | `--template_key EC_NUMBER_PROMPT_1`                                                           | Prompt 1                     | **`template_key=EC_NUMBER_PROMPT_2`** *(best template for current config)*                                                                                                                                                     |

---

## Training modes
Gemma4EC supports multiple training modes depending on transparency, efficiency, and prompt complexity requirements.

### 1. Zero-shot fine-tuning (default)
Standard supervised fine-tuning without in-context examples.

```bash
python main.py --trainer_mode sft
```

Characteristics:
* Fastest and most memory-efficient
* Sequence length typically ≤ 512 tokens
* Recommended baseline configuration

---

### 2. Manual training loop
Uses a custom training loop with synchronized metric computation and enhanced logging.

```bash
python main.py --trainer_mode manual
```

Features:
* Explicit EC-level metrics (Accuracy, F1, MCC)
* Early stopping and best-checkpoint saving
* Optional decoded-prompt logging

---

### 3. Few-shot training
Enables **on-the-fly few-shot prompt construction** during training.

```bash
python main.py \
  --trainer_mode manual \
  --few_shot_training True \
  --few_shot_ratio 0.3 \
  --few_shot_k_min 1 \
  --few_shot_k_max 8 \
  --max_seq_length 1280
```

Few-shot prompts concatenate randomly sampled reaction–EC examples to the main query.

| Mode            | Typical max length | Relative cost |
| --------------- | ------------------ | ------------- |
| Zero-shot       | 512                | 1×            |
| Few-shot (safe) | 1024               | ~2×           |
| Few-shot (full) | 1280–1408          | ~2.5–3×       |

Sequence length must be increased accordingly to avoid truncation.

---

## PEFT adapters
Training uses **parameter-efficient adapters**, keeping the base TxGemma weights frozen.

Supported methods:

* LoRA
* DoRA
* AdaLoRA

Adapter parameters (rank, alpha, dropout) can be configured via CLI arguments. The resulting adapter is saved independently of the base model, enabling lightweight distribution and reuse.

---

## Evaluation and logging
During training, Gemma4EC can compute:

* loss curves,
* EC-level classification metrics,
* decoded prompt and prediction examples.

Logging is performed via **Weights & Biases (optional)** and can be enabled by setting the corresponding CLI arguments.

Early stopping and best-checkpoint tracking are supported in both trainer modes.

---

## Running on HPC (SLURM)
Gemma4EC provides example SLURM scripts for large-scale training on multi-GPU systems.

Typical workflow:

```bash
sbatch slurm/run_train_gemma4ec_9b.sh
```

The scripts:

* configure GPU and memory resources,
* activate the Conda environment,
* launch distributed training via 🤗 Accelerate.

For authentication and caching requirements, see:

* `docs/huggingface_authentication.md`

---

## Output artifacts

A training run produces:

* a PEFT adapter directory (`adapter_model.safetensors`, `adapter_config.json`),
* training logs and metrics,
* optional W&B artifacts.

The adapter directory can be used directly for inference as described in the main README.

---

## Notes
* Training large models (e.g. 9B) requires substantial GPU memory and is recommended only on HPC systems.
* Few-shot training significantly increases compute cost.
* For most users, pretrained adapters are sufficient and retraining is unnecessary.
