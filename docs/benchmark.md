# Reproducing the benchmark

The paper compares methods over 10 re-splits of ECReact (`SPLIT_SET=strat_dedup`): canonical-SMILES deduplicated,
reaction-grouped, 80/10/10 stratified by EC sub-subclass. The resulting metric tables are in
`results/seeds_strat_dedup/`; the steps below regenerate them.

Set paths in `config.sh` first (`cp config.sh.example config.sh`). Outputs go to `$GEMMA4EC_WORK/seeds_strat_dedup/`.

## 1. Splits

The splits ship as one assignment table, `data/ECReact_strat_dedup_splits.csv.gz` (one row per reaction–EC pair,
one column per seed). Rebuild the per-seed CSVs with:

```bash
python scripts/make_seed_splits.py          # → data/ECReact_seeds_strat_dedup/seed{0..9}/
```

To rebuild the table itself from the raw ECReact CSVs (needs RDKit), pass
`--from_ecreact <dir with train/val/test.csv>`. The splits are deterministic (seeds 0–9).

## 2. Trained methods (one SLURM array task per seed)

```bash
DRY_RUN=1 bash slurm/seeds/submit_seeds.sh                          # preview
METHODS="gemma4ec_9b gemma4ec_2b txgemma_noft theia becpred claire" bash slurm/seeds/submit_seeds.sh
```

| Method | Script | Needs |
|---|---|---|
| Gemma4EC-9B / 2B | `run_seed_gemma4ec.sh` (`MODEL_SIZE=9b\|2b`) | gemma4ec env, 4 GPUs |
| TxGemma-9B, not fine-tuned | `run_seed_txgemma_noft.sh` | gemma4ec env |
| Theia | `run_seed_theia.sh` | gemma4ec env |
| BEC-Pred | `run_seed_becpred.sh` | `$ENVS/becpred_gpu` (see `benchmarking/bec-pred/README.md`) |
| CLAIRE | `run_seed_claire.sh` | `$CLAIRE_ROOT`, `$ENVS/claire`, `$ENVS/rxnfp-env` |

## 3. Similarity tools (SIMMER, SelenzymeRF)

These do not train; the 10 test sets are pooled so each reaction is queried once.

```bash
sbatch slurm/seeds/run_tool_simmer.sh        # published reference database
sbatch slurm/seeds/run_tool_selenzyme.sh
python scripts/collect_tool_pool.py          # → seed*/tools/
```

Variants with the training split as reference database: `run_seed_simmer_traindb.sh` (`NULL_MODE=per_class` for the
per-class null) and `scripts/selenzyme_traindb.py` + `run_selenzyme_build_shard.sh` + `run_selenzyme_traindb_dbs.sh` +
`run_seed_selenzyme_traindb.sh`, then `scripts/collect_selenzyme_traindb.py`. Both need `$ECN_ROOT`.

## 4. General-purpose LLMs (Gemini, GPT)

Zero-shot answers do not depend on the seed, so each unique test reaction is queried once and the answers are copied
to every seed. Keys go in `~/.gemma4ec_api_keys` (`chmod 600`; never commit them).

```bash
python scripts/make_api_pool.py --prefill
python scripts/gemini_batch_pool.py submit --model gemini-3.1-flash-lite   # Batch API, spend cap
python scripts/gemini_batch_pool.py collect --model gemini-3.1-flash-lite
python scripts/openai_batch_pool.py submit --model gpt-4.1-mini            # same for OpenAI
python scripts/fanout_api_predictions.py
```

## 5. Metrics, tests and figures

```bash
python results/seeds/compute_seed_metrics.py   # → results/seeds_strat_dedup/
Rscript figures/seed_figures.R                                       # → figures/seeds/strat_dedup/
```

Per seed: support-weighted MCC, precision and recall at the EC sub-subclass level. Across seeds: mean, SD and 95%
interval (`seed_summary.csv`). Significance: `significance_tests.csv` holds paired Wilcoxon signed-rank, paired t-test and rank-sum p-values with
Benjamini–Hochberg correction for every method pair; the figure's p-value triangle uses the paired signed-rank test.
`pairwise_tests.csv` and `vs_gemma4ec_9b.csv` give the Holm-corrected comparisons against Gemma4EC-9B. Per-class and per-level tables:
`per_class_metrics.csv`, `level_metrics.csv`.
