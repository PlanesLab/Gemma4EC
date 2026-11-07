# results/

Tables behind the figures. Metric: support-weighted MCC / precision / recall over EC sub-subclass labels.

| Folder | Files | Figure |
|---|---|---|
| `seeds_strat_dedup/` | `seed_metrics.csv`, `seed_summary.csv`, `per_class_metrics.csv`, `level_metrics.csv`, `significance_tests.csv` | `figures/seeds/strat_dedup/` |
| `seeds_rhea500/` | `benchmark_seed_metrics.csv`, `benchmark_per_class_metrics.csv`, `benchmark_level_metrics.csv` | `figures/seeds/rhea500/` |
| `chat_eval/` | `accuracy_overall.csv`, `explanation_audit.csv` | `figures/chat/fig_chat_validation.png` |

Scorers: `seeds/compute_seed_metrics.py`, `seeds/rhea500_benchmark.py`, `../chat/evaluate_chat.py`.
