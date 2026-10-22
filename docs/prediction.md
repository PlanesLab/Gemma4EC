# Prediction

## Predict EC numbers

```bash
python predict.py --raw_data_file reactions.csv --model_checkpoint_folder models/Gemma4EC-9B-Predict
```

The input CSV needs a `rxn_smiles` column. Predictions are written as a TSV to `--output_folder`.

| Argument | Default | Description |
|---|---|---|
| `--raw_data_file` | *(required)* | Input CSV with a `rxn_smiles` column |
| `--model_checkpoint_folder` | *(required)* | Adapter folder (`adapter_model.safetensors` + `adapter_config.json`) |
| `--model_id` | `google/txgemma-9b-predict` | Base model |
| `--output_folder` | `./outputs/results` | Where the prediction TSV is written |
| `--eval_batch_size` | `8` | Lower it if you run out of GPU memory |

## 2B model

The 2B model needs about 6 GB of GPU memory and is slightly less accurate (MCC 0.903 vs 0.908). Pass the 2B base
model and a 2B adapter:

```bash
python predict.py --raw_data_file reactions.csv --model_checkpoint_folder path/to/Gemma4EC-2B-adapter \
    --model_id google/txgemma-2b-predict
```

To train a 2B adapter, see [`training.md`](training.md) (`MODEL_ID=google/txgemma-2b-predict`).

## Prediction with attention

`infer_attention.py` predicts and also saves the attention of the tokens that generate the EC number, per SMILES
token (`rxnNN_smiles_attn.npz`), as an interactive BertViz page and as a heatmap PNG. It writes `summary.tsv` with
the predicted EC and the top-3 alternatives with their probabilities.

```bash
python infer_attention.py --test_csv reactions.csv --n 0 --output_dir attn_out    # --n 0: every row, in order
python infer_attention.py --test_csv data/ECReact_seeds_strat_dedup/seed0/test.csv --n 10                 # 10 random test reactions
python infer_attention.py ... --load_in_4bit                                      # ~12 GB GPU
```

Without a GPU it runs on CPU in float32 (slow, about 6 minutes per reaction on 11 cores).

## Zero-shot baseline

TxGemma without fine-tuning:

```bash
python predict_zeroshot.py --test_csv data/ECReact_seeds_strat_dedup/seed0/test.csv --output_folder outputs/zeroshot
```

## Hardware

| Model | GPU memory |
|---|---|
| Gemma4EC-9B (bf16) | ~20 GB (A100, L40S, RTX 3090/4090) |
| Gemma4EC-9B (4-bit, attention only) | ~12 GB |
