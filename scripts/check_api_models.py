"""
check_api_models.py — Verify that API model IDs exist for the current keys,
and list the newest available IDs so the seed benchmark can be updated.

Usage:
    python scripts/check_api_models.py gpt-5.2 gemini-3.8-flash ...
    python scripts/check_api_models.py --list
Exit code 1 if any requested model is unavailable.
"""

import argparse
import os
import sys


def openai_ids():
    from openai import OpenAI
    return sorted(m.id for m in OpenAI(api_key=os.environ["OPENAI_API_KEY"]).models.list())


def gemini_ids():
    from google import genai
    key = (os.environ.get("GEMINI_API_KEYS", "").split(",")[0].strip()
           or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    client = genai.Client(api_key=key)  # keep a reference: the pager needs an open client
    return sorted(m.name.removeprefix("models/") for m in client.models.list())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="*")
    ap.add_argument("--list", action="store_true", help="Print GPT / Gemini model IDs available to these keys.")
    args = ap.parse_args()

    available = {}
    if args.list or any(not m.startswith("gemini-") for m in args.models):
        available["openai"] = set(openai_ids())
    if args.list or any(m.startswith("gemini-") for m in args.models):
        available["gemini"] = set(gemini_ids())

    if args.list:
        for provider, ids in available.items():
            keep = [i for i in sorted(ids) if i.startswith(("gpt-", "gemini-"))]
            print(f"== {provider} ({len(keep)}) ==")
            print("\n".join(keep))

    missing = [m for m in args.models
               if m not in available["gemini" if m.startswith("gemini-") else "openai"]]
    for m in args.models:
        print(f"{'OK     ' if m not in missing else 'MISSING'} {m}")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
