"""
openai_batch_pool.py — Run an OpenAI model on the deduplicated API pool via the OpenAI Batch API
(50% of standard price), under a hard spend cap. Mirrors scripts/gemini_batch_pool.py.

Each unique test reaction of the split set is queried once (data/ECReact_seeds_<SPLIT_SET>/api_pool.csv);
scripts/fanout_api_predictions.py then copies the answers into every seed. Same prompt
(EC_NUMBER_PROMPT_API, few-shot), same request shape as predict_api.py (chat.completions,
default sampling) and same answer parsing.

    SPLIT_SET=strat_dedup python scripts/openai_batch_pool.py submit  --model gpt-4.1-mini [--limit N]
    SPLIT_SET=strat_dedup python scripts/openai_batch_pool.py status  --model gpt-4.1-mini
    SPLIT_SET=strat_dedup python scripts/openai_batch_pool.py collect --model gpt-4.1-mini
    python scripts/openai_batch_pool.py spend [--add_spend 0.08]

Spend guard: `submit` refuses when recorded spend + estimated batch cost (measured tokens/request,
batch prices) would exceed --budget_usd; `collect` records the real cost from each response's usage.
Ledger: ~/.gemma4ec_openai_spend.json. Key: OPENAI_API_KEY (source ~/.gemma4ec_api_keys).
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

SPLIT_SET = os.environ.get("SPLIT_SET", "strat_dedup")
POOL_CSV = ROOT / "data" / f"ECReact_seeds_{SPLIT_SET}" / "api_pool.csv"
TSV_PREFIX = "predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_API."
COLS = ["true_label", "pred_raw", "pred_fragment", "pred_well_formed", "smiles", "n_attempts", "status"]
LEDGER = Path.home() / ".gemma4ec_openai_spend.json"

# Batch prices, USD per 1M tokens (input, output) — developers.openai.com/api/docs/pricing (2026-10-09)
BATCH_PRICES = {"gpt-4.1-mini": (0.20, 0.80), "gpt-4.1-nano": (0.05, 0.20), "gpt-6-luna": (0.05, 0.25)}
# Measured on 10 pool prompts (2026-10-09): input ~534 tokens; output tokens per request
MEASURED_OUT = {"gpt-4.1-mini": 5, "gpt-4.1-nano": 5, "gpt-6-luna": 1055}


def client():
    from openai import OpenAI
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("No OPENAI_API_KEY: source ~/.gemma4ec_api_keys")
    return OpenAI()


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
    return pool_dir / f"{TSV_PREFIX}{safe}.tsv", pool_dir / f"openai_batch_{safe}.json"


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
    if state_path.exists() and json.loads(state_path.read_text()).get("state") != "collected":
        sys.exit(f"A batch is already pending for {args.model}: run status/collect first ({state_path})")
    cur = load_pool_tsv(tsv, len(pool))
    todo = [i for i in range(len(pool)) if cur.at[i, "pred_well_formed"].lower() != "true"]
    if args.limit:
        todo = todo[: args.limit]
    if not todo:
        sys.exit("Nothing left to predict.")

    p_in, p_out = BATCH_PRICES[args.model]
    est = len(todo) * (534 * p_in + MEASURED_OUT[args.model] * p_out) / 1e6
    spent = ledger()["spent_usd"]
    print(f"[submit] {len(todo)} requests, estimated ${est:.2f}; spent so far ${spent:.2f}; budget ${args.budget_usd:.2f}")
    if spent + est > args.budget_usd:
        sys.exit("[submit] REFUSED: would exceed the budget. Use --limit to submit fewer requests.")

    tpl = json.load(open(ROOT / "prompts" / "prompts.json"))["EC_NUMBER_PROMPT_API"]
    jsonl = state_path.with_suffix(".input.jsonl")
    with open(jsonl, "w") as f:
        for i in todo:
            f.write(json.dumps({"custom_id": f"Q{i}", "method": "POST", "url": "/v1/chat/completions",
                                "body": {"model": args.model, "messages": [
                                    {"role": "user", "content": tpl.format(reaction_smiles=pool.at[i, "rxn_smiles"])}]}}) + "\n")
    c = client()
    up = c.files.create(file=open(jsonl, "rb"), purpose="batch")
    job = c.batches.create(input_file_id=up.id, endpoint="/v1/chat/completions", completion_window="24h",
                           metadata={"project": f"gemma4ec_{SPLIT_SET}_{args.model}"})
    state_path.write_text(json.dumps({"job": job.id, "model": args.model, "n": len(todo), "estimate_usd": est,
                                      "state": job.status}, indent=1))
    print(f"[submit] batch {job.id} created ({job.status}); state -> {state_path}")


def status(args):
    _, state_path = paths(args.work_root, args.model)
    st = json.loads(state_path.read_text())
    c = client()
    job = c.batches.retrieve(st["job"])
    print(f"{st['job']}: {job.status}  counts={job.request_counts}")
    return job


def collect(args):
    pool = pd.read_csv(POOL_CSV, dtype=str)
    tsv, state_path = paths(args.work_root, args.model)
    st = json.loads(state_path.read_text())
    c = client()
    job = c.batches.retrieve(st["job"])
    if job.status != "completed":
        sys.exit(f"Batch not finished: {job.status}")
    cur = load_pool_tsv(tsv, len(pool))
    p_in, p_out = BATCH_PRICES[args.model]
    tok_in = tok_out = n_ok = n_err = 0
    lines = c.files.content(job.output_file_id).text.splitlines() if job.output_file_id else []
    for line in lines:
        rec = json.loads(line)
        i = int(rec["custom_id"][1:])
        body = (rec.get("response") or {}).get("body") or {}
        if not body.get("choices"):
            n_err += 1
            continue
        u = body.get("usage", {})
        tok_in += u.get("prompt_tokens", 0)
        tok_out += u.get("completion_tokens", 0)
        text = body["choices"][0]["message"].get("content") or ""
        pred = parse_ec_raw(f"Answer: {text}")
        wf = is_well_formed_ec(pred)
        cur.loc[i, COLS] = [pool.at[i, "ec"], pred, leading_ec_fragment(pred), str(wf),
                            pool.at[i, "rxn_smiles"], "1", "OK" if wf else "ERROR_PARSE"]
        n_ok += 1
    if job.error_file_id:
        n_err += len(c.files.content(job.error_file_id).text.splitlines())
    cur[COLS].to_csv(tsv, sep="\t", index=False)
    cost = (tok_in * p_in + tok_out * p_out) / 1e6
    total = add_spend(cost, f"batch {st['job']} ({args.model}, {n_ok} responses)")
    st["state"] = "collected"
    state_path.write_text(json.dumps(st, indent=1))
    done = (cur["pred_well_formed"].str.lower() == "true").sum()
    print(f"[collect] {n_ok} responses ({n_err} errors); cost ${cost:.2f}; total spent ${total:.2f}; "
          f"{done}/{len(pool)} well-formed -> {tsv.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["submit", "status", "collect", "spend"])
    ap.add_argument("--model", default="gpt-4.1-mini", choices=sorted(BATCH_PRICES))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--budget_usd", type=float, default=4.80, help="Hard cap on total recorded OpenAI spend.")
    ap.add_argument("--work_root", type=Path, default=Path(os.environ.get("GEMMA4EC_WORK", "work")) / f"seeds_{SPLIT_SET}")
    ap.add_argument("--add_spend", type=float, default=None)
    args = ap.parse_args()
    if args.action == "spend":
        if args.add_spend is not None:
            add_spend(args.add_spend, "manual entry")
        print(json.dumps(ledger(), indent=1))
        return
    {"submit": submit, "status": status, "collect": collect}[args.action](args)


if __name__ == "__main__":
    main()
