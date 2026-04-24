# Hugging Face authentication for Gemma4EC
This document explains how to authenticate with the Hugging Face Hub in order to **automatically download and cache the TxGemma base models** used by Gemma4EC.

Authentication is required in most environments, and **mandatory on HPC / SLURM systems**, where anonymous downloads are typically blocked.

---

## Why authentication is required
Gemma4EC relies on **TxGemma-Predict** base models hosted on the Hugging Face Hub (e.g. `google/txgemma-9b-predict`).

Although these models are downloaded automatically by the 🤗 `transformers` library, **access to the repository requires authentication**.

Without a valid Hugging Face token:

* the base model download will fail,
* prediction and training jobs will not start,
* caching across jobs and nodes will not work.

Once the model is cached locally, authentication is no longer required for subsequent runs.

---

## Create a Hugging Face access token
1. Go to: [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Create a **read-only** access token
3. Copy the token (it starts with `hf_...`)

> A read-only token is sufficient for all Gemma4EC use cases.

---

## Making the token available
### Recommended: secrets script (safe and reusable)
Create a private file **not tracked by git**, for example:

```bash
~/.secrets_hf.sh
```

with the following content:

```bash
export HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxx
```

Then source it in your shell:

```bash
source ~/.secrets_hf.sh
```

You may also add this line to your `.bashrc` or `.bash_profile` if appropriate.

---

### Using the token in SLURM jobs (HPC)
When running Gemma4EC on an HPC cluster, the token must be visible **inside the batch job**.

The recommended approach is to source the secrets file directly in the SLURM script:

```bash
source ~/.secrets_hf.sh
```

The Gemma4EC SLURM scripts pass the token explicitly to the prediction code:

```bash
--hf_token $HUGGINGFACE_TOKEN
```

Internally, this enables:

* automatic download of the TxGemma base model,
* proper caching in `$HF_HOME` / `$TRANSFORMERS_CACHE`,
* reuse of the cached model across multiple runs and jobs.

---

## Notes on caching behavior
* The Hugging Face token is **only required for the initial download** of the base model.
* Once cached, the model will not be downloaded again.
* Cached models can be reused across:

  * multiple prediction runs,
  * different SLURM jobs,
  * training and inference workflows.

---

## Security best practices
* **Never commit tokens** to the repository.
* Always use environment variables or private scripts.
* Prefer read-only tokens.
* Do not hard-code tokens in SLURM scripts or Python files.

---

## Related documentation
* For local and HPC prediction workflows, see: `docs/prediction_hpc.md`
* For training pipelines, see: `docs/training.md`
* For model architecture and design choices, see: `docs/model_details.md`
