#!/usr/bin/env python3
"""
slim_bertviz.py — trim existing bertviz HTML files to show only SMILES tokens
and the predicted EC tokens (last layer, no GPU needed).

Reads summary.tsv for the smiles_tok_start / total_tokens span of each
reaction, slices the embedded attention matrix accordingly, and overwrites
each rxnNN_bertviz.html in place.

Usage:
    cd /scratch/jarcagniriv/Gemma4EC
    python slim_bertviz.py
    python slim_bertviz.py --attn_dir attn_out --summary attn_out/summary.tsv
"""

import argparse
import csv
import json
from pathlib import Path


def load_summary(tsv_path: Path) -> dict[int, dict]:
    rows = {}
    with open(tsv_path) as f:
        for row in csv.DictReader(f, delimiter="\t"):
            rxn = int(row["reaction"])
            rows[rxn] = {
                "smiles_start": int(row["smiles_tok_start"]) if row["smiles_tok_start"] != "None" else None,
                "total_tokens": int(row["total_tokens"]),
            }
    return rows


def slim_html(path: Path, tok_start: int, tok_end: int) -> None:
    mb = path.stat().st_size / 1024 / 1024
    n_show = tok_end - tok_start
    print(f"  {path.name}  ({mb:.0f} MB)  tok [{tok_start}:{tok_end}] …", end=" ", flush=True)

    text = path.read_text(encoding="utf-8")

    marker = "const params = "
    idx = text.find(marker)
    if idx == -1:
        print("SKIP — marker not found")
        return

    json_start = idx + len(marker)
    decoder = json.JSONDecoder()
    try:
        params, json_end = decoder.raw_decode(text, json_start)
    except json.JSONDecodeError as exc:
        print(f"SKIP — JSON parse error: {exc}")
        return

    for entry in params["attention"]:
        attn = entry["attn"]      # [layers][heads][from][to]

        # Keep last layer only; slice to [tok_start:tok_end]; round to 4 d.p.
        last = attn[-1]           # [heads][from][to]
        trunc = [
            [
                [round(v, 4) for v in row[tok_start:tok_end]]
                for row in head[tok_start:tok_end]
            ]
            for head in last
        ]
        entry["attn"]       = [trunc]
        entry["left_text"]  = entry["left_text"][tok_start:tok_end]
        entry["right_text"] = entry["right_text"][tok_start:tok_end]

    # Also update include_layers to reflect the single layer we're keeping
    params["include_layers"] = [0]

    new_json = json.dumps(params, separators=(",", ":"))

    # bertviz embeds PYTHON_PARAMS twice on one line:
    #   const params = {JSON}; // HACK: {JSON} is a template marker ...
    hack_prefix = "; // HACK: "
    if text[json_end: json_end + len(hack_prefix)] == hack_prefix:
        hack_start = json_end + len(hack_prefix)
        _, hack_end = decoder.raw_decode(text, hack_start)
        new_text = text[:json_start] + new_json + hack_prefix + new_json + text[hack_end:]
    else:
        new_text = text[:json_start] + new_json + text[json_end:]

    path.write_text(new_text, encoding="utf-8")
    new_kb = len(new_text.encode()) / 1024
    print(f"done  →  {new_kb:.0f} KB  ({n_show} tokens)")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--attn_dir", default="./attn_out")
    p.add_argument("--summary",  default="./attn_out/summary.tsv")
    args = p.parse_args()

    out_dir = Path(args.attn_dir)
    summary = load_summary(Path(args.summary))

    files = sorted(out_dir.glob("*_bertviz.html"))
    if not files:
        print(f"No *_bertviz.html files found in {out_dir}")
        return

    print(f"Trimming {len(files)} files to SMILES + EC tokens (last layer)\n")
    for path in files:
        stem    = path.stem.replace("_bertviz", "")          # "rxn01"
        rxn_num = int("".join(c for c in stem if c.isdigit()))

        info = summary.get(rxn_num)
        if info is None:
            print(f"  {path.name}  SKIP — not in summary.tsv")
            continue

        tok_start = info["smiles_start"]
        tok_end   = info["total_tokens"]

        if tok_start is None:
            print(f"  {path.name}  SKIP — smiles_tok_start is None")
            continue

        slim_html(path, tok_start, tok_end)

    print("\nDone.  Open the HTML files in any browser.")


if __name__ == "__main__":
    main()
