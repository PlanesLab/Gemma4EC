"""
prepare_db.py  — Convert a raw database TSV partition to the
rxn_smiles/ec CSV format expected by Gemma4EC, then produce
stratified train / val / test splits.

Primary databases (Case1-Rhea partitions) — provide --db_root pointing to:
  Rhea_Scaffold    <db_root>/Scaffold/
  Rhea_Stratified  <db_root>/Stratified/
  Rhea_Time        <db_root>/Time/

Additional databases (DatabasesEC):
  ECREACT   columns: rxn_smiles, ec
  KEGG      columns: Isomeric_SMILES (as rxn_smiles), ec
  Rhea_raw  columns: REACTION_SMILES (as rxn_smiles), ec
  MetaNetX  columns: rxn (as rxn_smiles), ec

EC numbers are normalised to the x.xx.xx format used by the model
(first 3 numeric parts, 2nd and 3rd zero-padded to 2 digits).
Rows with fewer than 3 numeric EC parts are dropped.

The databases already provide train.tsv + test.tsv splits.
A validation split is carved out of train with stratified sampling.

Usage — prepare the three Rhea partitions:

  DB_ROOT=/path/to/Case1-Rhea/Database
  OUT_ROOT=data/partitions

  for DB in Rhea_Scaffold Rhea_Stratified Rhea_Time; do
      python scripts/prepare_db.py \\
          --db $DB \\
          --db_root $DB_ROOT \\
          --out_root $OUT_ROOT
  done
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.datamod.split_ec_strat import build_strat_key as _build_strat_key


# ---------------------------------------------------------------------------
# Database registry
# ---------------------------------------------------------------------------
# Each entry: (sub_dir_relative_to_db_root, smiles_col, ec_col, sep)
# sub_dir="" means db_root IS the database directory (not used here)
DB_REGISTRY: dict[str, tuple[str, str, str, str]] = {
    # Case1-Rhea partitions  (primary)
    "Rhea_Scaffold":    ("Scaffold",    "REACTION_SMILES", "EC_NUMBER", "\t"),
    "Rhea_Stratified":  ("Stratified",  "REACTION_SMILES", "EC_NUMBER", "\t"),
    "Rhea_Time":        ("Time",        "REACTION_SMILES", "EC_NUMBER", "\t"),
    # DatabasesEC
    "ECREACT":          ("ECREACT",     "rxn_smiles",      "ec",        "\t"),
    "KEGG":             ("KEGG",        "Isomeric_SMILES", "ec",        "\t"),
    "Rhea_raw":         ("Rhea",        "REACTION_SMILES", "ec",        "\t"),
    "MetaNetX":         ("MetaNetX",    "rxn",             "ec",        "\t"),
}


# ---------------------------------------------------------------------------
# EC number helpers
# ---------------------------------------------------------------------------
_NUMERIC_RE = re.compile(r"^\d+$")


def normalise_ec(raw_ec: str) -> str | None:
    """
    Return the first-3-part, zero-padded EC string (e.g. '2.07.08'),
    or None if the EC has fewer than 3 numeric parts.
    """
    if pd.isna(raw_ec):
        return None
    parts = str(raw_ec).strip().split(".")
    # take only the first 3
    parts = parts[:3]
    if len(parts) < 3:
        return None
    # all 3 must be pure numeric digits
    if not all(_NUMERIC_RE.match(p) for p in parts):
        return None
    class_  = parts[0]
    sub     = parts[1].zfill(2)
    subsub  = parts[2].zfill(2)
    return f"{class_}.{sub}.{subsub}"


# ---------------------------------------------------------------------------
# Stratified split (val from train — test comes from the DB directly)
# ---------------------------------------------------------------------------
def stratified_val_split(
    train_df: pd.DataFrame,
    val_frac: float,
    strat_level: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split train_df into (new_train, val) with EC-stratified sampling.
    """
    rng = np.random.default_rng(seed)
    key_col = "_strat_key"
    train_df[key_col] = train_df["ec"].apply(lambda s: _build_strat_key(s, strat_level))

    train_idx, val_idx = [], []

    for _, idx_arr in train_df.groupby(key_col).indices.items():
        idx = np.array(list(idx_arr))
        rng.shuffle(idx)
        n = len(idx)

        if n <= 1:
            train_idx.extend(idx.tolist())
            continue

        n_val = max(1, int(np.floor(val_frac * n)))
        n_val = min(n_val, n - 1)   # keep at least 1 in train

        val_idx.extend(idx[:n_val].tolist())
        train_idx.extend(idx[n_val:].tolist())

    new_train = train_df.loc[train_idx].drop(columns=[key_col]).reset_index(drop=True)
    val = train_df.loc[val_idx].drop(columns=[key_col]).reset_index(drop=True)
    train_df.drop(columns=[key_col], inplace=True)
    return new_train, val


