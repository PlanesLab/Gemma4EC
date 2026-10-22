# results/seeds/ — ECReact 10-seed benchmark

Ten fresh random re-splits of ECReact (seeds 0–9) with the original train/val/test sizes (49,764 / 6,218 / 6,220). Every trained method is retrained on each seed and every model is evaluated on that seed's test set. Methods are then compared with paired tests across seeds.

## Methods

| Method | Script (`slurm/seeds/`) | Per seed |
|---|---|---|
| Gemma4EC-9b / 2b | `run_seed_gemma4ec.sh` (`MODEL_SIZE=9b\|2b`) | LoRA fine-tune (same hyperparameters as `run_train_gemma4ec_9b.sh`) + test prediction |
| TxGemma-9b (no FT) | `run_seed_txgemma_noft.sh` | Base `txgemma-9b-predict`, `EC_NUMBER_PROMPT_API`, up to 5 retries for malformed output |
| Theia | `run_seed_theia.sh` | DRFP-MLP trained on train, early stopping on val |
| BEC-Pred | `run_seed_becpred.sh` | RDKit-canonicalized SMILES → EC fine-tune from the shared label-free MLM-pretrained BERT → test prediction |
| CLAIRE | `run_seed_claire.sh` | rxnfp+DRFP embeddings, contrastive training (2,000 epochs), GMM-calibrated top-1 (code in `ECNumberPrediction/methods/CLAIRE`) |
| API models | `run_api_pool.sh` (`MODEL_NAME=...`) | Zero-shot with `EC_NUMBER_PROMPT_API`. Not per seed: see below |

## API models: one query per unique reaction

API models are zero-shot, so their answer does not depend on the seed. `scripts/make_api_pool.py` pools the 10 test sets into one list of unique reactions (`data/ECReact_seeds_strat_dedup/api_pool.csv`), each model runs once on that pool, and `scripts/fanout_api_predictions.py` writes the answers into every seed's `api/` folder.

Free tier: requests are spaced with `API_MIN_INTERVAL` (default 6 s ≈ 10 RPM). A per-minute 429 backs off and retries. When the daily quota runs out, the job stops and re-submits itself for after the reset, provided it made progress. `compute_seed_metrics.py` reports `coverage` until the pool is complete.

## API keys

Keep keys in a private file. Do not paste them into chat or commit them:

```bash
cat > ~/.gemma4ec_api_keys <<'KEYS'
export GEMINI_API_KEYS=key1          # comma-separated if you have several projects
# export OPENAI_API_KEY=...          # OpenAI has no free API tier
KEYS
chmod 600 ~/.gemma4ec_api_keys
```

Jobs source it automatically (override the path with `API_KEYS_FILE`).

## Run

```bash
python scripts/make_seed_splits.py                  # data/ECReact_seeds/seed{0..9}/ (already generated)
python scripts/check_api_models.py --list           # confirm model IDs available to your key
DRY_RUN=1 bash slurm/seeds/submit_seeds.sh          # preview
bash slurm/seeds/submit_seeds.sh                    # submit (SEEDS / METHODS / API_MODELS to subset)
```

Per-seed outputs go to `$GEMMA4EC_WORK/seeds_<split>/seed{S}/<method>/`, and the API pool to `$GEMMA4EC_WORK/seeds_<split>/api_pool/` (see `docs/benchmark.md`).

## Metrics and significance

```bash
python results/seeds/compute_seed_metrics.py        # any python with pandas/sklearn/scipy
```

- Per seed: support-weighted sub-subclass (3-level EC) MCC / PPV / Recall. One label space is shared by all methods within the seed. Predictions are matched to test rows by (SMILES, EC), or by position for BEC-Pred and CLAIRE. A test row with no prediction counts as a miss, and `coverage` reports the matched fraction.
- Across seeds: mean, SD and 95% t-interval (`seed_summary.csv`).
- Pairwise: two-sided paired t-test and Wilcoxon signed-rank test over the per-seed values, Holm-corrected within each metric (`pairwise_tests.csv`; `vs_gemma4ec_9b.csv` lists the Gemma4EC-9b comparisons). With 10 seeds, the smallest possible exact Wilcoxon p is 0.002.
