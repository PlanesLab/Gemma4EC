#!/usr/bin/env python3
"""generate_becpred_db.py (fixed)

Author: Josefina Arcagni
Date: 2025-10-14 

Fixes and improvements included:
- Labels now start at 0 (current_label starts at 0) so they are suitable for PyTorch CrossEntropyLoss.
- Global, monotonically-increasing "idx" across all processed rows (no duplicates between files).
- Configurable input/output paths and split ratio via command-line arguments.
- Robust treatment of EC field and rxn_smiles, with an option to remove incomplete ECs.
- Ensures output directory exists before writing.
- Writes label mapping sorted by assigned label for reproducibility.
- Several extra sanity checks and clear error messages.
"""

import argparse
import os
import random
from typing import List, Dict, Tuple, Optional

import pandas as pd

# deterministic randomness
random.seed(41)

label_mapping: Dict[str, int] = {}
current_label = 0  # start at 0 so labels are 0..(num_labels-1)
_global_idx_counter = 1


def split_promiscuous_reactions(row: pd.Series) -> List[pd.Series]:
    """Return a list of rows: one per EC if the row contains '|' in 'ec'."""
    if '|' in str(row['ec']):
        ec_numbers = str(row['ec']).split('|')
        new_rows = []
        for ec in ec_numbers:
            new_row = row.copy()
            new_row['ec'] = ec.strip()
            new_rows.append(new_row)
        return new_rows
    else:
        return [row]


def split_smiles(reaction_smiles: str) -> Tuple[Optional[str], Optional[str]]:
    """Split reaction SMILES into reactants and products. Return (r, p) or (None, None)."""
    if not isinstance(reaction_smiles, str):
        return None, None
    try:
        reactants, products = reaction_smiles.split('>>')
        return reactants.strip(), products.strip()
    except ValueError:
        return None, None


def get_class_label(ec_class_th: str) -> int:
    """Return numeric label for ec_class_th, creating it if necessary."""
    global current_label, label_mapping
    if ec_class_th not in label_mapping:
        label_mapping[ec_class_th] = current_label
        current_label += 1
    return label_mapping[ec_class_th]


def process_file(
    file_path: str,
    split_mode: str,
    remove_incomplete: bool,
    split_ratio_train: float = 0.9,
) -> List[Dict]:
    """Process input CSV/TSV file and return list of processed rows (dicts).

    Parameters
    ----------
    file_path: path to input file (pandas will infer delimiter)
    split_mode: 'random', 'train', 'val' (if 'random' uses split_ratio_train)
    remove_incomplete: if True, skip ECs with missing or non-numeric 3rd part
    split_ratio_train: probability a row is assigned to train when split_mode == 'random'
    """
    global _global_idx_counter

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")

    # Let pandas infer separator; explicitly handle common extensions
    if file_path.endswith('.tsv') or file_path.endswith('.txt'):
        df = pd.read_csv(file_path, sep='\t')
    else:
        df = pd.read_csv(file_path)

    # Guard: ensure columns exist
    if 'ec' not in df.columns:
        raise ValueError("Input file must contain an 'ec' column")
    if 'rxn_smiles' not in df.columns:
        raise ValueError("Input file must contain an 'rxn_smiles' column")

    # Normalize EC column to string and drop empty/nan-like values
    df['ec'] = df['ec'].astype(str).str.strip()
    df = df[(df['ec'] != '') & (df['ec'].str.lower() != 'nan')]

    new_rows: List[Dict] = []

    for _, row in df.iterrows():
        if row['ec'] == '-' or pd.isna(row.get('rxn_smiles', None)):
            continue

        # Expand promiscuous reactions
        for split_row in split_promiscuous_reactions(row):
            ec = str(split_row['ec']).strip()

            parts = ec.split('.')
            # Optionally skip incomplete
            if remove_incomplete:
                if len(parts) < 3 or not parts[2].strip().isdigit():
                    continue

            r, p = split_smiles(split_row['rxn_smiles'])
            if r is None or p is None or r == '' or p == '':
                continue

            # Define the EC class using the first three parts.
            # If parts < 3 and remove_incomplete is False, pad with 'x' to keep string key stable.
            if len(parts) >= 3:
                ec_class_th = '.'.join(parts[:3])
            else:
                # pad to 3 parts to avoid mapping different-length classes unpredictably
                padded = parts + ['x'] * (3 - len(parts))
                ec_class_th = '.'.join(padded[:3])

            class_label = get_class_label(ec_class_th)

            if split_mode == 'random':
                split_label = 'train' if random.random() < split_ratio_train else 'val'
            else:
                split_label = split_mode

            new_rows.append({
                'idx': _global_idx_counter,
                'rxn': split_row['rxn_smiles'],
                'rxn_class': ec,
                'r': r,
                'p': p,
                'rxn_class_th': ec_class_th,
                'class_id': int(class_label),
                'split': split_label,
            })
            _global_idx_counter += 1

    return new_rows


def write_outputs(
    train_rows: List[Dict],
    val_rows: List[Dict],
    output_dir: str,
):
    os.makedirs(output_dir, exist_ok=True)

    df_train = pd.DataFrame(train_rows)
    df_val = pd.DataFrame(val_rows)

    df_train.to_csv(os.path.join(output_dir, 'train_ecreact.csv'), index=False)
    df_val.to_csv(os.path.join(output_dir, 'val_ecreact.csv'), index=False)

    # write label mapping sorted by assigned label for reproducibility
    labels_sorted = sorted(label_mapping.items(), key=lambda kv: kv[1])
    df_labels = pd.DataFrame([{'EC Class': k, 'Assigned Label': v} for k, v in labels_sorted])
    df_labels.to_csv(os.path.join(output_dir, 'ec_class_labels_ecreact.csv'), index=False)


def main():
    parser = argparse.ArgumentParser(description='Generate BEC-Pred Database (fixed).')
    parser.add_argument('--remove_incomplete', action='store_true',
                        help='Remove rows with incomplete EC numbers (missing 3rd part or non-numeric).')
    parser.add_argument('--train_file', default='gemma4ec/data/ECReact_seeds_strat_dedup/seed0/train.csv',
                        help='Input file treated as train (or used with split_mode=train).')
    parser.add_argument('--val_file', default='gemma4ec/data/ECReact_seeds_strat_dedup/seed0/val.csv',
                        help='Input file treated as val (or used with split_mode=val).')
    parser.add_argument('--output_dir', default='./DB/',
                        help='Directory to write CSV outputs.')
    parser.add_argument('--split_ratio_train', type=float, default=0.9,
                        help='If using random split, probability to assign a row to train (default 0.9).')
    parser.add_argument('--force_random_split', action='store_true',
                        help='Ignore file-based split and randomly assign each example to train/val.')

    args = parser.parse_args()

    # Process files. Keep original behaviour: first file marked 'train', second 'val', unless force_random_split
    train_rows = process_file(args.train_file, 'random' if args.force_random_split else 'train', args.remove_incomplete, args.split_ratio_train)
    val_rows = process_file(args.val_file, 'random' if args.force_random_split else 'val', args.remove_incomplete, args.split_ratio_train)

    write_outputs(train_rows, val_rows, args.output_dir)

    print(f"Saved {len(train_rows)} train rows and {len(val_rows)} val rows to {args.output_dir}")
    print(f"Number of distinct EC classes: {len(label_mapping)}")


if __name__ == '__main__':
    main()