# ---------------------------------------------------------------------------
# Load & normalise a single TSV
# ---------------------------------------------------------------------------
def load_and_normalise(
    tsv_path: Path,
    smiles_col: str,
    ec_col: str,
    sep: str = "\t",
) -> pd.DataFrame:
    df = pd.read_csv(tsv_path, sep=sep, low_memory=False)

    missing = {smiles_col, ec_col} - set(df.columns)
    if missing:
        sys.exit(
            f"[ERROR] {tsv_path.name} is missing columns: {missing}\n"
            f"  Available: {list(df.columns)}"
        )

    out = pd.DataFrame(
        {
            "rxn_smiles": df[smiles_col].astype(str).str.strip(),
            "ec":         df[ec_col].astype(str).str.strip(),
        }
    )

    # drop empty SMILES
    out = out[
        out["rxn_smiles"].notna()
        & (out["rxn_smiles"] != "")
        & (out["rxn_smiles"] != "nan")
    ]

    # normalise EC → x.xx.xx
    before = len(out)
    out["ec"] = out["ec"].apply(normalise_ec)
    out = out.dropna(subset=["ec"]).reset_index(drop=True)
    dropped = before - len(out)
    if dropped:
        print(f"  [warn] Dropped {dropped} rows with invalid/partial EC numbers.")

    # drop exact duplicates
    before_dedup = len(out)
    out = out.drop_duplicates(subset=["rxn_smiles", "ec"]).reset_index(drop=True)
    dupes = before_dedup - len(out)
    if dupes:
        print(f"  [warn] Dropped {dupes} duplicate (rxn_smiles, ec) pairs.")

    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Prepare DB partition CSVs for Gemma4EC finetuning."
    )
    ap.add_argument(
        "--db", required=True, choices=list(DB_REGISTRY.keys()),
        help="Database/partition name. "
             "Rhea partitions: Rhea_Scaffold | Rhea_Stratified | Rhea_Time  "
             "DatabasesEC: ECREACT | KEGG | Rhea_raw | MetaNetX",
    )
    ap.add_argument(
        "--db_root", required=True,
        help="Root directory containing the raw database splits. "
             "For Rhea partitions: directory with Scaffold/, Stratified/, Time/ sub-folders. "
             "For DatabasesEC: directory with ECREACT/, KEGG/, etc. sub-folders.",
    )
    ap.add_argument(
        "--out_root", required=True,
        help="Output root. CSVs are written to <out_root>/<db>/{train,val,test}.csv",
    )
    ap.add_argument(
        "--val_frac", type=float, default=0.10,
        help="Fraction of training rows to hold out for validation. (default: 0.10)",
    )
    ap.add_argument(
        "--strat_level", type=int, default=2, choices=[1, 2, 3],
        help="EC stratification level for val split: 1=class, 2=class.sub, 3=full. (default: 2)",
    )
    ap.add_argument(
        "--seed", type=int, default=42,
        help="Random seed. (default: 42)",
    )
    args = ap.parse_args()

    sub_dir, smiles_col, ec_col, sep = DB_REGISTRY[args.db]
    db_dir   = Path(args.db_root) / sub_dir
    out_dir  = Path(args.out_root) / args.db
    out_dir.mkdir(parents=True, exist_ok=True)

    train_tsv = db_dir / "train.tsv"
    test_tsv  = db_dir / "test.tsv"

    for p in (train_tsv, test_tsv):
        if not p.exists():
            sys.exit(f"[ERROR] File not found: {p}")

    # ---- load & normalise ----
    print(f"\n[{args.db}] Loading train.tsv …")
    all_train = load_and_normalise(train_tsv, smiles_col, ec_col, sep)
    print(f"  {len(all_train)} valid rows.")

    print(f"[{args.db}] Loading test.tsv …")
    test_df = load_and_normalise(test_tsv, smiles_col, ec_col, sep)
    print(f"  {len(test_df)} valid rows.")

    # ---- carve out val from train ----
    print(f"[{args.db}] Creating val split (val_frac={args.val_frac}, strat_level={args.strat_level}) …")
    train_df, val_df = stratified_val_split(
        all_train, args.val_frac, args.strat_level, args.seed
    )
    print(f"  train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")

    # ---- save ----
    for name, df in [("train.csv", train_df), ("val.csv", val_df), ("test.csv", test_df)]:
        path = out_dir / name
        df.to_csv(path, index=False)
        print(f"  Saved → {path}")

    print(f"[{args.db}] Done.\n")


if __name__ == "__main__":
    main()
