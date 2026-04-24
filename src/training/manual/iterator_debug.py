
# gemma4ec/src/training/manual/iterator_debug.py

from itertools import chain
from typing import Tuple

def _first_signature_from_iterator(dataloader, max_batches: int = 2, max_ids: int = 32):
    """
    Extracts (first_batch, signature) from the SAME iterator you'll use later.
    The signature concatenates 'row_ids' from the first `max_batches` batches for inspection
    
    """
    it = iter(dataloader)
    first_batch = None
    sig = []
    cached_batches = []
    for _ in range(max_batches):
        try:
            batch = next(it)
        except StopIteration:
            break
        if first_batch is None:
            first_batch = batch
        cached_batches.append(batch)
        if "row_ids" in batch:
            sig.extend(batch["row_ids"].tolist())

    it = chain(cached_batches[1:], it) if len(cached_batches) > 1 else it
    return (first_batch, tuple(sig[:max_ids])), it
