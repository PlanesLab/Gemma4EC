# SLURM scripts

Submit from the repository root. Scripts read `./config.sh` (from `config.sh.example`); any variable can be set on the
command line (`VAR=value sbatch ...`). Adjust `--partition`, `--gres`, `--mem` and `--time` to your cluster.
Hugging Face: `huggingface-cli login` once, or export `HUGGINGFACE_TOKEN`.

| Script | What it does |
|---|---|
| `run_predict_gemma4ec.sh` | EC prediction (`MODEL_CHECKPOINT_FOLDER=models/Gemma4EC-9B-Predict RAW_DATA_FILE=reactions_prep.csv`) |
| `run_chat.sh` | chat explanations (`IN=reactions_prep.csv OUT=chat_out`) |
| `run_train_gemma4ec_9b.sh` | LoRA fine-tuning on your own data (2B: `MODEL_ID=google/txgemma-2b-predict`) |
