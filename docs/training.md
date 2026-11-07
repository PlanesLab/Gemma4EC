# Training

Only needed to retrain on your own data; the Hugging Face adapters cover normal use.

Gemma4EC fine-tunes TxGemma-Predict with a PEFT adapter (LoRA by default; DoRA, AdaLoRA available). The base
weights stay frozen; only the adapter is saved.

## Data

A folder with `train.csv`, `val.csv`, `test.csv`, each with `rxn_smiles` and `ec` columns:

```text
rxn_smiles,ec
CCO.O=O>>CC=O.OO,1.1.3
```

Benchmark splits: `python scripts/make_seed_splits.py` → `data/ECReact_seeds_strat_dedup/seed{0..9}/`.

## Run

```bash
python main.py \
  --raw_data_folder       data/ECReact_seeds_strat_dedup/seed0 \
  --processed_data_folder data/processed \
  --prompts_json_path     prompts/prompts.json \
  --template_key          EC_NUMBER_PROMPT_2 \
  --template_alias        EC_NUMBER \
  --trainer_mode manual --save_best true --disable_wandb
```

On SLURM (4 GPUs, Accelerate): `sbatch slurm/run_train_gemma4ec_9b.sh` (2B: `MODEL_ID=google/txgemma-2b-predict`).

## Main arguments

| Argument | Default | |
|---|---|---|
| `--trainer_mode` | `sft` | `manual` = custom loop with per-epoch EC metrics, early stopping, best checkpoint |
| `--batch_size` / `--gradient_accumulation_steps` | 8 / 4 | effective batch = batch × accum × GPUs |
| `--learning_rate` | 5e-4 | cosine schedule |
| `--num_train_epochs` | 30 | |
| `--max_seq_length` | 512 | raise for few-shot (1024–1408) |
| `--adapter_method` | `lora` | `lora`, `dora`, `adalora` |
| `--lora_r` / `--lora_alpha` / `--lora_dropout` | 16 / 16 / 0.0 | |
| `--model_id` | `google/txgemma-9b-predict` | |
| `--monitor_metric` | `mcc` | `accuracy`, `mcc`, `f1_macro` |
| `--early_stopping_patience` | 5 | |
| `--few_shot_training`, `--few_shot_ratio`, `--few_shot_k_min/max` | off, 0.3, 1/10 | in-context examples mixed into training prompts |
| `--wandb_project`, `--wandb_entity` / `--disable_wandb` | | optional W&B logging |

Output: `adapter_model.safetensors` + `adapter_config.json`, usable directly with `predict.py`.
The 9B model needs an A100 80 GB or 4× A100 40 GB.
