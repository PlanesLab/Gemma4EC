"""
train_theia.py — Train the Theia MLP on a raw CSV partition.

Reads train/val/test CSVs with `rxn_smiles` and `ec` columns, encodes DRFP
fingerprints, trains an MLPClassifier with early stopping on val loss, and
evaluates on the test set. Outputs are saved to --output_dir:

    <output_dir>/model.pt             — model weights
    <output_dir>/label_encoder.pkl    — sklearn LabelEncoder
    <output_dir>/training_metrics.pkl — per-epoch loss/acc
    <output_dir>/test_predictions.tsv — TSV compatible with summarize_results.py

Usage:
    python train_theia.py \
        --train_csv data/raw/train.csv \
        --val_csv   data/raw/val.csv \
        --test_csv  data/raw/test.csv \
        --output_dir outputs/theia_raw
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
import torch.nn.functional as nnf
from drfp import DrfpEncoder
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.metrics import accuracy_score, f1_score, matthews_corrcoef
from sklearn.preprocessing import LabelEncoder
from theia.ml import MLPClassifier, ReactionDataset
from torch.optim.lr_scheduler import ExponentialLR
from torch.utils.data import DataLoader

warnings.filterwarnings("ignore", category=InconsistentVersionWarning)


def _compute_metrics(true_labels, pred_labels):
    return {
        "accuracy":    accuracy_score(true_labels, pred_labels),
        "f1_macro":    f1_score(true_labels, pred_labels, average="macro", zero_division=0),
        "f1_weighted": f1_score(true_labels, pred_labels, average="weighted", zero_division=0),
        "mcc":         matthews_corrcoef(true_labels, pred_labels),
    }

# ── constants (match original Theia paper) ──────────────────────────────────
_FPS_LENGTH = 10240
_HIDDEN_DIM = 1664
_LR         = 1e-3
_LR_GAMMA   = 0.9
_BATCH_TRAIN = 64
_BATCH_EVAL  = 256
_EPOCHS      = 50
_PATIENCE    = 5
# ────────────────────────────────────────────────────────────────────────────


def encode_drfp(smiles_list: list[str], desc: str = "") -> np.ndarray:
    print(f"[drfp] Encoding {len(smiles_list)} reactions{' (' + desc + ')' if desc else ''} ...")
    t0 = time.time()
    fps = DrfpEncoder.encode(
        smiles_list,
        root_central_atom=False,
        radius=2,
        include_hydrogens=True,
        n_folded_length=_FPS_LENGTH,
        show_progress_bar=True,
    )
    arr = np.array([np.array(fp, dtype=np.float32) for fp in fps], dtype=np.float32)
    print(f"[drfp] Done in {time.time() - t0:.1f}s  shape={arr.shape}")
    return arr


def load_split(csv_path: Path, le: LabelEncoder | None, desc: str) -> tuple[pd.DataFrame, LabelEncoder | None]:
    """Load CSV, encode DRFP, apply label encoder. Returns (df_with_fps_and_label, le)."""
    df = pd.read_csv(csv_path)
    df = df[df["rxn_smiles"].notna() & df["ec"].notna()].copy()

    # Remove EC class 7 (translocases) — matches original Theia preprocessing
    df["_ec1"] = df["ec"].astype(str).str.split(".").str[0]
    df = df[df["_ec1"] != "7"].drop(columns=["_ec1"])

    df["rxn_smiles"] = df["rxn_smiles"].astype(str).str.strip()
    df["ec"] = df["ec"].astype(str).str.strip()

    fps = encode_drfp(df["rxn_smiles"].tolist(), desc=desc)
    df["fps"] = [row for row in fps]

    if le is None:
        # Will be fit after all splits are loaded
        return df, None

    # Map to integer labels; rows with unseen labels (not in le.classes_) are dropped
    known = set(le.classes_)
    mask = df["ec"].isin(known)
    if (~mask).any():
        print(f"  [warn] {(~mask).sum()} rows with unseen EC labels dropped from {desc}")
        df = df[mask].copy()
    df["label"] = le.transform(df["ec"])
    return df, le


def make_dataset(df: pd.DataFrame) -> ReactionDataset:
    return ReactionDataset(df)


def run_epoch(model, loader, optimizer, criterion, device, train: bool):
    model.train(train)
    total_loss = 0.0
    correct = 0
    total = 0
    for X, y in loader:
        X, y = X.to(device), y.to(device)
        if train:
            optimizer.zero_grad()
        out = model(X)
        loss = criterion(out, y)
        if train:
            loss.backward()
            optimizer.step()
        total_loss += loss.item()
        correct += out.argmax(1).eq(y).sum().item()
        total += len(y)
    return total_loss / len(loader), correct / total


@torch.no_grad()
def evaluate(model, loader, device, le: LabelEncoder):
    model.eval()
    all_true, all_pred = [], []
    for X, y in loader:
        X = X.to(device)
        pred = model(X).argmax(1).cpu().numpy()
        all_pred.extend(pred.tolist())
        all_true.extend(y.numpy().tolist())
    return le.inverse_transform(all_true), le.inverse_transform(all_pred)


def main():
    args = parse_args()

    train_csv = Path(args.train_csv)
    val_csv   = Path(args.val_csv)
    test_csv  = Path(args.test_csv)
    out_dir   = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── load & encode ────────────────────────────────────────────────────────
    df_train, _ = load_split(train_csv, le=None, desc="train")
    df_val,   _ = load_split(val_csv,   le=None, desc="val")
    df_test,  _ = load_split(test_csv,  le=None, desc="test")

    # Fit label encoder on train+val (covers all classes seen during training)
    le = LabelEncoder()
    le.fit(pd.concat([df_train["ec"], df_val["ec"], df_test["ec"]]))
    print(f"[le] {len(le.classes_)} EC classes after fitting on train+val+test.")

    le_path = out_dir / "label_encoder.pkl"
    with open(le_path, "wb") as f:
        pickle.dump(le, f)
    print(f"[le] Saved → {le_path}")

    # Apply labels
    for df in (df_train, df_val, df_test):
        df["label"] = le.transform(df["ec"])

    # ── datasets & loaders ───────────────────────────────────────────────────
    ds_train = make_dataset(df_train)
    ds_val   = make_dataset(df_val)
    ds_test  = make_dataset(df_test)

    loader_train = DataLoader(ds_train, batch_size=_BATCH_TRAIN, shuffle=True,  num_workers=4, pin_memory=True)
    loader_val   = DataLoader(ds_val,   batch_size=_BATCH_EVAL,  shuffle=False, num_workers=4, pin_memory=True)
    loader_test  = DataLoader(ds_test,  batch_size=_BATCH_EVAL,  shuffle=False, num_workers=4, pin_memory=True)

    # ── model ────────────────────────────────────────────────────────────────
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[train] Device: {device}")

    n_classes = len(le.classes_)
    model = MLPClassifier(_FPS_LENGTH, args.hidden_dim, n_classes).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    scheduler = ExponentialLR(optimizer, gamma=_LR_GAMMA)
    criterion = torch.nn.CrossEntropyLoss()

    # ── training loop ────────────────────────────────────────────────────────
    best_val_loss = float("inf")
    best_state = None
    patience_counter = 0

    history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}

    print(f"\n[train] Starting training: {args.epochs} epochs, hidden_dim={args.hidden_dim}, "
          f"n_classes={n_classes}, train={len(ds_train)}, val={len(ds_val)}")

    for epoch in range(1, args.epochs + 1):
        t0 = time.time()
        train_loss, train_acc = run_epoch(model, loader_train, optimizer, criterion, device, train=True)
        with torch.no_grad():
            val_loss, val_acc = run_epoch(model, loader_val, None, criterion, device, train=False)
        scheduler.step()

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["train_acc"].append(train_acc)
        history["val_acc"].append(val_acc)

        elapsed = time.time() - t0
        print(f"  Epoch {epoch:3d}/{args.epochs}  "
              f"train_loss={train_loss:.4f}  val_loss={val_loss:.4f}  "
              f"train_acc={train_acc:.4f}  val_acc={val_acc:.4f}  "
              f"({elapsed:.1f}s)")

        if val_loss < best_val_loss - 1e-4:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"  [early stop] No improvement for {args.patience} epochs. Stopping.")
                break

    # ── restore best & save ──────────────────────────────────────────────────
    if best_state is not None:
        model.load_state_dict(best_state)
        print(f"[train] Restored best model (val_loss={best_val_loss:.4f})")

    model_path = out_dir / "model.pt"
    torch.save(model.state_dict(), model_path)
    print(f"[train] Model saved → {model_path}")

    metrics_path = out_dir / "training_metrics.pkl"
    with open(metrics_path, "wb") as f:
        pickle.dump(history, f)

    # ── test evaluation ──────────────────────────────────────────────────────
    print("\n[eval] Running test set evaluation ...")
    true_labels, pred_labels = evaluate(model, loader_test, device, le)

    metrics = _compute_metrics(list(true_labels), list(pred_labels))

    smiles_list = df_test["rxn_smiles"].tolist()
    print(f"\n{'='*52}")
    print(f"  Theia MLP  TEST RESULTS (Raw partition)")
    print(f"{'='*52}")
    print(f"  Accuracy   : {metrics['accuracy']:.4f}")
    print(f"  F1 macro   : {metrics['f1_macro']:.4f}")
    print(f"  F1 weighted: {metrics['f1_weighted']:.4f}")
    print(f"  MCC        : {metrics['mcc']:.4f}")
    print(f"  N samples  : {len(pred_labels)}")
    print(f"{'='*52}\n")

    # ── save TSV ─────────────────────────────────────────────────────────────
    out_tsv = out_dir / "test_predictions.tsv"
    pd.DataFrame({
        "true_label": list(true_labels),
        "pred":       list(pred_labels),
        "smiles":     smiles_list,
    }).to_csv(out_tsv, sep="\t", index=False)
    print(f"[eval] Saved → {out_tsv}")

    # Also run on val split
    print("\n[eval] Running val set evaluation ...")
    val_true, val_pred = evaluate(model, loader_val, device, le)
    val_metrics = _compute_metrics(list(val_true), list(val_pred))
    print(f"  Val accuracy: {val_metrics['accuracy']:.4f}  MCC: {val_metrics['mcc']:.4f}")

    val_tsv = out_dir / "val_predictions.tsv"
    pd.DataFrame({
        "true_label": list(val_true),
        "pred":       list(val_pred),
        "smiles":     df_val["rxn_smiles"].tolist(),
    }).to_csv(val_tsv, sep="\t", index=False)
    print(f"[eval] Saved → {val_tsv}")


def parse_args():
    ap = argparse.ArgumentParser(
        description="Train Theia MLP on a raw CSV partition.",
        allow_abbrev=False,
    )
    ap.add_argument("--train_csv",   type=str, default="data/raw/train.csv")
    ap.add_argument("--val_csv",     type=str, default="data/raw/val.csv")
    ap.add_argument("--test_csv",    type=str, default="data/raw/test.csv")
    ap.add_argument("--output_dir",  type=str, required=True,
                    help="Directory to save model, label encoder, metrics, and predictions.")
    ap.add_argument("--hidden_dim",  type=int, default=_HIDDEN_DIM)
    ap.add_argument("--epochs",      type=int, default=_EPOCHS)
    ap.add_argument("--patience",    type=int, default=_PATIENCE)
    ap.add_argument("--lr",          type=float, default=_LR)
    return ap.parse_args()


if __name__ == "__main__":
    main()
