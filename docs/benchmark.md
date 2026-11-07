# Benchmark

## ECReact, 10 seeds

10 re-splits of ECReact: canonical-SMILES deduplicated, reaction-grouped, 80/10/10 stratified by EC sub-subclass.
The splits ship as one table, `data/ECReact_strat_dedup_splits.csv.gz`; rebuild the per-seed CSVs with:

```bash
python scripts/make_seed_splits.py      # -> data/ECReact_seeds_strat_dedup/seed{0..9}/
```

## Rhea500

10 bootstrap samples of 500 Rhea reactions (EC7 dropped); no method is retrained.

```bash
python scripts/make_rhea500_inputs.py   # -> data/ECReact_seeds_rhea500/seed{0..9}/
```

## Metrics and figures

Support-weighted MCC, precision and recall at EC sub-subclass level. The p-value triangle uses the paired Wilcoxon
signed-rank test with Benjamini–Hochberg correction.

```bash
python results/seeds/compute_seed_metrics.py   # -> results/seeds_strat_dedup/
python results/seeds/rhea500_benchmark.py      # -> results/seeds_rhea500/
Rscript figures/seed_figures.R                 # -> figures/seeds/strat_dedup/
Rscript figures/rhea500_figure.R               # -> figures/seeds/rhea500/
```
