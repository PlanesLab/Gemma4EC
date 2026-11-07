#!/usr/bin/env python3
"""Rate a rating sheet with an LLM judge (OpenAI, or Gemini via its OpenAI-compatible endpoint).

The judge sees the rubric (<sheet_dir>/README.md) and one item at a time, never KEY.csv.
Writes <sheet_dir>/ratings_<model>.csv (resumable), same columns as ratings.csv.
Usage: source ~/.gemma4ec_api_keys
       python chat/eval/llm_rate.py chat/eval/ratings [--model gpt-4.1|gemini-3.8-flash] [--items I001]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

RUBRIC = ["mechanism_correct", "enzyme_plausible", "contradicts_reaction", "unverifiable_detail", "useful"]


def system_prompt(keys):
    return ("You are an expert enzymologist rating machine-written explanations of enzyme reactions. "
            "Judge only what the item shows (it tells you whether the true EC number is given), and follow the "
            "rubric and its anchors exactly. Answer with a JSON object with the keys " + ", ".join(keys) +
            " (integers 0-2) and notes (a short string: anything wrong the scores do not capture).")


def items(sheet):
    parts = re.split(r"^## (I\d+)\s*$", sheet.read_text(), flags=re.M)
    return {parts[i]: parts[i + 1].strip().rstrip("-").strip() for i in range(1, len(parts), 2)}


def rate(client, model, rubric, item_id, text):
    # reasoning models (gpt-5*, o*) take no temperature; the others are run greedy
    greedy = {} if model.startswith(("gpt-5", "o3", "o4")) else {"temperature": 0}
    r = client.chat.completions.create(
        model=model, response_format={"type": "json_object"}, **greedy,
        messages=[{"role": "system", "content": system_prompt(RUBRIC)},
                  {"role": "user", "content": f"RUBRIC\n{rubric}\n\nITEM {item_id}\n{text}"}])
    d = json.loads(r.choices[0].message.content)
    row = {"item_id": item_id, "notes": str(d.get("notes", "")).replace("\n", " ")}
    for k in RUBRIC:
        v = d.get(k)
        row[k] = int(v) if isinstance(v, (int, float)) and v in (0, 1, 2) else None
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet_dir", type=Path)
    ap.add_argument("--model", default="gpt-4.1")
    ap.add_argument("--items", nargs="+", help="only these item ids (for a quick test)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    from openai import OpenAI
    if args.model.startswith("gemini-"):
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or \
            os.environ.get("GEMINI_API_KEYS", "").split(",")[0]
        if not key:
            sys.exit("No Gemini key: source ~/.gemma4ec_api_keys")
        client = OpenAI(api_key=key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
    else:
        if not os.environ.get("OPENAI_API_KEY"):
            sys.exit("No OPENAI_API_KEY: source ~/.gemma4ec_api_keys")
        client = OpenAI()

    rubric = (args.sheet_dir / "README.md").read_text()
    global RUBRIC
    RUBRIC = re.findall(r"^- \*\*(\w+)\*\*", rubric, flags=re.M) or RUBRIC
    todo = items(args.sheet_dir / "sheet.md")
    if args.items:
        todo = {k: v for k, v in todo.items() if k in args.items}
    out = args.out or args.sheet_dir / f"ratings_{args.model}.csv"
    done = pd.read_csv(out, dtype={"item_id": str}) if out.exists() else pd.DataFrame(columns=["item_id"] + RUBRIC + ["notes"])
    rows = done.to_dict("records")
    for item_id, text in todo.items():
        if item_id in set(done.item_id):
            continue
        rows.append(rate(client, args.model, rubric, item_id, text))
        pd.DataFrame(rows)[["item_id"] + RUBRIC + ["notes"]].to_csv(out, index=False)   # save after each item
        print(item_id, {k: rows[-1][k] for k in RUBRIC}, flush=True)
    print(f"{len(rows)} items → {out}")


if __name__ == "__main__":
    main()
