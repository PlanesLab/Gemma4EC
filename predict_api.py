
# gemma4ec/predict_api.py

import json
import random
import time
import argparse
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import pandas as pd
from typing import Optional, List

from src.evaluation.eval import parse_ec_raw, leading_ec_fragment, is_well_formed_ec
from src.predict_utils.common import (
    build_jsonl_from_raw,
    extract_smiles_from_input,
    write_predictions_tsv,
    call_api_model
)

def run_prediction(
    raw_data_file: str,
    processed_data_folder: str,
    output_folder: str,
    prompts_json_path: str,
    template_key: str,
    template_alias: str,
    model_name: str,
    max_output_tokens: Optional[int] = None,
    batch_limit: Optional[int] = None,
    workers: int = 1,
    max_attempts: int = 8,
    min_interval: float = 0.0,
):
    """
    1) Generates the JSONL from the CSV, using the same logic as Gemma4EC.
    2) Reads that JSONL and calls the chosen API model (OpenAI or Gemini) using input_text.
    3) Parses the responses with parse_ec_raw / leading_ec_fragment / is_well_formed_ec.
    4) Writes a TSV with the columns:
       [true_label, pred_raw, pred_fragment, pred_well_formed, smiles]
    """
    # ------------------------------------------------------------------
    # Build JSONL (same logic as local Gemma4EC prediction)
    # ------------------------------------------------------------------
    jsonl_path = Path(
        build_jsonl_from_raw(
            raw_data_file=raw_data_file,
            processed_data_folder=processed_data_folder,
            prompts_json_path=prompts_json_path,
            template_key=template_key,
            template_alias=template_alias,
        )
    )

    out_dir = Path(output_folder)
    out_dir.mkdir(parents=True, exist_ok=True)

    # We try to imitate the naming from evaluate_model
    # predict.EC_NUMBER_PROMPT_2.EC_NUMBER.jsonl
    #  -> split="pred", key="EC_NUMBER_PROMPT_2", alias="EC_NUMBER"
    stem_parts = jsonl_path.stem.split(".")
    if len(stem_parts) >= 3 and stem_parts[0] == "predict":
        split = "pred"
        key = stem_parts[1]
        alias = stem_parts[2]
    else:
        split = "pred"
        key = template_key
        alias = template_alias

    safe_model_name = model_name.replace(".", "_")
    out_name = f"predictions_{split}.{alias}.{key}.{safe_model_name}.tsv"
    out_path = out_dir / out_name

    print(f"[api_predict] Reading JSONL: {jsonl_path}")
    print(f"[api_predict] Writing TSV to: {out_path}")
    print(f"[api_predict] API model: {model_name}")

    # ------------------------------------------------------------------
    # Load JSONL length (number of samples)
    # ------------------------------------------------------------------
    with jsonl_path.open("r", encoding="utf-8") as f:
        num_samples = sum(1 for _ in f)

    # ------------------------------------------------------------------
    # Initialize full buffers (state = TSV)
    # ------------------------------------------------------------------
    def init_list(default):
        return [default] * num_samples

    all_labels    = init_list("")
    all_preds     = init_list("")
    all_frags     = init_list("")
    all_wf        = init_list(False)
    all_smiles    = init_list("")
    all_attempts  = init_list(0)
    all_status    = init_list("")

    # ------------------------------------------------------------------
    # Rehydrate from existing TSV if present
    # ------------------------------------------------------------------
    if out_path.exists():
        print(f"[api_predict] Resuming from existing TSV: {out_path}", flush=True)
        df_prev = pd.read_csv(out_path, sep="\t")

        for idx, row in df_prev.iterrows():
            if idx >= num_samples:
                continue
            all_labels[idx]    = row["true_label"]
            all_preds[idx]     = row["pred_raw"]
            all_frags[idx]     = row["pred_fragment"]
            all_wf[idx]        = bool(row["pred_well_formed"])
            all_smiles[idx]    = row["smiles"]
            all_attempts[idx]  = int(row["n_attempts"])
            all_status[idx]    = row["status"]

    # ------------------------------------------------------------------
    # Main prediction loop (thread pool; one API call per sample)
    # ------------------------------------------------------------------
    with jsonl_path.open("r", encoding="utf-8") as f:
        samples = [json.loads(line) if line.strip() else None for line in f]

    pending = [
        idx for idx, obj in enumerate(samples)
        if obj is not None and not all_wf[idx]
        and (batch_limit is None or idx < batch_limit)
    ]
    print(f"[api_predict] {sum(all_wf)} samples already done, "
          f"{len(pending)} pending, workers={workers}", flush=True)

    BASE_SLEEP = 2.0
    lock = threading.Lock()
    stop_event = threading.Event()
    fatal = []
    n_done = 0
    rate_lock = threading.Lock()
    next_slot = [0.0]

    def wait_for_slot():
        # Global spacing between request starts (free-tier requests-per-minute limits)
        if min_interval <= 0:
            return
        with rate_lock:
            now = time.monotonic()
            start = max(now, next_slot[0])
            next_slot[0] = start + min_interval
        time.sleep(max(0.0, start - now))

    def checkpoint():
        write_predictions_tsv(
            out_path, all_labels, all_preds, all_frags, all_wf,
            all_smiles, all_attempts, all_status,
        )

    def predict_one(idx: int):
        obj = samples[idx]
        input_text = obj.get("input_text", "")
        label = obj.get("output_text", "")
        true_label = "" if label is None else str(label)
        smiles = extract_smiles_from_input(input_text)

        completion = None
        attempt = 0
        while attempt < max_attempts and not stop_event.is_set():
            attempt += 1
            try:
                wait_for_slot()
                completion = call_api_model(
                    model_name=model_name,
                    prompt=input_text,
                    max_output_tokens=max_output_tokens,
                )
                if completion and completion.strip():
                    break
            except Exception as e:
                err_low = str(e).lower()
                print(f"[api_predict] Error at sample {idx} attempt {attempt}: {e}", flush=True)
                if "gemini_key_exhausted" in err_low:
                    continue
                if "no credits remaining" in err_low or "insufficient_quota" in err_low:
                    print("\n🔴 [api_predict] Account has no credit — stopping (not retried).\n", flush=True)
                    fatal.append("no_credit")
                    stop_event.set()
                    return
                if "all gemini api keys exhausted" in err_low or "openai_daily_cap_reached" in err_low:
                    print("\n🔴 [api_predict] Daily free quota exhausted. Stopping; "
                          "re-run the same job to resume.\n", flush=True)
                    stop_event.set()
                    return
            time.sleep(BASE_SLEEP * (2 ** min(attempt - 1, 5)) + random.uniform(0, 1))

        if stop_event.is_set() and not completion:
            return

        status = None
        if not completion:
            # Left not well-formed → retried automatically on the next run.
            status = "RETRY_LATER"
            completion = "error"

        raw = parse_ec_raw(f"Answer: {completion}")
        frag = leading_ec_fragment(raw)
        wf = is_well_formed_ec(raw)
        if status is None:
            status = "OK" if wf else "ERROR_PARSE"

        nonlocal n_done
        with lock:
            all_labels[idx]   = true_label
            all_preds[idx]    = raw
            all_frags[idx]    = frag
            all_wf[idx]       = wf
            all_smiles[idx]   = smiles
            all_attempts[idx] = attempt
            all_status[idx]   = status
            n_done += 1
            if n_done % 50 == 0:
                print(f"[api_predict] Processed {n_done}/{len(pending)} pending samples", flush=True)
                checkpoint()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for fut in as_completed([pool.submit(predict_one, i) for i in pending]):
            fut.result()
    quota_stopped = stop_event.is_set()

    # ------------------------------------------------------------------
    # Final write
    # ------------------------------------------------------------------
    write_predictions_tsv(
        out_path,
        all_labels,
        all_preds,
        all_frags,
        all_wf,
        all_smiles,
        all_attempts,
        all_status
    )
    if fatal:
        return "fatal"
    return "quota" if quota_stopped else "done"

