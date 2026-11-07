# Hugging Face authentication

The TxGemma base models are gated. Request access once on each model page:
[txgemma-9b-predict](https://huggingface.co/google/txgemma-9b-predict),
[txgemma-2b-predict](https://huggingface.co/google/txgemma-2b-predict),
[txgemma-9b-chat](https://huggingface.co/google/txgemma-9b-chat) (chat explanations only).

Create a read-only token at <https://huggingface.co/settings/tokens>, then either:

```bash
huggingface-cli login            # stores ~/.huggingface/token; the SLURM scripts read it
export HUGGINGFACE_TOKEN=hf_...  # or set it in the environment / a private file you source
```

The token is only needed for the first download; models are then cached in `$HF_HOME`.
Never commit tokens or hard-code them in scripts.
