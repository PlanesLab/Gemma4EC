# SLURM scripts

Job templates for running Gemma4EC on a cluster. Submit them from the repository root. Each script reads
`./config.sh` (copy it from `config.sh.example`) for interpreter and data paths, and every variable can also be
overridden on the command line (`VAR=value sbatch ...`). Adjust `--partition`, `--gres`, `--mem` and `--time` to your
cluster.

Hugging Face: run `huggingface-cli login` once (scripts read `~/.huggingface/token`), or export `HUGGINGFACE_TOKEN`.
W&B logging is optional (`WANDB_API_KEY`, `WANDB_ENTITY`).

## EC prediction and training

| Script | What it does | Example |
|---|---|---|
| `run_predict_gemma4ec.sh` | predict EC numbers for a CSV | `MODEL_CHECKPOINT_FOLDER=models/Gemma4EC-9B-Predict RAW_DATA_FILE=reactions.csv sbatch slurm/run_predict_gemma4ec.sh` |
| `run_train_gemma4ec_9b.sh` | LoRA fine-tuning on `data/ECReact_seeds_strat_dedup/seed0` | `sbatch slurm/run_train_gemma4ec_9b.sh` (2B: add `MODEL_ID=google/txgemma-2b-predict`) |
| `run_predict_zeroshot.sh` | TxGemma without fine-tuning | `sbatch slurm/run_predict_zeroshot.sh` |
| `run_attention_cpu.sh` | prediction + attention on CPU | `TEST_CSV=reactions.csv OUT=attn_out N=0 sbatch slurm/run_attention_cpu.sh` |

## Chat explanations ([docs/chat.md](../docs/chat.md))

| Script | What it does |
|---|---|
| `run_mechanistic_v2.sh` | facts → candidate enzymes → chat explanation on GPU (`STEPS=attn,facts,prepare,explain`) |
| `run_mechanistic_v2_cpu.sh` | the explanation step on CPU |
| `run_facts_array.sh` | reaction facts for many reaction chunks (CPU array) |
| `run_finetune_explainer.sh` | LoRA fine-tuning of the chat model on teacher explanations |

## Benchmark ([docs/benchmark.md](../docs/benchmark.md))

| Script | What it does |
|---|---|
| `seeds/submit_seeds.sh` | submits the 10-seed benchmark (`SPLIT_SET`, `METHODS`, `SEEDS`, `DRY_RUN=1`) |
| `seeds/run_seed_*.sh` | one method on one seed (array task id = seed) |
| `seeds/run_tool_*.sh`, `seeds/run_selenzyme_*.sh` | SIMMER and SelenzymeRF on the pooled test reactions |
| `seeds/run_api_pool.sh` | an API model on the pooled test reactions |
| `run_predict_api.sh` | an API model on the original test set |
| `../benchmarking/theia/slurm/`, `../benchmarking/bec-pred/slurm/` | Theia and BEC-Pred on the original split |

Multi-GPU training uses Accelerate, with the number of processes taken from the allocated GPUs.
