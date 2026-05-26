#!/usr/bin/env python3
"""
Parse the BRENDA flat-file and build a per-EC-subsubclass JSON index for RAG.

Each BRENDA entry (delimited by ///) maps to a 4-part EC number.
This script groups them by 3-part prefix (class.subclass.sub-subclass) and
builds a text summary per group that can be injected into a chat prompt.

Usage:
    python chat/build_brenda_index.py \
        --brenda_file /data/jarcagniriv/BRENDA/brenda_2026_1.txt \
        --output_file /scratch/jarcagniriv/Gemma4EC/chat/data/brenda_index.json
"""

import re
import json
import argparse
from pathlib import Path
from collections import defaultdict

# Section headers are all-caps identifiers (≥4 chars, letters + underscores)
_HEADER_RE = re.compile(r'^[A-Z][A-Z_]{3,}$')

TARGET_SECTIONS = {"RECOMMENDED_NAME", "SYSTEMATIC_NAME", "REACTION", "REACTION_TYPE"}


def normalize_ec3(ec_id: str) -> str | None:
    """'1.1.1.1' or '2.07.08.01' → '1.1.1';  non-numeric → None."""
    parts = ec_id.strip().split('.')
    if len(parts) < 3:
        return None
    try:
        return '.'.join(str(int(p)) for p in parts[:3])
    except ValueError:
        return None


def parse_brenda_entries(file_path: str):
    """
    Stream-parse the BRENDA flat file.
    Yields (ec_id: str, data: dict[section, list[str]]) for each entry.
    Only extracts sections in TARGET_SECTIONS.
    """
    current_id = None
    current_data: dict = {}
    current_section: str | None = None
    buf: list[str] = []

    def flush():
        if buf and current_section in TARGET_SECTIONS:
            current_data.setdefault(current_section, []).append(' '.join(buf))
        buf.clear()

    with open(file_path, 'r', encoding='utf-8', errors='replace') as fh:
        for raw in fh:
            line = raw.rstrip('\n')
            stripped = line.strip()

            # ── entry separator ──────────────────────────────────────────
            if stripped == '///':
                flush()
                if current_id is not None:
                    yield current_id, current_data
                current_id = None
                current_section = None
                current_data = {}
                buf = []
                continue

            # ── entry ID ─────────────────────────────────────────────────
            if line.startswith('ID\t'):
                current_id = line[3:].strip()
                current_section = None
                current_data = {}
                buf = []
                continue

            if current_id is None:
                continue

            # ── section header (all-caps, no tab) ────────────────────────
            if stripped and '\t' not in line and _HEADER_RE.match(stripped):
                flush()
                current_section = stripped
                continue

            if current_section not in TARGET_SECTIONS:
                continue

            # ── blank line → flush current buffer entry ──────────────────
            if not stripped:
                flush()
                continue

            # ── continuation (leading tab) ────────────────────────────────
            if line.startswith('\t'):
                buf.append(stripped)
                continue

            # ── new content line: CODE\tCONTENT ──────────────────────────
            if '\t' in line:
                flush()
                _, _, content = line.partition('\t')
                if content.strip():
                    buf.append(content.strip())
                continue

        # flush final entry
        flush()
        if current_id is not None:
            yield current_id, current_data


def build_index(
    brenda_file: str,
    max_enzymes_per_class: int = 25,
    max_reactions_per_enzyme: int = 5,
    max_chars_per_class: int = 4000,
) -> dict[str, str]:
    """Return {ec3: text_summary} suitable for injection into RAG prompts."""

    # Collect enzymes per 3-part class
    classes: dict[str, list[dict]] = defaultdict(list)
    total = 0

    for ec_id, data in parse_brenda_entries(brenda_file):
        ec3 = normalize_ec3(ec_id)
        if ec3 is None:
            continue
        total += 1
        if len(classes[ec3]) >= max_enzymes_per_class:
            continue
        classes[ec3].append({
            "ec4":       ec_id,
            "names":     data.get("RECOMMENDED_NAME", [])[:2],
            "systematic": data.get("SYSTEMATIC_NAME",  [])[:1],
            "reactions": data.get("REACTION",          [])[:max_reactions_per_enzyme],
            "types":     data.get("REACTION_TYPE",     [])[:2],
        })
        if total % 1000 == 0:
            print(f"  parsed {total} entries, {len(classes)} EC-3 classes so far …")

    print(f"Parsed {total} BRENDA entries → {len(classes)} EC sub-subclasses")

    # Build text summaries
    index: dict[str, str] = {}
    for ec3, enzymes in classes.items():
        lines = [f"=== EC {ec3} — enzyme sub-subclass information ==="]
        for e in enzymes:
            lines.append(f"\nEC {e['ec4']}:")
            if e["names"]:
                lines.append(f"  Recommended name : {e['names'][0]}")
            if e["systematic"]:
                lines.append(f"  Systematic name  : {e['systematic'][0]}")
            if e["types"]:
                lines.append(f"  Reaction type    : {'; '.join(e['types'])}")
            if e["reactions"]:
                lines.append("  Reactions:")
                for rxn in e["reactions"]:
                    short = rxn[:280] + ("…" if len(rxn) > 280 else "")
                    lines.append(f"    • {short}")

        summary = '\n'.join(lines)
        if len(summary) > max_chars_per_class:
            summary = summary[:max_chars_per_class] + "\n[…truncated]"
        index[ec3] = summary

    return index


def main():
    parser = argparse.ArgumentParser(description="Build BRENDA RAG index")
    parser.add_argument("--brenda_file",
                        default="/data/jarcagniriv/BRENDA/brenda_2026_1.txt")
    parser.add_argument("--output_file",
                        default="/scratch/jarcagniriv/Gemma4EC/chat/data/brenda_index.json")
    parser.add_argument("--max_enzymes_per_class",  type=int, default=25)
    parser.add_argument("--max_reactions_per_enzyme", type=int, default=5)
    parser.add_argument("--max_chars_per_class",    type=int, default=4000)
    args = parser.parse_args()

    print(f"Parsing: {args.brenda_file}")
    index = build_index(
        args.brenda_file,
        args.max_enzymes_per_class,
        args.max_reactions_per_enzyme,
        args.max_chars_per_class,
    )

    Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output_file, 'w', encoding='utf-8') as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2)

    print(f"Saved {len(index)} EC-3 entries → {args.output_file}")


if __name__ == "__main__":
    main()