def parse_args():
    parser = argparse.ArgumentParser(
        description="Predict EC numbers using OpenAI or Gemini models on Gemma4EC JSONL (input_text/output_text).",
        allow_abbrev=False,
    )
    # Paths
    parser.add_argument("--raw_data_file", type=str, required=True, help="CSV file with the raw reactions to predict on.")
    parser.add_argument("--processed_data_folder", type=str, required=True, help="Directory where the intermediate JSONL files will be written.")
    parser.add_argument("--output_folder", type=str, required=True, help="Directory where the TSV predictions will be written.")

    # Prompts
    parser.add_argument("--prompts_json_path", type=str, required=True, help="Path to prompts.json containing your templates.")
    parser.add_argument("--template_key", type=str, default="EC_NUMBER_PROMPT_2", help="Key in prompts.json to use (default: EC_NUMBER_PROMPT_2).")
    parser.add_argument("--template_alias", type=str, default="EC_NUMBER", help="Dictionary key to expose to your pipeline (default: EC_NUMBER).")

    # Model (OpenAI or Gemini)
    parser.add_argument("--model_name",type=str, required=True, help="Model name, e.g. 'gpt-5-mini', 'gpt-5.1', 'gemini-3.5-pro', 'gemini-2.5-flash'.")
    parser.add_argument("--max_output_tokens", type=int, default=None, help="Optional: override max output tokens. If None, model default is used.")
    parser.add_argument("--batch_limit", type=int, default=None, help="Optional: limit number of samples to process, for quick tests.")
    parser.add_argument("--workers", type=int, default=1, help="Concurrent API requests (default: 1).")
    parser.add_argument("--min_interval", type=float, default=0.0, help="Minimum seconds between API requests across all workers (e.g. 6 for a 10 RPM free tier).")
    parser.add_argument("--max_attempts", type=int, default=8, help="Attempts per sample before marking RETRY_LATER (retried on the next run).")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    outcome = run_prediction(
        raw_data_file=args.raw_data_file,
        processed_data_folder=args.processed_data_folder,
        output_folder=args.output_folder,
        prompts_json_path=args.prompts_json_path,
        template_key=args.template_key,
        template_alias=args.template_alias,
        model_name=args.model_name,
        max_output_tokens=args.max_output_tokens,
        batch_limit=args.batch_limit,
        workers=args.workers,
        max_attempts=args.max_attempts,
        min_interval=args.min_interval,
    )
    if outcome == "fatal":
        sys.exit(4)  # e.g. no API credit: do not re-submit
    if outcome == "quota":
        sys.exit(3)  # daily free quota exhausted → caller re-submits after the reset
