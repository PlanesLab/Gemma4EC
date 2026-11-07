#!/usr/bin/env python3
"""
brenda_refs.py — BRENDA enzyme references for the chat pipeline.

For a predicted EC sub-subclass, parses the BRENDA flat file for the enzymes of that class and
and lists them with their known reactions (MetaNetX tables shipped with SelenzymeRF). Used by
chat/prepare_chat.py, which decides which of them reach the model.
"""

import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

_HEADER_RE = re.compile(r'^[A-Z][A-Z_]{3,}$')
TARGET_SECTIONS = {"RECOMMENDED_NAME", "SYSTEMATIC_NAME", "REACTION", "REACTION_TYPE"}


def normalize_ec3(ec_id) -> str | None:
    parts = str(ec_id).strip().split('.')
    if len(parts) < 3:
        return None
    try:
        return '.'.join(str(int(p)) for p in parts[:3])
    except ValueError:
        return None


def clean_brenda_text(text: str) -> str:
    """Drop organism/literature markers (#12#, <34>) and the bracketed commentary after a reaction."""
    text = re.split(r'\s\((?=#)', text)[0]
    text = re.sub(r'#[\d,]+#\s*|<[\d,]+>|\{[^}]*\}', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def parse_brenda_for_ec3s(brenda_file: Path, ec3_set: set[str]) -> dict[str, list[dict]]:
    """Return {ec3: [enzyme entries]} for the requested EC sub-subclasses only."""
    classes: dict[str, list[dict]] = defaultdict(list)
    current_id, current_section, current_data, buf = None, None, {}, []

    def flush():
        if buf and current_section in TARGET_SECTIONS:
            current_data.setdefault(current_section, []).append(' '.join(buf))
        buf.clear()

    with open(brenda_file, encoding='utf-8', errors='replace') as fh:
        for raw in fh:
            line = raw.rstrip('\n')
            stripped = line.strip()
            if stripped == '///':
                flush()
                ec3 = normalize_ec3(current_id) if current_id else None
                if ec3 in ec3_set:
                    uniq = lambda xs: list(dict.fromkeys(clean_brenda_text(x) for x in xs if clean_brenda_text(x)))
                    classes[ec3].append({
                        "ec4":        current_id,
                        "name":       (uniq(current_data.get("RECOMMENDED_NAME", [])) or [""])[0],
                        "systematic": (uniq(current_data.get("SYSTEMATIC_NAME", [])) or [""])[0],
                        "types":      uniq(current_data.get("REACTION_TYPE", []))[:3],
                        "reactions":  uniq(current_data.get("REACTION", []))[:2],
                        # all substrate/product pairs, lower case, for keyword matching (prepare_chat.py)
                        "substrates_text": ' '.join(uniq(current_data.get("SUBSTRATE_PRODUCT", [])))[:200_000].lower(),
                    })
                current_id, current_section, current_data = None, None, {}
                buf = []
                continue
            if line.startswith('ID\t'):
                flush()
                current_id, current_section, current_data = line[3:].strip(), None, {}
                buf = []
                continue
            if current_id is None:
                continue
            if stripped and '\t' not in line and _HEADER_RE.match(stripped):
                flush()
                current_section = stripped
                continue
            if current_section not in TARGET_SECTIONS:
                continue
            if not stripped:
                flush()
            elif line.startswith('\t'):
                buf.append(stripped)
            elif '\t' in line:
                flush()
                content = line.partition('\t')[2].strip()
                if content:
                    buf.append(content)
    return classes


# ── BRENDA enzymes of the predicted sub-subclass, with their known reactions ──


def live_enzymes(enzymes: list[dict], max_enzymes: int) -> list[dict]:
    """The live BRENDA enzymes of the class, in BRENDA order; deleted and transferred EC numbers dropped.

    No reaction fingerprint is computed: which of them reach the model is decided by
    prepare_chat.py from the reaction's own participants and cofactors.
    """
    live = [e for e in enzymes if not re.search(r'\b(deleted|transferred)\b', e["name"], re.I)]
    return live[:max_enzymes]


def format_brenda(ec3: str, enzymes: list[dict], max_chars: int) -> str:
    if not enzymes:
        return f"No BRENDA entry found for EC {ec3}."
    lines = []
    for e in enzymes:
        head = f"- EC {e['ec4']} {e['name']}"
        if e["systematic"]:
            head += f" (systematic: {e['systematic']})"
        lines.append(head)
        if e["types"]:
            lines.append(f"  type: {'; '.join(e['types'])}")
        for r in e["reactions"]:
            lines.append(f"  reaction: {r[:250]}")
    text = '\n'.join(lines)
    return text if len(text) <= max_chars else text[:max_chars].rsplit('\n- ', 1)[0] + "\n[... more enzymes in this sub-subclass]"


# ── attention ─────────────────────────────────────────────────────────────────
