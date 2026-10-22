"""
gemini_batch_pool.py — Run a Gemini model on the deduplicated API pool via the Gemini
Batch API (50% of standard price), under a hard spend cap.

Same prompt as predict_api.py (EC_NUMBER_PROMPT_API, few-shot) and the same answer
parsing; results go into the pool TSV that scripts/fanout_api_predictions.py reads.

    python scripts/gemini_batch_pool.py submit  --model gemini-3.1-flash-lite [--limit N]
    python scripts/gemini_batch_pool.py status  --model gemini-3.1-flash-lite
    python scripts/gemini_batch_pool.py collect --model gemini-3.1-flash-lite

Spend guard: `submit` refuses when recorded spend + the estimated cost of the batch
(measured tokens/request, batch prices) would exceed --budget_usd. `collect` records
the real cost from each response's usage metadata. Ledger: ~/.gemma4ec_gemini_spend.json
Keys are read from GEMINI_API_KEYS / GEMINI_API_KEY (source ~/.gemma4ec_api_keys).
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.evaluation.eval import is_well_formed_ec, leading_ec_fragment, parse_ec_raw  # noqa: E402

SPLIT_SET = os.environ.get("SPLIT_SET", "strat_dedup")  # which seed split set (data/ECReact_seeds_<set>)
POOL_CSV = ROOT / "data" / f"ECReact_seeds_{SPLIT_SET}" / "api_pool.csv"
TSV_PREFIX = "predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API."
COLS = ["true_label", "pred_raw", "pred_fragment", "pred_well_formed", "smiles", "n_attempts", "status"]
LEDGER = Path.home() / ".gemma4ec_gemini_spend.json"

# Batch prices, USD per 1M tokens (input, output incl. thinking) — ai.google.dev/gemini-api/docs/pricing
BATCH_PRICES = {
    "gemini-3.1-flash-lite": (0.125, 0.75),
    "gemini-3.5-flash-lite": (0.15, 1.25),
    "gemini-3.8-flash": (0.375, 1.875),
}
# Measured on 20 pool prompts (2026-09-24): input ≈ 512, answer ≈ 7, thinking tokens per request
MEASURED_OUT = {"gemini-3.1-flash-lite": 7, "gemini-3.5-flash-lite": 7, "gemini-3.8-flash": 944}


def client():
    from google import genai
    key = (os.environ.get("GEMINI_API_KEYS", "").split(",")[0].strip()
           or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    if not key:
        sys.exit("No Gemini key: source ~/.gemma4ec_api_keys")
    return genai.Client(api_key=key)


def ledger():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {"spent_usd": 0.0, "entries": []}


def add_spend(usd, note):
    led = ledger()
    led["spent_usd"] = round(led["spent_usd"] + usd, 4)
    led["entries"].append({"time": time.strftime("%F %T"), "usd": round(usd, 4), "note": note})
    LEDGER.write_text(json.dumps(led, indent=1))
    return led["spent_usd"]


def paths(work_root, model):
    pool_dir = work_root / "api_pool"
    pool_dir.mkdir(parents=True, exist_ok=True)
    safe = model.replace(".", "_")
    return pool_dir / f"{TSV_PREFIX}{safe}.tsv", pool_dir / f"gemini_batch_{safe}.json"


def load_pool_tsv(tsv, n):
    if tsv.exists():
        cur = pd.read_csv(tsv, sep="\t", dtype=str, keep_default_na=False)
        assert len(cur) == n, f"{tsv} row count differs from the pool"
        return cur
    cur = pd.DataFrame({c: [""] * n for c in COLS})
    cur["pred_well_formed"], cur["n_attempts"] = "False", "0"
    return cur


def submit(args):
    pool = pd.read_csv(POOL_CSV, dtype=str)
    tsv, state_path = paths(args.work_root, args.model)
    if state_path.exists() and json.loads(state_path.read_text()).get("state") not in ("collected", None):
        sys.exit(f"A batch is already pending for {args.model}: run status/collect first ({state_path})")
    cur = load_pool_tsv(tsv, len(pool))
    todo = [i for i in range(len(pool)) if cur.at[i, "pred_well_formed"].lower() != "true"]
    if args.limit:
        todo = todo[: args.limit]
    if not todo:
        sys.exit("Nothing left to predict.")

    p_in, p_out = BATCH_PRICES[args.model]
    est = len(todo) * (520 * p_in + MEASURED_OUT[args.model] * p_out) / 1e6
    spent = ledger()["spent_usd"]
    print(f"[submit] {len(todo)} requests, estimated ${est:.2f}; spent so far ${spent:.2f}; budget ${args.budget_usd:.2f}")
    if spent + est > args.budget_usd:
        sys.exit("[submit] REFUSED: would exceed the budget. Use --limit to submit fewer requests.")

    tpl = json.load(open(ROOT / "prompts" / "prompts.json"))["EC_NUMBER_PROMPT_API"]
    jsonl = state_path.with_suffix(".input.jsonl")
    with open(jsonl, "w") as f:
        for i in todo:
            f.write(json.dumps({
                "key": str(i),
                "request": {
                    "contents": [{"role": "user", "parts": [{"text": tpl.format(reaction_smiles=pool.at[i, "rxn_smiles"])}]}],
                    "generation_config": {"temperature": 0.0},
                },
            }) + "\n")

    c = client()
    up = c.files.upload(file=str(jsonl), config={"mime_type": "jsonl", "display_name": jsonl.name})
    job = c.batches.create(model=args.model, src=up.name, config={"display_name": f"gemma4ec_pool_{args.model}"})
    state_path.write_text(json.dumps({"job": job.name, "model": args.model, "n": len(todo),
                                      "estimate_usd": est, "state": str(job.state)}, indent=1))
    print(f"[submit] batch {job.name} created ({job.state}); state → {state_path}")


def status(args):
    _, state_path = paths(args.work_root, args.model)
    st = json.loads(state_path.read_text())
    c = client()  # keep a reference: a temporary client is closed before the request
    job = c.batches.get(name=st["job"])
    print(f"{st['job']}: {job.state}  stats={job.completion_stats}")
    return job


def collect(args):
    pool = pd.read_csv(POOL_CSV, dtype=str)
    tsv, state_path = paths(args.work_root, args.model)
    st = json.loads(state_path.read_text())
    c = client()
    job = c.batches.get(name=st["job"])
    if "SUCCEEDED" not in str(job.state):
        sys.exit(f"Batch not finished: {job.state}")

    raw = c.files.download(file=job.dest.file_name)
    cur = load_pool_tsv(tsv, len(pool))
    p_in, p_out = BATCH_PRICES[args.model]
    tok_in = tok_out = n_ok = n_err = 0
    for line in raw.decode().splitlines():
        rec = json.loads(line)
        i = int(rec["key"])
        resp = rec.get("response")
        if not resp:
            n_err += 1
            continue
        usage = resp.get("usageMetadata", {})
        tok_in += usage.get("promptTokenCount", 0)
        tok_out += usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)
        text = "".join(p.get("text", "") for cand in resp.get("candidates", [])[:1]
                       for p in cand.get("content", {}).get("parts", []) if not p.get("thought"))
        pred = parse_ec_raw(f"Answer: {text}")
        wf = is_well_formed_ec(pred)
        cur.loc[i, COLS] = [pool.at[i, "ec"], pred, leading_ec_fragment(pred), str(wf),
                            pool.at[i, "rxn_smiles"], "1", "OK" if wf else "ERROR_PARSE"]
        n_ok += 1
    cur[COLS].to_csv(tsv, sep="\t", index=False)
    cost = (tok_in * p_in + tok_out * p_out) / 1e6
    total = add_spend(cost, f"batch {st['job']} ({args.model}, {n_ok} responses)")
    st["state"] = "collected"
    state_path.write_text(json.dumps(st, indent=1))
    done = (cur["pred_well_formed"].str.lower() == "true").sum()
    print(f"[collect] {n_ok} responses ({n_err} errors); cost ${cost:.2f}; total spent ${total:.2f}; "
          f"{done}/{len(pool)} well-formed → {tsv.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["submit", "status", "collect", "spend"])
    ap.add_argument("--model", default="gemini-3.1-flash-lite", choices=sorted(BATCH_PRICES))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--budget_usd", type=float, default=5.00, help="Hard cap on total recorded spend (kept below €5).")
    ap.add_argument("--work_root", type=Path, default=Path(os.environ.get("GEMMA4EC_WORK", "work")) / f"seeds_{SPLIT_SET}")
    ap.add_argument("--add_spend", type=float, default=None, help="With 'spend': record spend made outside this script.")
    args = ap.parse_args()
    if args.action == "spend":
        if args.add_spend is not None:
            add_spend(args.add_spend, "manual entry")
        print(json.dumps(ledger(), indent=1))
        return
    {"submit": submit, "status": status, "collect": collect}[args.action](args)


if __name__ == "__main__":
    main()
