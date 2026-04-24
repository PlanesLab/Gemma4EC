
# /gemma4ec/src/training/manual/text_fewshot_utils.py

import re
from typing import Tuple

# =========================
#  Few-shot helpers  
# =========================
_SMILES_RE = re.compile(r"^\s*Reaction\s+SMILES\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)

def _split_instructions_and_smiles_block(input_text: str) -> tuple[str, str]:
    """
    Split an input prompt into:
      - instructions: everything BEFORE the first 'Reaction SMILES:' line
      - rxn_line: the 'Reaction SMILES: ...' line as a single line

    If no 'Reaction SMILES:' is found, instructions = full text, rxn_line = '' (empty).
    """
    m = _SMILES_RE.search(input_text)
    if not m:
        return input_text.strip(), ""
    start, end = m.span()
    instructions = input_text[:start].strip()
    rxn_line = f"Reaction SMILES: {m.group(1).strip()}"
    return instructions, rxn_line

def _fmt_shot(input_text: str, output_text: str) -> str:
    """
    Lightweight shot: keep only 'Reaction SMILES' + 'Answer: <label>'.
    Instructions are NOT repeated here.
    """
    _, rxn_line = _split_instructions_and_smiles_block(input_text)
    # Fallback: if we failed to extract a SMILES line, keep the whole text (rare)
    rxn_line = rxn_line if rxn_line else input_text.strip()
    return f"{rxn_line}\nAnswer: {output_text}".strip()

def _fmt_query_tail(input_text: str) -> str:
    """
    Final query tail: ONLY 'Reaction SMILES: ...' + 'Answer:' (empty).
    Instructions must be placed once at the header (outside this function).
    """
    _, rxn_line = _split_instructions_and_smiles_block(input_text)
    rxn_line = rxn_line if rxn_line else input_text.strip()
    return f"{rxn_line}\nAnswer:"