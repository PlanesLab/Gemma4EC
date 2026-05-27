#!/usr/bin/env python3
"""
Build 10 mechanistic-explanation prompts for TxGemma-9B-Chat.

For each reaction in attn_out/summary.tsv, assembles a prompt containing:
  - reaction SMILES
  - predicted EC number
  - BRENDA sub-subclass summary
  - attention vector (per-SMILES-token, averaged over sampled layers & heads)

Output: chat/prompts/mechanistic_prompts.json

Usage:
    python chat/build_mechanistic_prompts.py
"""

import re
import json
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

ATTN_DIR   = Path("attn_out")
BRENDA = Path(os.environ.get("BRENDA_FILE", "brenda_2026_1.txt"))
OUT_FILE   = Path("chat/prompts/mechanistic_prompts.json")

_HEADER_RE = re.compile(r'^[A-Z][A-Z_]{3,}$')
TARGET_SECTIONS = {"RECOMMENDED_NAME", "SYSTEMATIC_NAME", "REACTION", "REACTION_TYPE"}


# ── BRENDA parsing ─────────────────────────────────────────────────────────────

def normalize_ec3(ec_id: str) -> str | None:
    parts = ec_id.strip().split('.')
    if len(parts) < 3:
        return None
    try:
        return '.'.join(str(int(p)) for p in parts[:3])
    except ValueError:
        return None


def parse_brenda_for_ec3s(ec3_set: set[str]) -> dict[str, str]:
    """Return {ec3: text_summary} for the requested EC sub-subclasses only."""
    classes: dict[str, list[dict]] = defaultdict(list)

    current_id = None
    current_data: dict = {}
    current_section: str | None = None
    buf: list[str] = []

    def flush():
        if buf and current_section in TARGET_SECTIONS:
            current_data.setdefault(current_section, []).append(' '.join(buf))
        buf.clear()

    with open(BRENDA, encoding='utf-8', errors='replace') as fh:
        for raw in fh:
            line = raw.rstrip('\n')
            stripped = line.strip()

            if stripped == '///':
                flush()
                if current_id is not None:
                    ec3 = normalize_ec3(current_id)
                    if ec3 in ec3_set and len(classes[ec3]) < 20:
                        classes[ec3].append({
                            "ec4":       current_id,
                            "names":     current_data.get("RECOMMENDED_NAME", [])[:2],
                            "systematic": current_data.get("SYSTEMATIC_NAME", [])[:1],
                            "reactions": current_data.get("REACTION", [])[:4],
                            "types":     current_data.get("REACTION_TYPE", [])[:3],
                        })
                current_id = None
                current_section = None
                current_data = {}
                buf = []
                continue

            if line.startswith('ID\t'):
                flush()
                current_id = line[3:].strip()
                current_section = None
                current_data = {}
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
                continue

            if line.startswith('\t'):
                buf.append(stripped)
            elif '\t' in line:
                flush()
                _, _, content = line.partition('\t')
                if content.strip():
                    buf.append(content.strip())

    flush()

    summaries: dict[str, str] = {}
    for ec3, enzymes in classes.items():
        lines = [f"EC {ec3} sub-subclass information:"]
        for e in enzymes:
            lines.append(f"EC {e['ec4']}:")
            if e["names"]:
                lines.append(f"Recommended name: {e['names'][0]}")
            if e["systematic"]:
                lines.append(f"Systematic name: {e['systematic'][0]}")
            if e["types"]:
                lines.append(f"Reaction type: {'; '.join(e['types'])}")
            if e["reactions"]:
                for rxn in e["reactions"]:
                    short = rxn[:300] + ("..." if len(rxn) > 300 else "")
                    lines.append(f"Reaction: {short}")
            lines.append("")
        summary = '\n'.join(lines).strip()
        if len(summary) > 5000:
            summary = summary[:5000] + "\n[truncated]"
        summaries[ec3] = summary

    return summaries


# ── attention extraction ───────────────────────────────────────────────────────

