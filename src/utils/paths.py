# gemma4ec/src/utils/paths.py

from pathlib import Path
from typing import Optional

def get_jsonl_path(
    parent_dir: str,
    split: str,                       # "train" | "val" | "test" | "predict"
    template_key: Optional[str] = None,  # e.g., "EC_NUMBER_PROMPT_1"
    alias: Optional[str] = None,         # e.g., "EC_NUMBER"
    create_dir: bool = True,
) -> str:
    """
    Build a single JSONL path inside `parent_dir`, e.g.:
      /scratch/.../data/train.EC_NUMBER.EC_NUMBER_PROMPT_1.jsonl
    """
    split = split.strip().lower()
    if split not in {"train", "val", "test", "predict"}:
        raise ValueError("split must be 'train', 'val', 'test' or 'predict'.")
    parent = Path(parent_dir)
    if create_dir:
        parent.mkdir(parents=True, exist_ok=True)
    parts = [split]
    if alias:
        parts.append(alias)
    if template_key:
        parts.append(template_key)
    filename = ".".join(parts) + ".jsonl"
    return str(parent / filename)