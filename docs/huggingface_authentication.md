# Hugging Face authentication

This document explains how to authenticate with the Hugging Face Hub in order to **automatically download and cache the TxGemma base models** used by Gemma4EC.

Authentication is required in most environments and **mandatory on HPC / SLURM systems**, where anonymous downloads are typically blocked.

---

## Why authentication is required

Gemma4EC relies on **TxGemma-Predict** (and optionally **TxGemma-Chat**) base models hosted on the Hugging Face Hub.

Although these models are downloaded automatically by the 🤗 `transformers` library, **access requires authentication**. Without a valid token:

- the base model download will fail,
- prediction and training jobs will not start,
- model caching across jobs and nodes will not work.

Once the model is cached locally, the token is no longer needed for subsequent runs.

---

## Models that require access

Request access on each model's Hub page before running Gemma4EC:

| Model | Hub page | Used for |
|---|---|---|
| `google/txgemma-9b-predict` | [link](https://huggingface.co/google/txgemma-9b-predict) | Fine-tuning + inference (9B) |
| `google/txgemma-2b-predict` | [link](https://huggingface.co/google/txgemma-2b-predict) | Fine-tuning + inference (2B) |
| `google/txgemma-9b-chat` | [link](https://huggingface.co/google/txgemma-9b-chat) | Mechanistic explanation notebook |

Access is typically approved within minutes.

---

## Creating a Hugging Face access token

1. Go to [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
2. Create a **read-only** access token (sufficient for all Gemma4EC use cases).
3. Copy the token — it starts with `hf_...`.

---

## Making the token available

### Option 1 — Interactive login (local use)

```bash
huggingface-cli login
```

This stores the token in `~/.huggingface/token` and is automatically picked up by `transformers`.

### Option 2 — Environment variable (recommended for scripts and HPC)

Create a private file **not tracked by git**, for example `~/.secrets_hf.sh`:

```bash
export HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxx
```

Then source it in your shell before running:

```bash
source ~/.secrets_hf.sh
```

You may also add this to your `.bashrc` or `.bash_profile` if appropriate.

### Option 3 — Inline export (one-off)

```bash
export HUGGINGFACE_TOKEN=hf_...
python predict.py ...
```

---

## Using the token in SLURM jobs (HPC)

The token must be visible **inside the batch job**. Source the secrets file directly in the SLURM script:

```bash
source ~/.secrets_hf.sh
```

The Gemma4EC SLURM scripts pass the token to the Python code via:

```bash
--hf_token $HUGGINGFACE_TOKEN
```

This enables:
- automatic download of the TxGemma base model,
- proper caching in `$HF_HOME` / `$TRANSFORMERS_CACHE`,
- reuse of the cached model across multiple runs and jobs.

---

## Notes on caching

- The token is **only required for the initial download**.
- Once cached, the model will not be re-downloaded.
- Cached models are reused across prediction runs, training jobs, and SLURM arrays.
- To control the cache location, set `HF_HOME` or `TRANSFORMERS_CACHE` before running.

---

## Security best practices

- **Never commit tokens** to the repository.
- Always use environment variables or private scripts.
- Prefer read-only tokens.
- Do not hard-code tokens in SLURM scripts or Python files.

---

## Related documentation

- Local and HPC prediction: [`docs/prediction_hpc.md`](prediction_hpc.md)
- Training and fine-tuning: [`docs/training.md`](training.md)
- SLURM scripts: [`slurm/README.md`](../slurm/README.md)
