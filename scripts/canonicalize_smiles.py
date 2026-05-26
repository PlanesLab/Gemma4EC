#!/usr/bin/env python3
"""Canonicalize rxn_smiles in all partition, raw, and bec-pred CSV files in-place."""

from pathlib import Path
import pandas as pd
from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")

PROJECT = Path(__file__).resolve().parent.parent


def canon_mol(smi: str) -> str:
    try:
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            return Chem.MolToSmiles(mol)
    except Exception:
        pass
    return smi


def canon_rxn(rxn_smi: str) -> str:
    if not isinstance(rxn_smi, str) or not rxn_smi.strip():
        return rxn_smi
    parts = rxn_smi.split(">")
    if len(parts) != 3:
        return rxn_smi
    return ">".join(
        ".".join(canon_mol(m) for m in part.split(".")) if part else ""
        for part in parts
    )


def process(path: Path, col: str) -> None:
    df = pd.read_csv(path)
    if col not in df.columns:
        print(f"  SKIP {path.name}: no '{col}' column")
        return
    before = df[col].tolist()
    df[col] = df[col].apply(canon_rxn)
    changed = sum(a != b for a, b in zip(before, df[col].tolist()))
    df.to_csv(path, index=False)
    print(f"  {path.relative_to(PROJECT)}  →  {changed}/{len(df)} updated")


# ── partition + raw CSVs (rxn_smiles column) ─────────────────────────────────
for csv in sorted(PROJECT.glob("data/**/*.csv")):
    process(csv, "rxn_smiles")

# ── bec-pred DB ──────────────────────────────────────────────────────────────
bec_db = PROJECT / "src/bec-pred/DB"

process(bec_db / "test.csv", "rxn_smiles")

for f in ("train_ecreact.csv", "val_ecreact.csv"):
    path = bec_db / f
    df = pd.read_csv(path)
    for col in ("rxn", "r", "p"):
        if col in df.columns:
            before = df[col].tolist()
            df[col] = df[col].apply(canon_rxn)
            changed = sum(a != b for a, b in zip(before, df[col].tolist()))
            print(f"  src/bec-pred/DB/{f}[{col}]  →  {changed}/{len(df)} updated")
    df.to_csv(path, index=False)

print("\nDone.")
