"""
summarize_results.py — Unified evaluation summary across all Gemma4EC runs.

Scans one or more directories for prediction TSV files, groups them by
model/partition/split, computes EC-class metrics, and writes a single
comparison CSV.

Supported TSV formats (auto-detected):
  • Standard  : true_label, pred_fragment or pred, smiles
  • BEC-Pred  : Reaction, Prediction  (needs --true_csv)

Default search paths (all optional, used only if they exist):
  1. <project>/results/
  2. <scratch>/gemma4ec/*/results/          (finetuned partition results)
  3. <scratch>/gemma4ec/zeroshot/results/   (zeroshot run results)

Usage:
    python scripts/summarize_results.py

    # custom paths
    python scripts/summarize_results.py \\
        --search_dirs outputs/Rhea_Scaffold/results \\
                      outputs/zeroshot/results \\
                      results \\
        --true_csv data/ECReact/test.csv \\
        --output_dir results/summary
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
)
from sklearn.preprocessing import LabelEncoder


# ---------------------------------------------------------------------------
# EC helpers
# ---------------------------------------------------------------------------

def extract_ec_class(ec: str) -> str | None:
    """Return the EC class digit (1–7), or None if invalid."""
    s = str(ec).strip().split(".")[0]
    return s if s.isdigit() and s in "1234567" else None


# ---------------------------------------------------------------------------
# TSV loading with auto-detected columns
# ---------------------------------------------------------------------------

def _find_col(df: pd.DataFrame, *candidates: str) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def load_predictions(
    tsv: Path,
    true_df: pd.DataFrame | None,
) -> tuple[pd.DataFrame | None, str]:
    """
    Load a prediction file and return (df_with_true_pred, status_msg).

    The returned DataFrame has exactly two columns: true_label, pred.
    Returns (None, reason) when the file cannot be evaluated.
    """
    sep = "\t" if tsv.suffix == ".tsv" else ","
    try:
        df = pd.read_csv(tsv, sep=sep, low_memory=False)
    except Exception as e:
        return None, f"read error: {e}"

    pred_col = _find_col(df, "pred_fragment", "pred", "Prediction")
    true_col = _find_col(df, "true_label", "ec")

    if pred_col is None:
        return None, "no prediction column found"

    # Fast path: true_label already embedded
    if true_col is not None:
        result = df[[true_col, pred_col]].rename(
            columns={true_col: "true_label", pred_col: "pred"}
        )
        result = result.dropna(subset=["true_label", "pred"])
        # Drop rows that are clearly not EC (status == "invalid" if present)
        if "status" in df.columns:
            result = result[df.loc[result.index, "status"] != "invalid"]
        return result.reset_index(drop=True), "ok"

    # Need external ground truth (BEC-Pred style)
    if true_df is None:
        return None, "no true_label column and --true_csv not provided"

    smiles_col = _find_col(df, "smiles", "rxn_smiles", "Reaction")
    true_smiles = _find_col(true_df, "rxn_smiles", "smiles", "Reaction")
    true_ec = _find_col(true_df, "ec", "true_label")

    if smiles_col is None:
        return None, "no smiles column for merge"
    if true_smiles is None or true_ec is None:
        return None, f"true_csv missing columns (found: {list(true_df.columns)})"

    merged = pd.merge(
        df[[smiles_col, pred_col]],
        true_df[[true_smiles, true_ec]],
        left_on=smiles_col,
        right_on=true_smiles,
        how="inner",
    ).rename(columns={true_ec: "true_label", pred_col: "pred"})

    return merged[["true_label", "pred"]].dropna().reset_index(drop=True), "merged"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(
    true: list[str], pred: list[str]
) -> dict:
    """Compute global classification metrics."""
    if not true:
        return {"accuracy": 0.0, "f1_macro": 0.0, "f1_weighted": 0.0, "mcc": 0.0,
                "ppv": 0.0, "recall": 0.0}
    return {
        "accuracy":    accuracy_score(true, pred),
        "f1_macro":    f1_score(true, pred, average="macro",    zero_division=0),
        "f1_weighted": f1_score(true, pred, average="weighted", zero_division=0),
        "mcc":         matthews_corrcoef(true, pred),
        "ppv":         precision_score(true, pred, average="weighted", zero_division=0),
        "recall":      recall_score(true, pred, average="weighted", zero_division=0),
    }


def compute_per_class_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-EC-class metrics from a df with true_label and pred columns."""
    df = df.copy()
    df["true_class"] = df["true_label"].apply(extract_ec_class)
    df["pred_class"] = df["pred"].apply(extract_ec_class)
    df = df[df["true_class"].notna() & df["pred_class"].notna()]

    if df.empty:
        return pd.DataFrame(columns=["EC_class", "MCC", "PPV", "Recall", "F1", "Samples"])

    all_classes = pd.concat([df["true_class"], df["pred_class"]]).unique()
    le = LabelEncoder().fit(all_classes)
    y_true = le.transform(df["true_class"])
    y_pred = le.transform(df["pred_class"])

    rows = []
    for cls_idx, cls_label in zip(np.unique(y_true), le.inverse_transform(np.unique(y_true))):
        yt = (y_true == cls_idx).astype(int)
        yp = (y_pred == cls_idx).astype(int)
        rows.append({
            "EC_class": cls_label,
            "MCC":    matthews_corrcoef(yt, yp),
            "PPV":    precision_score(yt, yp, zero_division=0),
            "Recall": recall_score(yt, yp, zero_division=0),
            "F1":     f1_score(yt, yp, zero_division=0),
            "Samples": int(yt.sum()),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_files(search_dirs: list[Path]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for d in search_dirs:
        if not d.is_dir():
            continue
        for ext in ("*.tsv", "*.csv"):
            for f in sorted(d.rglob(ext)):
                # Skip our own output files
                if f.name.startswith("summary_") or f.name.startswith("comparison_"):
                    continue
                if f not in seen:
                    seen.add(f)
                    files.append(f)
    return files


def _label_for_file(tsv: Path) -> str:
    """
    Produce a short, human-readable model label from the TSV path.

    Examples:
      .../results/APIs/chatgpt-5_1/test_predictions_...tsv  → "APIs/chatgpt-5_1"
      .../results/Gemma4EC-2b/predictions_test...tsv        → "Gemma4EC-2b"
      .../gemma4ec/Rhea_Scaffold/results/predictions_...tsv → "Rhea_Scaffold"
      .../gemma4ec/zeroshot/results/zeroshot_test_...tsv    → "zeroshot"
    """
    parent      = tsv.parent       # immediate containing folder
    grandparent = parent.parent    # one level up

    # If the file lives directly in a 'results' folder, go up one more level
    # to get the meaningful group name (e.g. Rhea_Scaffold, zeroshot)
    if parent.name == "results":
        return grandparent.name

    # If the grandparent is a known group prefix (APIs), include it
    if grandparent.name == "APIs":
        return f"APIs/{parent.name}"

    return parent.name


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_search_dirs() -> list[Path]:
    """Build default list of directories to scan."""
    project = Path(__file__).parent.parent
    scratch = Path(f"/scratch/{os.environ.get('USER', os.environ.get('LOGNAME', 'user'))}")
    dirs = [
        project / "results",
        scratch / "gemma4ec" / "zeroshot" / "results",
    ]
    # Partition result dirs: /scratch/$USER/gemma4ec/Rhea_*/results/
    partition_root = scratch / "gemma4ec"
    if partition_root.is_dir():
        for sub in sorted(partition_root.iterdir()):
            candidate = sub / "results"
            if candidate.is_dir():
                dirs.append(candidate)
    return dirs


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Summarize EC prediction metrics across all models and partitions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument(
        "--search_dirs", type=Path, nargs="+", default=None,
        help="Directories to scan for prediction TSVs. Defaults to results/ and "
             "$SCRATCH/gemma4ec/*/results/.",
    )
    ap.add_argument(
        "--true_csv", type=Path, default=None,
        help="Ground-truth CSV (rxn_smiles, ec). Required for files without embedded true_label.",
    )
    ap.add_argument(
        "--output_dir", type=Path,
        default=Path(__file__).parent.parent / "results" / "summary",
        help="Directory to write output CSVs.",
    )
    ap.add_argument(
        "--split", type=str, default=None,
        help="Only include TSVs whose filename contains this string (e.g. 'test').",
    )
    ap.add_argument(
        "--min_samples", type=int, default=10,
        help="Skip files with fewer than this many evaluable rows.",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()

    search_dirs = args.search_dirs or _default_search_dirs()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Load optional ground-truth CSV
    true_df: pd.DataFrame | None = None
    if args.true_csv is not None:
        if not args.true_csv.exists():
            sys.exit(f"[ERROR] --true_csv not found: {args.true_csv}")
        true_df = pd.read_csv(args.true_csv)
        print(f"[info] Ground-truth loaded: {len(true_df)} rows from {args.true_csv}")

    # Discover files
    all_files = discover_files(search_dirs)
    if args.split:
        all_files = [f for f in all_files if args.split in f.name]
    print(f"[info] Scanning {len(search_dirs)} dir(s), found {len(all_files)} candidate file(s).\n")

    # Evaluate each file
    rows: list[dict] = []
    per_class_tables: dict[str, pd.DataFrame] = {}

    for tsv in all_files:
        label = _label_for_file(tsv)
        merged, status = load_predictions(tsv, true_df)

        if merged is None:
            print(f"  [skip] {label}  ({status})")
            continue
        if len(merged) < args.min_samples:
            print(f"  [skip] {label}  (only {len(merged)} evaluable rows)")
            continue

        m = compute_metrics(merged["true_label"].tolist(), merged["pred"].tolist())
        per_class = compute_per_class_metrics(merged)

        rows.append({"model": label, "n": len(merged), **m})
        per_class_tables[label] = per_class

        print(
            f"  [ok]   {label:<50}  n={len(merged):>6}  "
            f"MCC={m['mcc']:>7.4f}  Acc={m['accuracy']:>7.4f}  F1w={m['f1_weighted']:>7.4f}"
        )

    if not rows:
        sys.exit("[ERROR] No files could be evaluated.")

    # ---- Summary table ----
    summary_df = pd.DataFrame(rows).sort_values(["model"])
    summary_df = summary_df[["model", "n", "mcc", "accuracy", "f1_macro", "f1_weighted", "ppv", "recall"]]

    out_summary = args.output_dir / "summary_all_models.csv"
    summary_df.to_csv(out_summary, index=False, float_format="%.4f")

    print(f"\n{'='*80}")
    print(f"  RESULTS SUMMARY  ({len(rows)} model/split combinations)")
    print(f"{'='*80}")
    print(summary_df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    # ---- Per-class comparison table ----
    combined: pd.DataFrame | None = None
    for name, per_class in per_class_tables.items():
        df = per_class.rename(columns={
            "MCC":    f"{name}_MCC",
            "PPV":    f"{name}_PPV",
            "Recall": f"{name}_Recall",
            "F1":     f"{name}_F1",
            "Samples": f"{name}_Samples",
        })
        combined = df if combined is None else pd.merge(combined, df, on="EC_class", how="outer")

    if combined is not None:
        combined = combined.fillna(0.0).sort_values("EC_class").reset_index(drop=True)
        out_per_class = args.output_dir / "summary_per_class.csv"
        combined.to_csv(out_per_class, index=False, float_format="%.4f")
        print(f"\n[saved] {out_per_class}")

    print(f"[saved] {out_summary}")


if __name__ == "__main__":
    main()