def extract_smiles_attention(html_path: Path, sm_start: int, sm_end: int):
    """
    Parse a bertviz HTML file and return:
      tokens       list[str]  — SMILES tokens only
      attn_vector  list[float] — per-SMILES-token attention weight
                                 (averaged over sampled layers & heads,
                                  queried from the final token position)
    """
    html = html_path.read_text(encoding='utf-8')
    m = re.search(r'params\s*=\s*(\{.*?\});', html, re.DOTALL)
    if not m:
        return [], []

    data = json.loads(m.group(1))
    entry = data['attention'][0]

    all_tokens = entry['left_text']        # full token list
    # shape: [n_layers, n_heads, seq_len, seq_len]
    attn = np.array(entry['attn'], dtype=np.float32)

    # Average over sampled layers and heads → [seq_len, seq_len]
    avg_attn = attn.mean(axis=(0, 1))

    # Use the last token as the query (closest to EC generation)
    last_row = avg_attn[-1]               # [seq_len]

    # Slice to SMILES token region
    sm_slice = last_row[sm_start:sm_end]

    # Normalize to sum to 1
    total = sm_slice.sum()
    if total > 0:
        sm_slice = sm_slice / total
    else:
        sm_slice = np.zeros_like(sm_slice)

    smiles_tokens = all_tokens[sm_start:sm_end]
    return smiles_tokens, sm_slice.tolist()


# ── prompt template ────────────────────────────────────────────────────────────

PROMPT_TEMPLATE = """\
You are an expert enzymologist and mechanistic chemist.

A large language model (TxGemma-9B) was given the following reaction SMILES and predicted the EC number {ec} for the enzyme that catalyzes it. The attention profile below shows which SMILES tokens the model attended to most when making that prediction.

Reaction SMILES: {rxn_smiles}

Predicted EC number (by TxGemma-9B): {ec}

EC sub-subclass information (BRENDA):
{brenda_info}

Tokenized SMILES: {smiles_tokens}
Attention profile (weight per token, same order, normalized to sum to 1):
{attention_profile}

Using the reaction SMILES, the EC number predicted by TxGemma-9B, the BRENDA reference, and the attention profile, provide a detailed mechanistic explanation for why this reaction belongs to EC {ec}. Cover the type of chemical transformation, the likely catalytic mechanism, how the structural features of the reactants and products support this classification, and which parts of the molecule the model's attention highlights as most relevant."""


def format_attention_profile(tokens: list[str], weights: list[float]) -> str:
    if not weights:
        return "N/A"
    return ' '.join(f"{t}:{w:.2f}" for t, w in zip(tokens, weights))


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    tsv = ATTN_DIR / "summary.tsv"
    df  = pd.read_csv(tsv, sep='\t')

    # Collect unique EC3s to look up in BRENDA
    ec3_set = set()
    for ec in df['predicted_ec']:
        ec3 = normalize_ec3(ec)
        if ec3:
            ec3_set.add(ec3)

    print(f"Fetching BRENDA summaries for: {sorted(ec3_set)}")
    brenda_index = parse_brenda_for_ec3s(ec3_set)
    print(f"  Got {len(brenda_index)} entries.")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for _, row in df.iterrows():
        rxn_id  = int(row['reaction'])
        smiles  = row['rxn_smiles']
        ec3     = normalize_ec3(row['predicted_ec']) or row['predicted_ec']
        true_ec = normalize_ec3(row['true_ec']) or row['true_ec']
        pred_ec = ec3  # display without zero-padding
        sm_start = int(row['smiles_tok_start'])
        sm_end   = int(row['smiles_tok_end'])

        brenda_info = brenda_index.get(ec3, f"No BRENDA entry found for EC {ec3}.")

        html_path = ATTN_DIR / f"rxn{rxn_id:02d}_bertviz.html"
        if html_path.exists():
            smiles_tokens, attn_vector = extract_smiles_attention(html_path, sm_start, sm_end)
        else:
            smiles_tokens, attn_vector = [], []

        attn_profile_str = format_attention_profile(smiles_tokens, attn_vector)

        prompt_text = PROMPT_TEMPLATE.format(
            ec=pred_ec,
            rxn_smiles=smiles,
            brenda_info=brenda_info,
            smiles_tokens=' '.join(smiles_tokens) if smiles_tokens else 'N/A',
            attention_profile=attn_profile_str,
        )

        records.append({
            "rxn_id":          rxn_id,
            "rxn_smiles":      smiles,
            "true_ec":         true_ec,
            "predicted_ec":    pred_ec,
            "ec_subsubclass":  ec3,
            "smiles_tokens":   smiles_tokens,
            "attention_vector": [round(v, 2) for v in attn_vector],
            "brenda_summary":  brenda_info,
            "prompt":          prompt_text,
        })

        print(f"  rxn{rxn_id:02d}  EC {pred_ec}  SMILES tokens: {len(smiles_tokens)}")

    with open(OUT_FILE, 'w', encoding='utf-8') as fh:
        json.dump(records, fh, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(records)} prompts → {OUT_FILE}")


if __name__ == "__main__":
    main()
