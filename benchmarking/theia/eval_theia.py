"""
eval_theia.py — Evaluate the pre-trained Theia MLP baseline on a CSV split.

Reads a CSV with `rxn_smiles` and `ec` columns, encodes DRFP fingerprints,
runs the Theia MLPClassifier, and writes a TSV of predictions.

Usage:
    python eval_theia.py \
        --input_csv    data/ECReact_seeds_strat_dedup/seed0/test.csv \
        --output_tsv   outputs/theia/theia_test.tsv \
        --model_pt     outputs/theia_raw/model.pt \
        --labelenc_pkl outputs/theia_raw/label_encoder.pkl

    # all three splits:
    for SPLIT in train val test; do
        python eval_theia.py \
            --input_csv    data/ECReact_seeds_strat_dedup/seed0/${SPLIT}.csv \
            --output_tsv   outputs/theia/theia_${SPLIT}.tsv \
            --model_pt     outputs/theia_raw/model.pt \
            --labelenc_pkl outputs/theia_raw/label_encoder.pkl
    done

Note: train_theia.py saves model.pt and label_encoder.pkl to --output_dir.
"""

from __future__ import annotations

import argparse
import pickle
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from drfp import DrfpEncoder
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.metrics import accuracy_score, f1_score, matthews_corrcoef
from theia.ml import MLPClassifier

# Suppress sklearn version mismatch warnings (model trained with 1.1.1, may run on newer)
warnings.filterwarnings("ignore", category=InconsistentVersionWarning)


def _compute_metrics(true_labels, pred_labels):
    return {
        "accuracy":    accuracy_score(true_labels, pred_labels),
        "f1_macro":    f1_score(true_labels, pred_labels, average="macro", zero_division=0),
        "f1_weighted": f1_score(true_labels, pred_labels, average="weighted", zero_division=0),
        "mcc":         matthews_corrcoef(true_labels, pred_labels),
    }

_FPS_LENGTH = 10240
_HIDDEN_DIM = 1664
_BATCH_SIZE = 256


def encode_drfp(smiles_list: list[str], batch_size: int = 256) -> np.ndarray:
    encoder = DrfpEncoder()
    all_fps = []
    n_failed = 0
    for start in range(0, len(smiles_list), batch_size):
        batch = smiles_list[start : start + batch_size]
        try:
            fps = encoder.encode(
                batch,
                root_central_atom=False,
                radius=2,
                include_hydrogens=True,
                n_folded_length=_FPS_LENGTH,
                show_progress_bar=False,
            )
            all_fps.append(np.vstack([np.array(fp, dtype=np.int8) for fp in fps]))
        except Exception as e:
            print(f"  [warn] DRFP encoding failed for batch {start}: {e}")
            all_fps.append(np.zeros((len(batch), _FPS_LENGTH), dtype=np.int8))
            n_failed += len(batch)
    if n_failed:
        print(f"  [warn] {n_failed}/{len(smiles_list)} SMILES failed encoding → zero-vector fallback")
    return np.vstack(all_fps)


def load_model(model_pt: Path, label_encoder) -> MLPClassifier:
    output_dim = len(label_encoder.classes_)
    model = MLPClassifier(_FPS_LENGTH, _HIDDEN_DIM, output_dim)
    checkpoint = torch.load(str(model_pt), map_location="cpu")
    model.load_state_dict(checkpoint)
    model.eval()
    return model


def predict(model: MLPClassifier, X: np.ndarray, batch_size: int = 256) -> tuple[np.ndarray, np.ndarray]:
    """Returns (pred_indices, confidences)."""
    all_indices = []
    all_conf = []
    X_f32 = X.astype(np.float32)
    with torch.no_grad():
        for start in range(0, len(X_f32), batch_size):
            batch = torch.from_numpy(X_f32[start : start + batch_size])
            logits = model(batch)
            probs = torch.softmax(logits, dim=1).cpu().numpy()
            all_indices.append(probs.argmax(axis=1))
            all_conf.append(probs.max(axis=1))
    return np.concatenate(all_indices), np.concatenate(all_conf)


