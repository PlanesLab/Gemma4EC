# gemma4ec/src/split_ec_strat.py

"""
Hierarchical stratified split for EC numbers.

- Stratification by EC prefix at the desired level:
  level=1 -> "clase"        (e.g., "2")
  level=2 -> "clase.subclase" (e.g., "2.7")
  level=3 -> "clase.subclase.subsubclase" (e.g., "2.7.8")

Default splits: train=0.8, val=0.1, test=0.1.
Constraints per strat group:
- n==1:     all to train
- n==2:     1 to val, 1 to train (0 to test)
- n>=3:     at least 1 sample in each of train/val/test

Usage:
  python split_ec_strat.py --input raw.csv --output-dir ./out --strat-level 2 \
                           --val-frac 0.1 --test-frac 0.1 --seed 42 --save-summary
"""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

REQUIRED_COLS = {"ec"}

def build_strat_key(ec: str, level: int) -> str:
    if pd.isna(ec):
        return "NA"
    parts = str(ec).split(".")
    return ".".join(parts[:max(1, min(level, len(parts)))])

def split_by_group(df: pd.DataFrame, key_col: str, val_frac: float, test_frac: float, seed: int):
    rng = np.random.default_rng(seed)
    train_idx, val_idx, test_idx = [], [], []

    for key, idx in df.groupby(key_col).indices.items():
        idx = np.array(list(idx))
        rng.shuffle(idx)
        n = len(idx)

        if n == 1:
            # all to train
            train_idx.extend(idx.tolist())
            continue
        if n == 2:
            # one to val, one to train
            val_idx.append(idx[0])
            train_idx.append(idx[1])
            continue

        # n >= 3
        n_val  = int(np.floor(val_frac * n))
        n_test = int(np.floor(test_frac * n))

        # ensure at least 1 in val and test
        n_val  = max(1, n_val)
        n_test = max(1, n_test)

        # ensure at least 1 remains for train
        # reduce the larger of (n_val, n_test) if necessary
        while n_val + n_test >= n:
            if n_val >= n_test and n_val > 1:
                n_val -= 1
            elif n_test > 1:
                n_test -= 1
            else:
                # final fallback: leave at least one for train
                n_test -= 1
                break

        test_idx.extend(idx[:n_test].tolist())
        val_idx.extend(idx[n_test:n_test+n_val].tolist())
        train_idx.extend(idx[n_test+n_val:].tolist())

    train_df = df.loc[train_idx].sample(frac=1.0, random_state=seed).reset_index(drop=True)
    val_df   = df.loc[val_idx].sample(frac=1.0, random_state=seed).reset_index(drop=True)
    test_df  = df.loc[test_idx].sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return train_df, val_df, test_df

def make_summary(full_df: pd.DataFrame, train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame, key_col: str):
    overall = full_df[key_col].value_counts().rename("all_count")
    t_counts = train_df[key_col].value_counts().rename("train_count")
    v_counts = val_df[key_col].value_counts().rename("val_count")
    te_counts = test_df[key_col].value_counts().rename("test_count")
    summary = pd.concat([overall, t_counts, v_counts, te_counts], axis=1).fillna(0).astype(int)
    summary["train_prop"] = (summary["train_count"] / summary["all_count"]).round(3)
    summary["val_prop"]   = (summary["val_count"] / summary["all_count"]).round(3)
    summary["test_prop"]  = (summary["test_count"] / summary["all_count"]).round(3)
    summary = summary.sort_values("all_count", ascending=False).reset_index().rename(columns={"index": key_col})
    return summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Ruta al CSV de entrada con columnas rxn_smiles,ec")
    ap.add_argument("--output-dir", required=True, help="Directorio de salida para train/val/test CSV")
    ap.add_argument("--strat-level", type=int, default=2, choices=[1,2,3], help="Nivel de estratificación EC (1,2,3)")
    ap.add_argument("--val-frac", type=float, default=0.10, help="Proporción para validación")
    ap.add_argument("--test-frac", type=float, default=0.10, help="Proporción para test")
    ap.add_argument("--seed", type=int, default=42, help="Semilla aleatoria")
    ap.add_argument("--save-summary", action="store_true", help="Guardar resumen por grupo de estratificación")
    args = ap.parse_args()

    in_path = Path(args.input)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(in_path)

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise SystemExit(f"Faltan columnas requeridas: {missing}")

    # Build strat key
    key_col = "ec_strat"
    df[key_col] = df["ec"].astype(str).apply(lambda s: build_strat_key(s, args.strat_level))

    # Validate fractions
    if args.val_frac < 0 or args.test_frac < 0 or args.val_frac + args.test_frac >= 1.0:
        raise SystemExit("val_frac y test_frac deben ser >=0 y su suma < 1.0")

    train_df, val_df, test_df = split_by_group(df, key_col, args.val_frac, args.test_frac, args.seed)

    # Drop helper column before saving
    for name, part in [("train.csv", train_df), ("val.csv", val_df), ("test.csv", test_df)]:
        part.drop(columns=[key_col]).to_csv(out_dir / name, index=False)

    if args.save_summary:
        summary = make_summary(df, train_df, val_df, test_df, key_col)
        summary.to_csv(out_dir / f"summary_by_{key_col}.csv", index=False)

    print(f"[OK] Guardado en: {out_dir}")

if __name__ == "__main__":
    main()
