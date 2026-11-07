# Prediction on a SLURM cluster

`slurm/run_predict_gemma4ec.sh` runs `predict.py` through Accelerate on all allocated GPUs. Paths come from
`config.sh` (copy `config.sh.example`) and can be overridden per job:

```bash
git clone https://huggingface.co/PlanesLab/Gemma4EC-9B-Predict models/Gemma4EC-9B-Predict
MODEL_CHECKPOINT_FOLDER=models/Gemma4EC-9B-Predict \
RAW_DATA_FILE=reactions.csv \
OUTPUT_FOLDER=$SCRATCH/gemma4ec/predict \
sbatch slurm/run_predict_gemma4ec.sh
```

| Variable | Default |
|---|---|
| `RAW_DATA_FILE` | CSV with a `rxn_smiles` column |
| `MODEL_CHECKPOINT_FOLDER` | adapter dir (`adapter_model.safetensors`, `adapter_config.json`) |
| `MODEL_ID` | `google/txgemma-9b-predict` (2B adapter: `google/txgemma-2b-predict`) |
| `TEMPLATE_KEY` | `EC_NUMBER_PROMPT_2`, the training prompt; do not change |
| `OUTPUT_FOLDER`, `PROCESSED_DATA_FOLDER` | under `$SCRATCH_ROOT/gemma4ec/predict/` |

Output: `predictions_*.tsv` (schema in [`results/README.md`](../results/README.md)). The base model is downloaded
once and cached in `$HF_HOME`; the job needs a Hugging Face token ([`huggingface_authentication.md`](huggingface_authentication.md)).
