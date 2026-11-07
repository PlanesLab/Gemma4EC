# /gemma4ec/src/training/manual/ops.py

from typing import Any, Tuple
import torch
from transformers import get_scheduler

try:
    import bitsandbytes as bnb  # opcional
except Exception:
    bnb = None

def _pick_optimizer(model, args):
    """
    Choose optimizer over *trainable* (LoRA) params, mirroring SFTTrainer:
    - "paged_adamw_8bit" -> bitsandbytes PagedAdamW8bit (if available)
    - "adamw_torch"/"adamw" -> torch.optim.AdamW
    Falls back to AdamW with a warning if unknown/unavailable.
    """
    name = str(getattr(args, "optimizer", "adamw_torch")).lower()
    lr = float(getattr(args, "learning_rate", 5e-6))
    wd = float(getattr(args, "weight_decay", 0.0))
    params = [p for p in model.parameters() if p.requires_grad]
    if "paged" in name and "8bit" in name:
        if bnb is not None and hasattr(bnb.optim, "PagedAdamW8bit"):
            return bnb.optim.PagedAdamW8bit(params, lr=lr, weight_decay=wd)
        print("[warn] bitsandbytes PagedAdamW8bit not available; falling back to AdamW.")
    if ("adamw_torch" in name) or (name == "adamw"):
        return torch.optim.AdamW(params, lr=lr, weight_decay=wd)
    print(f"[warn] Unknown optimizer '{name}', using torch.optim.AdamW.")
    return torch.optim.AdamW(params, lr=lr, weight_decay=wd)

def _pick_scheduler(optimizer, args, num_training_steps: int):
    """
    Build LR scheduler equivalent to SFTTrainer config:
    supports 'linear', 'cosine', 'cosine_with_restarts',
    'polynomial', 'constant', 'constant_with_warmup'.
    Uses transformers.get_scheduler with warmup_steps.
    """
    name = str(getattr(args, "lr_scheduler_type", "linear")).lower()
    warmup_steps = int(getattr(args, "warmup_steps", 0))
    valid = {
        "linear", "cosine", "cosine_with_restarts",
        "polynomial", "constant", "constant_with_warmup"
    }
    if name not in valid:
        print(f"[warn] Unknown scheduler '{name}', using 'linear'.")
        name = "linear"
    return get_scheduler(
        name=name,
        optimizer=optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=num_training_steps,
    )

def _global_grad_norm(parameters) -> float:
    # Grad-norm L2 sobre todos los params entrenables con grad disponible
    norms = []
    for p in parameters:
        if p.grad is not None:
            # usa fp32 para estabilidad
            norms.append(p.grad.detach().float().norm(2))
    if not norms:
        return 0.0
    stacked = torch.stack(norms)
    return float(torch.norm(stacked, p=2).item())

def _token_acc_from_logits(logits: torch.Tensor, labels: torch.Tensor) -> tuple[int, int]:
    """
    Causal LM token accuracy (shifted):
      compare argmax(logits[..., :-1, :]) vs labels[..., 1:]
      ignora posiciones con label == -100.
    Devuelve (correctos, total)
    """
    with torch.no_grad():
        # shift
        shift_logits = logits[..., :-1, :]
        shift_labels = labels[..., 1:]
        # máscara válida
        valid = shift_labels.ne(-100)
        if not valid.any():
            return 0, 0
        preds = shift_logits.argmax(dim=-1)
        correct = (preds.eq(shift_labels) & valid).sum().item()
        total = valid.sum().item()
        return correct, total