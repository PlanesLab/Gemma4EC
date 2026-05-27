"""
get_metrics.py — DEPRECATED.

This script was a legacy one-off analysis tool with hardcoded paths.
It has been superseded by the main benchmark computation scripts:

    cd results/
    python compute_weighted_metrics.py         # main benchmark table
    python compute_per_class_and_splits.py     # per-class and partition tables

These scripts use a shared label space and support-weighted MCC at the
sub-subclass level (3-digit EC, e.g. 1.1.1), which is the methodology
reported in the Gemma4EC paper.
"""

raise RuntimeError(
    "This script is deprecated. "
    "Use results/compute_weighted_metrics.py instead."
)
