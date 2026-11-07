
# gemma4ec/src/utils/metrics.py

import re
from typing import Dict, List
from sklearn.metrics import accuracy_score, f1_score, matthews_corrcoef
import numpy as np

# Canonical 3-part EC format: x.xx.xx  (e.g. 2.07.08, 1.1.1, 3.05.04)
_EC_3PART_RE = re.compile(r"^\d+\.\d{1,2}\.\d{1,2}$")


def is_valid_ec(s: str) -> bool:
    """Return True if s matches the canonical 3-part EC format (e.g. '2.07.08')."""
    return bool(_EC_3PART_RE.fullmatch(str(s).strip()))


def compute_classification_metrics(true_labels: List[str], pred_labels: List[str]) -> Dict:
    acc = accuracy_score(true_labels, pred_labels)
    f1_macro = f1_score(true_labels, pred_labels, average="macro")
    f1_weighted = f1_score(true_labels, pred_labels, average="weighted")
    mcc = matthews_corrcoef(true_labels, pred_labels)
    return {
        "accuracy": acc,
        "f1_macro": f1_macro,
        "f1_weighted": f1_weighted,
        "mcc": mcc
    }
