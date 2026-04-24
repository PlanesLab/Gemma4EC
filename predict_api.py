
# gemma4ec/predict_api.py

import json
import random
import time
import argparse
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
    # Main prediction loop
    # ------------------------------------------------------------------
    with jsonl_path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            
            if batch_limit is not None and idx >= batch_limit:
                print(f"[api_predict] Reached batch_limit={batch_limit}, stopping.", flush=True)
                break

            if all_wf[idx]:
                print(f"[api_predict] Sample {idx} already done → skipping", flush=True)
                continue

            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            input_text = obj.get("input_text", "")
            label = obj.get("output_text", "")
            true_label = "" if label is None else str(label)
            smiles = extract_smiles_from_input(input_text)

            # API call with retries
            BASE_SLEEP = 2.0
            attempt = 0
            completion = None
            status = None

            while True:
                attempt += 1
                try:
                    print(
                        f"[api_predict] Sample {idx} | attempt {attempt}",
                        flush=True
                    )
                    completion = call_api_model(
                        model_name=model_name,
                        prompt=input_text,
                        max_output_tokens=max_output_tokens,
                    )

                    if completion and completion.strip():
                        break

                except Exception as e:
                    err_low = str(e).lower()
                    print(
                        f"[api_predict] Error at sample {idx} attempt {attempt}: {e}",
                        flush=True
                    )
                    if "gemini_key_exhausted" in err_low:
                        print("[api_predict] Gemini key exhausted, retrying with another key...", flush=True)
                        continue

                    if "all gemini api keys exhausted" in err_low:
                        print(
                            "\n🔴 [api_predict] ALL Gemini API KEYS exhausted.\n"
                            "🛑 Stopping execution safely.\n"
                            "📅 Re-run the same job tomorrow; it will resume automatically.\n",
                            flush=True
                        )

                        write_predictions_tsv(
                            out_path,
                            all_labels,
                            all_preds,
                            all_frags,
                            all_wf,
                            all_smiles,
                            all_attempts,
                            all_status,
                        )
                        return

                sleep_time = BASE_SLEEP * (2 ** min(attempt - 1, 5)) + random.uniform(0, 1)
                print(
                    f"[api_predict] Sleeping {sleep_time:.1f}s before retry",
                    flush=True
                )
                time.sleep(sleep_time)

            # --------------------------------------------------------------
            # Post-retry handling
            # --------------------------------------------------------------
            if not completion:
                status = "RETRY_LATER"
                completion = "error" 

                print(
                    "\n"
                    f"🟡 [api_predict] Sample {idx} could not be resolved today after "
                    f" {attempt} attempts."
                    "ℹ️ This is expected when working under daily API quota constraints.\n"
                    "📅 Re-run the same job tomorrow; execution will resume from this point.\n"
                    "✅ All previous predictions are safely preserved.\n",
                    flush=True
                )
                     
            combined_text = f"Answer: {completion}"
            raw = parse_ec_raw(combined_text)
            frag = leading_ec_fragment(raw)
            wf = is_well_formed_ec(raw)

            if status is None:
                status = "OK" if wf else "ERROR_PARSE"

            all_labels[idx]    = true_label
            all_preds[idx]     = raw
            all_frags[idx]     = frag
            all_wf[idx]        = wf
            all_smiles[idx]    = smiles
            all_attempts[idx] = attempt
            all_status[idx]   = status

            if (idx + 1) % 50 == 0:
                print(f"[api_predict] Processed {idx + 1} samples...", flush=True)

            if (idx + 1) % 10 == 0:
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
                print(f"[api_predict] Checkpoint saved at sample {idx}", flush=True)

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
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_prediction(
        raw_data_file=args.raw_data_file,
        processed_data_folder=args.processed_data_folder,
        output_folder=args.output_folder,
        prompts_json_path=args.prompts_json_path,
        template_key=args.template_key,
        template_alias=args.template_alias,
        model_name=args.model_name,
        max_output_tokens=args.max_output_tokens,
        batch_limit=args.batch_limit,
    )
 