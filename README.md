# Gemma4EC

<table>
  <tr>
    <td width="55%" valign="top">
      Predict Enzyme Commission (EC) numbers from biochemical reaction SMILES using Gemma4EC, a fine-tuned large language model.<br><br>
      Gemma4EC builds on <a href="https://deepmind.google/models/gemma/txgemma/">TxGemma</a> (Google's therapeutics LLM) and fine-tunes it for EC annotation via lightweight LoRA adapters.<br><br>
      <h2>Contents</h2>
      • <a href="#before-you-start">Before you start</a><br>
      • <a href="#installation">Installation</a><br>
      • <a href="#data">Data</a><br>
      • <a href="#predict-ec-numbers">Predict EC numbers</a><br>
      • <a href="#mechanistic-explanation">Mechanistic explanation</a><br>
      • <a href="#zero-shot-evaluation">Zero-shot evaluation</a><br>
      • <a href="#fine-tuning">Fine-tuning</a><br>
      • <a href="#benchmark-partitions">Benchmark partitions</a><br>
      • <a href="#hpc--slurm">HPC / SLURM</a><br>
      • <a href="#results">Results</a><br>
      • <a href="#project-structure">Project structure</a><br>
      • <a href="#cite">Cite</a><br>
      • <a href="#contact">Contact</a>
    </td>
    <td width="45%" valign="top" align="center">
      <img src="figures/gemma4ec.png" width="100%" style="border: 2.5px solid #555555;"/>
      <br>
      <em>Gemma4EC inference pipeline: TxGemma backbone with a LoRA adapter, a structured reaction SMILES prompt, and the predicted EC number as output.</em>
    </td>
  </tr>
</table>

---

## Before you start

You will need:

**1. A Hugging Face account** — [sign up here](https://huggingface.co/join)

**2. Access to [TxGemma](https://deepmind.google/models/gemma/txgemma/)** — request it on the model page (usually approved in minutes):
- [txgemma-9b-predict](https://huggingface.co/google/txgemma-9b-predict) — best accuracy
- [txgemma-2b-predict](https://huggingface.co/google/txgemma-2b-predict) — lighter, lower VRAM
- [txgemma-9b-chat](https://huggingface.co/google/txgemma-9b-chat) — required for mechanistic explanation

**3. A GPU with enough VRAM:**

| Model | Min VRAM | Recommended hardware |
|---|---|---|
| `txgemma-9b-predict` | ~18 GB | A100 (40 GB), H100 |
| `txgemma-2b-predict` | ~6 GB | Any modern research GPU |
| Mechanistic explanation (4-bit) | ~12 GB | Any modern research GPU |

---

## Installation

```bash
git clone https://github.com/PlanesLab/gemma4ec.git
cd gemma4ec
conda env create -f envs/gemma4ec_env.yaml
conda activate gemma4ec
```

Log in to Hugging Face once (saves your token locally):
```bash
huggingface-cli login
```

---

## Data

All datasets are included in this repository under `data/`.

```
data/
├── ECReact/
│   ├── train.csv   (~49 k reactions)
│   ├── val.csv     (~6 k reactions)
│   └── test.csv    (~6 k reactions)
└── partitions/
    ├── Rhea_Scaffold/   train / val / test
    ├── Rhea_Stratified/ train / val / test
    └── Rhea_Time/       train / val / test
```

The ECReact split is derived from [ECReact-1.0](https://github.com/rxn4chemistry/biocatalysis-model/blob/main/data/ecreact-1.0.csv), a curated dataset of enzyme-catalysed reactions in SMILES format. The three Rhea partitions are built from the same reactions re-split using [Rhea](https://www.rhea-db.org/) metadata (scaffold, stratified, time).

Each CSV contains at minimum:

| Column | Description |
|---|---|
| `rxn_smiles` | Reaction SMILES string |
| `ec` | EC number label (e.g. `1.1.1.1`) |

The three Rhea partitions are described in the [Benchmark partitions](#benchmark-partitions) section.
To regenerate partition splits from `data/ECReact/`, see [`scripts/prepare_db.py`](scripts/prepare_db.py).

---

## Predict EC numbers

### Step 1 — Download the adapter

```bash
git clone https://huggingface.co/PlanesLab/Gemma4EC-9B-Predict models/Gemma4EC-9B-Predict
```

The folder must contain `adapter_model.safetensors` and `adapter_config.json`.

### Step 2 — Prepare your input CSV

Create a CSV with at minimum a `rxn_smiles` column:

```csv
rxn_smiles
CC(=O)O>>CC(=O)[O-]
OC(=O)CCC(=O)C(=O)O>>OC(=O)CCC(N)C(=O)O
```

### Step 3 — Run prediction

```bash
python predict.py \
  --raw_data_file reactions.csv \
  --model_checkpoint_folder models/Gemma4EC-9B-Predict
```

Predictions are saved as a TSV in `outputs/results/`.

**Using the 2B model:**
```bash
python predict.py \
  --raw_data_file reactions.csv \
  --model_checkpoint_folder models/Gemma4EC-2B-Predict \
  --model_id google/txgemma-2b-predict
```

**Key arguments:**

| Argument | Default | Description |
|---|---|---|
| `--raw_data_file` | *(required)* | Input CSV with `rxn_smiles` column |
| `--model_checkpoint_folder` | *(required)* | Path to the adapter folder |
| `--model_id` | `google/txgemma-9b-predict` | Base model ID |
| `--output_folder` | `./outputs/results` | Where to save the prediction TSV |
| `--eval_batch_size` | `8` | Reduce if you run out of VRAM |

For an interactive prediction demo see [`notebooks/predict_ec_numbers.ipynb`](notebooks/predict_ec_numbers.ipynb).

---

## Mechanistic Explanation

Beyond EC prediction, Gemma4EC provides tools to **explain why** a particular EC number was assigned — grounding the model's output in attention weights and enzymatic literature.

Two entry points are available:

| Entry point | Description |
|---|---|
| [`notebooks/mechanistic_explanation.ipynb`](notebooks/mechanistic_explanation.ipynb) | Interactive notebook: attention heatmap widget + 4-turn TxGemma-Chat dialogue |
| [`infer_attention.py`](infer_attention.py) | Script version: batch attention inference, BertViz HTML exports, and attention heatmap PNGs |

### How the pipeline works

Three components run in sequence:

1. **Gemma4EC-9B-Predict** takes a reaction SMILES and predicts its EC number while returning layer-wise attention tensors.
2. **[BertViz](https://github.com/jessevig/bertviz)** renders an interactive attention heatmap over the SMILES tokens and produces a normalised per-token importance score showing which substructures drove the prediction.
3. **[TxGemma-9B-Chat](https://huggingface.co/google/txgemma-9b-chat)** receives the reaction, the predicted EC, the attention profile, and a BRENDA sub-subclass summary, then builds a step-by-step catalytic mechanism across four conversational turns.

### Quick start — notebook

```bash
pip install bertviz   # not bundled in the main env
jupyter notebook notebooks/mechanistic_explanation.ipynb
```

### Quick start — script (batch)

```bash
# Sample 10 reactions from the test set, save HTML + PNG outputs to ./attn_out/
python infer_attention.py

# Low-VRAM option (4-bit NF4, ~12 GB)
python infer_attention.py --load_in_4bit

# Use a Rhea partition adapter
python infer_attention.py --adapter_path results/Rhea_Stratified/results/best

# Custom input
python infer_attention.py --test_csv my_reactions.csv --n 50 --output_dir ./my_attn
```

**Key arguments for `infer_attention.py`:**

| Argument | Default | Description |
|---|---|---|
| `--adapter_path` | ECReact best adapter | Path to LoRA adapter dir (pass `""` for zero-shot) |
| `--test_csv` | `data/ECReact/test.csv` | Input CSV with `rxn_smiles` column |
| `--n` | `10` | Number of reactions to sample |
| `--output_dir` | `./attn_out` | Output directory for HTML, PNG, and TSV |
| `--load_in_4bit` | off | Enable 4-bit NF4 quantisation (~12 GB VRAM) |

### Expected outputs

| Output | Description |
|---|---|
| `attn_out/<rxn_id>_head_view.html` | BertViz interactive head-view (open in a browser) |
| `attn_out/<rxn_id>_attn_heatmap.png` | Attention heatmap over SMILES tokens |
| `attn_out/summary.tsv` | SMILES / true EC / predicted EC / correctness per reaction |

> **Note:** `infer_attention.py` requires `bertviz` to be installed in the active environment (`pip install bertviz`). TxGemma-9B-Chat access is only needed for the notebook pipeline; the script uses the Predict model only.

---

## Zero-shot evaluation

Evaluate the base [TxGemma](https://deepmind.google/models/gemma/txgemma/) model without any fine-tuning:

```bash
python predict_zeroshot.py \
  --test_csv data/ECReact/test.csv \
  --output_folder outputs/zeroshot
```

| Argument | Default | Description |
|---|---|---|
| `--test_csv` | `data/ECReact/test.csv` | Input CSV |
| `--output_folder` | `./outputs/zeroshot` | Output directory |
| `--eval_batch_size` | `16` | Batch size for generation |
| `--max_retries` | `5` | Per-sample retries for malformed outputs |
| `--disable_wandb` | — | Disable W&B logging |

---

## Fine-tuning

Fine-tune [TxGemma](https://deepmind.google/models/gemma/txgemma/) on your own reaction dataset using LoRA.

**Minimal usage:**
```bash
python main.py \
  --raw_data_folder data/ECReact \
  --disable_wandb
```

**Full example (with W&B logging):**
```bash
python main.py \
  --raw_data_folder data/ECReact \
  --model_id google/txgemma-9b-predict \
  --num_train_epochs 30 \
  --batch_size 8 \
  --lora_r 16 \
  --save_best true \
  --monitor_metric mcc \
  --wandb_project my_project \
  --wandb_entity my_team
```

**Key arguments:**

| Argument | Default | Description |
|---|---|---|
| `--model_id` | `google/txgemma-9b-predict` | Base model |
| `--num_train_epochs` | `30` | Training epochs |
| `--batch_size` | `8` | Per-device batch size |
| `--gradient_accumulation_steps` | `4` | Effective batch = batch × accum × n_gpus |
| `--learning_rate` | `5e-4` | Learning rate |
| `--lora_r` | `16` | LoRA rank |
| `--lora_alpha` | `16` | LoRA alpha |
| `--adapter_method` | `lora` | Adapter type: `lora`, `dora`, `adalora` |
| `--save_best` | `false` | Save best checkpoint by `--monitor_metric` |
| `--monitor_metric` | `mcc` | Metric for early stopping: `accuracy`, `mcc`, `f1_macro` |
| `--early_stopping_patience` | `5` | Stop after N epochs with no improvement |
| `--use_test` | `false` | Evaluate on test split after training |
| `--few_shot_training` | `false` | Mix few-shot examples into training prompts |
| `--disable_wandb` | — | Disable W&B logging |

Full documentation: [`docs/training.md`](docs/training.md)

---

## Benchmark partitions

To assess generalisation beyond random splits, we evaluate Gemma4EC on three [Rhea](https://www.rhea-db.org/) partitions
built from the same underlying dataset:

| Partition | Split strategy | Challenge |
|---|---|---|
| **Rhea_Scaffold** | Reactions grouped by Murcko scaffold — different scaffolds in train vs. test | Chemical novelty |
| **Rhea_Stratified** | Stratified random split preserving EC class balance | Standard baseline |
| **Rhea_Time** | Chronological split by reaction entry date | Temporal generalisation |

Data for all three partitions is in `data/partitions/`. To re-generate them from `data/ECReact/`:

```bash
python scripts/prepare_db.py --db Rhea_Scaffold   --out_root data/partitions
python scripts/prepare_db.py --db Rhea_Stratified --out_root data/partitions
python scripts/prepare_db.py --db Rhea_Time       --out_root data/partitions
```

To aggregate metrics across all models and partitions into a comparison table:

```bash
python scripts/summarize_results.py
```

---

## HPC / SLURM

For running on a cluster, all Gemma4EC workflows have SLURM scripts in `slurm/`. Baseline model workflows are in their own subdirectories under `benchmarking/`.

**Fine-tune Gemma4EC-9B on all three partitions:**
```bash
export HUGGINGFACE_TOKEN=hf_...
export WANDB_API_KEY=...
bash slurm/submit_all_partitions.sh
```

**Fine-tune Gemma4EC-2B on all three partitions:**
```bash
bash slurm/submit_all_partitions_2b.sh
```

**Theia baseline on all three partitions:**
```bash
bash benchmarking/theia/slurm/submit_all_partitions_theia.sh
```

**BEC-Pred baseline on all three partitions:**
```bash
bash benchmarking/bec-pred/slurm/submit_all_partitions_becpred.sh
```

**Single partition (any model):**
```bash
DB_NAME=Rhea_Time sbatch slurm/run_train_partition.sh                           # 9B
DB_NAME=Rhea_Time sbatch slurm/run_train_partition_2b.sh                        # 2B
DB_NAME=Rhea_Time sbatch benchmarking/theia/slurm/run_train_theia.sh            # Theia
DB_NAME=Rhea_Time sbatch benchmarking/bec-pred/slurm/run_becpred.sh             # BEC-Pred
```

**Re-evaluate a saved checkpoint (no retraining):**
```bash
DB_NAME=Rhea_Time sbatch slurm/run_predict_partition.sh
```

**Zero-shot baseline:**
```bash
sbatch slurm/run_predict_zeroshot.sh
```

See [`slurm/README.md`](slurm/README.md) for the full list of Gemma4EC scripts and options.

---

## Results

### Standard benchmark (ECReact test set)

Support-weighted MCC across all EC sub-subclasses:

| Model | Overall MCC | EC1 | EC2 | EC3 | EC4 | EC5 | EC6 | EC7 |
|---|---|---|---|---|---|---|---|---|---|
| **Gemma4EC-9b** | **0.903** | 0.847 | 0.971 | 0.771 | 0.848 | 0.779 | 0.895 | 0.433 |
| [BEC-Pred](https://github.com/KeeliaQWJ/BEC-Pred) | 0.886 | 0.799 | 0.965 | 0.777 | 0.834 | 0.681 | 0.869 | 0.314 |
| [Theia](https://github.com/daenuprobst/theia) | 0.884 | 0.824 | 0.961 | 0.743 | 0.808 | 0.729 | 0.829 | 0.501 |
| Gemma4EC-2b | 0.897 | 0.852 | 0.970 | 0.734 | 0.819 | 0.773 | 0.868 | 0.426 |
| [Gemini 2.5 Flash](https://ai.google.dev/gemini-api/docs?hl=es-419) | 0.774 | 0.593 | 0.927 | 0.555 | 0.737 | 0.496 | 0.669 | 0.000 |
| [ChatGPT-5 (v2)](https://openai.com/es-ES/api/) | 0.531 | 0.354 | 0.721 | 0.317 | 0.181 | 0.383 | 0.180 | 0.000 |
| [ChatGPT-5.1](https://openai.com/es-ES/api/) | 0.297 | 0.105 | 0.430 | 0.232 | 0.115 | 0.323 | 0.097 | 0.000 |
| [ChatGPT-4.1-mini](https://openai.com/es-ES/api/) | 0.224 | 0.087 | 0.342 | 0.136 | 0.051 | 0.057 | 0.028 | 0.000 |
| [TxGemma-9b (zero-shot)](https://deepmind.google/models/gemma/txgemma/) | ~0.000 | — | — | — | — | — | — | — |

### Benchmark partitions (Rhea splits)

Support-weighted MCC on the three [Rhea](https://www.rhea-db.org/) benchmark partitions:

| Partition | Gemma4EC-9b | Gemma4EC-2b | BEC-Pred |
|---|---|---|---|
| **Rhea_Scaffold** | **0.633** | 0.602 | 0.618 |
| **Rhea_Stratified** | **0.894** | 0.886 | 0.847 |
| **Rhea_Time** | **0.760** | 0.747 | 0.700 |

> Rhea_Scaffold splits by Murcko scaffold (chemical novelty challenge); Rhea_Stratified is a balanced random split; Rhea_Time is a chronological split (temporal generalisation). See [Benchmark partitions](#benchmark-partitions) for descriptions.

Metrics computed with [`results/compute_weighted_metrics.py`](results/compute_weighted_metrics.py) and [`results/compute_per_class_and_splits.py`](results/compute_per_class_and_splits.py). Full tables: [`results/summary/per_class_mcc.csv`](results/summary/per_class_mcc.csv) · [`results/summary/splits_weighted_mcc.csv`](results/summary/splits_weighted_mcc.csv).

---

## Project structure

```
Gemma4EC/
├── main.py                        # LoRA fine-tuning entry point
├── predict.py                     # Inference with a LoRA adapter
├── predict_zeroshot.py            # Zero-shot inference (no adapter)
├── predict_api.py                 # Inference via external LLM APIs (OpenAI / Gemini)
├── infer_attention.py             # Batch attention inference + BertViz HTML/PNG outputs
│
├── data/
│   ├── ECReact/                   # Full dataset from ECReact-1.0 (train / val / test CSVs)
│   └── partitions/                # Rhea_Scaffold / Rhea_Stratified / Rhea_Time splits
│
├── envs/
│   └── gemma4ec_env.yaml          # Conda environment
│
├── figures/                       # Paper figures
│
├── prompts/
│   └── prompts.json               # Prompt templates (few-shot, zero-shot, API, etc.)
│
├── results/
│   ├── compute_weighted_metrics.py        # Reproduce main benchmark table (weighted MCC)
│   ├── compute_per_class_and_splits.py    # Reproduce per-class and partition tables
│   ├── bec-pred/
│   │   └── results_test_ec.csv            # BEC-Pred predictions on the standard test set
│   ├── summary/
│   │   ├── weighted_metrics.csv           # All models — overall weighted MCC/PPV/Recall
│   │   ├── per_class_mcc.csv              # All models — MCC per EC class (1–7)
│   │   └── splits_weighted_mcc.csv        # Rhea splits — Gemma4EC / BEC-Pred / Theia
│   ├── ECReact/                           # Gemma4EC-9b fine-tuned on ECReact
│   │   └── results/best/                  # adapter_config.json + predictions TSV
│   ├── Rhea_Scaffold/                     # Gemma4EC-9b — Rhea_Scaffold
│   ├── Rhea_Stratified/                   # Gemma4EC-9b — Rhea_Stratified
│   ├── Rhea_Time/                         # Gemma4EC-9b — Rhea_Time
│   ├── Rhea_Scaffold_2b/                  # Gemma4EC-2b — Rhea_Scaffold
│   ├── Rhea_Stratified_2b/                # Gemma4EC-2b — Rhea_Stratified
│   ├── Rhea_Time_2b/                      # Gemma4EC-2b — Rhea_Time
│   ├── Gemma4EC-9b/                       # 9b predictions on ECReact test set
│   ├── Gemma4EC-2b/                       # 2b predictions on ECReact test set
│   ├── APIs/                              # API model predictions (OpenAI / Gemini)
│   ├── Theia/                             # Theia baseline predictions
│   └── zeroshot/                          # TxGemma zero-shot predictions
│
├── scripts/
│   ├── prepare_db.py              # Generate Rhea partition splits
│   ├── canonicalize_smiles.py     # Canonicalize rxn_smiles in all data CSVs
│   ├── summarize_results.py       # Aggregate metrics across models
│   ├── slim_bertviz.py            # Slim down BertViz HTML output files
│   └── make_attn_plotly.py        # Convert BertViz HTML to Plotly visualisations
│
├── slurm/                         # SLURM scripts for Gemma4EC workflows
│   ├── run_train_partition.sh        # Fine-tune TxGemma-9B on one Rhea partition
│   ├── submit_all_partitions.sh      # Submit all three 9B partition jobs
│   ├── run_train_partition_2b.sh     # Fine-tune TxGemma-2B on one Rhea partition
│   ├── submit_all_partitions_2b.sh   # Submit all three 2B partition jobs
│   ├── run_train_gemma4ec_9b.sh      # Fine-tune on raw ECReact (non-partitioned)
│   ├── run_predict_partition.sh      # Evaluate a saved adapter (no retraining)
│   ├── run_predict_gemma4ec.sh       # Large-scale prediction with a local adapter
│   ├── run_predict_zeroshot.sh       # Zero-shot evaluation (no adapter)
│   ├── run_predict_api.sh            # API benchmarking (OpenAI / Gemini)
│   ├── run_train_chat.sh             # Fine-tune TxGemma-Chat for mechanistic explanation
│   ├── run_rag_infer.sh              # RAG-based mechanistic inference with BRENDA
│   ├── submit_chat_pipeline.sh       # Submit full chat fine-tune + RAG pipeline
│   └── README.md
│
├── src/
│   ├── config.py
│   ├── datamod/                   # Data loading, prompt templates, JSONL builder
│   ├── evaluation/                # Evaluation loop, EC parsing, metrics saving
│   ├── models/                    # Model loading, PEFT config
│   ├── training/                  # SFT trainer, manual DDP loop, callbacks, checkpointing
│   └── utils/                     # Metrics, path helpers, sequence length checks
│
├── benchmarking/
│   ├── bec-pred/                  # BEC-Pred baseline pipeline
│   │   ├── BECPred/               # Training and evaluation scripts
│   │   ├── DB/                    # Pre-built ECReact DB (train/val/test CSVs)
│   │   ├── run_becpred.sh         # Main pipeline runner
│   │   ├── becpred_gpu.yml        # Conda environment
│   │   ├── slurm/
│   │   │   ├── run_becpred.sh
│   │   │   └── submit_all_partitions_becpred.sh
│   │   └── README.md
│   └── theia/                     # Theia MLP baseline pipeline
│       ├── train_theia.py         # Train Theia MLP
│       ├── eval_theia.py          # Evaluate Theia MLP
│       └── slurm/
│           ├── run_train_theia.sh
│           ├── run_eval_theia.sh
│           ├── run_theia_full.sh
│           └── submit_all_partitions_theia.sh
│
├── chat/                          # TxGemma-Chat fine-tuning + RAG for mechanistic explanation
│   ├── finetune_chat.py           # Fine-tune TxGemma-Chat on mechanistic prompts
│   ├── rag_infer.py               # RAG inference with BRENDA knowledge base
│   ├── build_brenda_index.py      # Build BRENDA vector index
│   ├── build_mechanistic_prompts.py # Generate training prompts from BRENDA
│   ├── chat_txgemma.py            # Interactive chat wrapper
│   ├── data/brenda_index.json     # Pre-built BRENDA index
│   └── prompts/mechanistic_prompts.json  # Mechanistic explanation prompt templates
│
├── notebooks/
│   ├── predict_ec_numbers.ipynb       # Interactive EC prediction demo
│   └── mechanistic_explanation.ipynb  # Attention heatmap + 4-turn TxGemma-Chat mechanism
│
└── docs/
    ├── training.md                    # Fine-tuning guide
    ├── prediction_hpc.md              # Large-scale HPC prediction
    ├── huggingface_authentication.md  # HF token setup
    ├── api_benchmarking.md            # OpenAI / Gemini benchmarking
    └── becpred_benchmarking.md        # BEC-Pred baseline guide
```

---

## Cite

> Citation to be added.

---

## Contact

| Name | Email |
|---|---|
| Josefina Arcagni | jarcagniriv@unav.es |
| Joseba Sancho-Zamora | jsanchoz@unav.es |
