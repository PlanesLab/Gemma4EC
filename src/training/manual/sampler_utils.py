
# /gemma4ec/src/training/manual/sampler_utils.py

import random
import numpy as np
import torch

# ------------------------------
# Sampler control + firmas
# ------------------------------
def _set_epoch_on_sampler(dataloader, epoch: int) -> bool:
    """Intenta aplicar set_epoch al sampler (DistributedSampler). Devuelve True si se aplicó."""
    for obj in (
        getattr(dataloader, "sampler", None),
        getattr(getattr(dataloader, "batch_sampler", None), "sampler", None),
    ):
        if hasattr(obj, "set_epoch"):
            obj.set_epoch(epoch)
            return True
    return False

def _reseed_for_epoch(base_seed: int, epoch: int):
    """Resiembra RNGs para que RandomSampler (u otras fuentes) barajen distinto cada epoch."""
    s = int(base_seed) + int(epoch)
    random.seed(s)
    np.random.seed(s % (2**32 - 1))
    torch.manual_seed(s)
    # si entrenas en GPU(s), añade:
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(s)