def main():
    args = parse_args()

    input_csv = Path(args.input_csv)
    output_tsv = Path(args.output_tsv)

    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    model_pt     = Path(args.model_pt)
    labelenc_pkl = Path(args.labelenc_pkl)

    # ── load data ────────────────────────────────────────────────────────────
    print(f"[theia] Reading {input_csv} ...")
    df = pd.read_csv(input_csv)
    if "rxn_smiles" not in df.columns:
        raise KeyError(f"Input CSV must have a 'rxn_smiles' column. Found: {list(df.columns)}")
    smiles_list  = df["rxn_smiles"].astype(str).str.strip().tolist()
    true_labels  = df["ec"].astype(str).tolist() if "ec" in df.columns else [""] * len(df)
    print(f"[theia] {len(smiles_list)} reactions loaded.")

    # ── label encoder ────────────────────────────────────────────────────────
    print(f"[theia] Loading label encoder from {labelenc_pkl} ...")
    with open(labelenc_pkl, "rb") as f:
        label_encoder = pickle.load(f)
    print(f"[theia] {len(label_encoder.classes_)} EC classes.")

    # ── model ────────────────────────────────────────────────────────────────
    print(f"[theia] Loading model from {model_pt} ...")
    model = load_model(model_pt, label_encoder)

    # ── encode DRFP ──────────────────────────────────────────────────────────
    print("[theia] Encoding DRFP fingerprints ...")
    t0 = time.time()
    X = encode_drfp(smiles_list, batch_size=args.batch_size)
    print(f"[theia] Encoding done in {time.time() - t0:.1f}s  shape={X.shape}")

    # ── inference ────────────────────────────────────────────────────────────
    print("[theia] Running inference ...")
    t1 = time.time()
    pred_indices, confidences = predict(model, X, batch_size=args.batch_size)
    pred_labels = label_encoder.inverse_transform(pred_indices)
    print(f"[theia] Inference done in {time.time() - t1:.1f}s")

    # ── metrics ──────────────────────────────────────────────────────────────
    if any(l not in ("", "nan", "none") for l in true_labels):
        metrics = _compute_metrics(true_labels, list(pred_labels))
        split = input_csv.stem
        print(f"\n{'='*52}")
        print(f"  Theia MLP  {split.upper()} RESULTS")
        print(f"{'='*52}")
        print(f"  Accuracy   : {metrics['accuracy']:.4f}")
        print(f"  F1 macro   : {metrics['f1_macro']:.4f}")
        print(f"  F1 weighted: {metrics['f1_weighted']:.4f}")
        print(f"  MCC        : {metrics['mcc']:.4f}")
        print(f"  N samples  : {len(pred_labels)}")
        print(f"{'='*52}\n")

    # ── save TSV ─────────────────────────────────────────────────────────────
    output_tsv.parent.mkdir(parents=True, exist_ok=True)
    out_df = pd.DataFrame({
        "true_label":  true_labels,
        "pred":        list(pred_labels),
        "confidence":  confidences,
        "smiles":      smiles_list,
    })
    out_df.to_csv(output_tsv, sep="\t", index=False)
    print(f"[theia] Saved → {output_tsv}")


def parse_args():
    ap = argparse.ArgumentParser(
        description="Evaluate Theia MLP on a CSV split.",
        allow_abbrev=False,
    )
    ap.add_argument("--input_csv",    type=str, required=True,
                    help="CSV with rxn_smiles (and optionally ec) columns.")
    ap.add_argument("--output_tsv",   type=str, required=True,
                    help="Output TSV path for predictions.")
    ap.add_argument("--model_pt",     type=str, required=True,
                    help="Path to Theia .pt model saved by train_theia.py.")
    ap.add_argument("--labelenc_pkl", type=str, required=True,
                    help="Path to label_encoder.pkl saved by train_theia.py.")
    ap.add_argument("--batch_size",   type=int, default=_BATCH_SIZE,
                    help=f"Batch size for encoding and inference. (default: {_BATCH_SIZE})")
    return ap.parse_args()


if __name__ == "__main__":
    main()
