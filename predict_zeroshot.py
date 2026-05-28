"""
predict_zeroshot.py — Zero-shot EC number prediction with base TxGemma (no adapter).

Predictions that are not in the required x.xx.xx format are retried up to
--max_retries times before being marked as INVALID.

Usage:
    python predict_zeroshot.py \
        --test_csv data/ECReact/test.csv \
        --wandb_entity miramon_team
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import pandas as pd
import torch
import wandb
from accelerate import Accelerator

from src.models.modeling import build_model_and_tokenizer
from src.evaluation.eval import parse_ec_raw
from src.utils.metrics import compute_classification_metrics, is_valid_ec
from src.datamod.templates import build_input_template_from_file

os.environ.setdefault("WORLD_SIZE", "1")
os.environ.setdefault("RANK", "0")
os.environ.setdefault("LOCAL_RANK", "0")
os.environ.setdefault("MASTER_ADDR", "localhost")
os.environ.setdefault("MASTER_PORT", "12355")


def generate_single(model, tokenizer, prompt: str, device, do_sample: bool = False) -> str:
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1280).to(device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=10,
            do_sample=do_sample,
            temperature=0.7 if do_sample else 1.0,
            synced_gpus=False,
        )
    decoded = tokenizer.decode(out[0], skip_special_tokens=True)
    return parse_ec_raw(decoded)


def predict_with_retry(
    model,
    tokenizer,
    prompts: list[str],
    device,
    batch_size: int,
    max_retries: int,
) -> tuple[list[str], list[int], list[str]]:
    """
    Batch inference with per-sample retry for malformed outputs.

    Returns:
        predictions  — final EC prediction per sample (or 'INVALID')
        n_attempts   — number of generation attempts per sample
        status       — 'ok' | 'retry_ok' | 'invalid'
    """
    n = len(prompts)
    predictions = [""] * n
    n_attempts  = [0]  * n
    status      = [""] * n

    # ---- pass 1: batch inference ----
    for start in range(0, n, batch_size):
        batch_prompts = prompts[start : start + batch_size]
        inputs = tokenizer(
            batch_prompts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=1280,
        ).to(device)
        with torch.no_grad():
            outputs = model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=10,
                do_sample=False,
                synced_gpus=False,
            )
        decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)
        for i, text in enumerate(decoded):
            idx = start + i
            predictions[idx] = parse_ec_raw(text)
            n_attempts[idx] = 1

    # ---- pass 2: retry malformed predictions individually ----
    malformed = [i for i, p in enumerate(predictions) if not is_valid_ec(p)]
    if malformed:
        print(f"  [retry] {len(malformed)}/{n} predictions malformed — retrying ...")

    for idx in malformed:
        raw = predictions[idx]
        for attempt in range(2, max_retries + 2):
            raw = generate_single(model, tokenizer, prompts[idx], device, do_sample=True)
            n_attempts[idx] = attempt
            if is_valid_ec(raw):
                predictions[idx] = raw
                break
        else:
            # exhausted retries — keep last attempt (may still be invalid)
            predictions[idx] = raw

    for i, p in enumerate(predictions):
        if is_valid_ec(p):
            status[i] = "ok" if n_attempts[i] == 1 else "retry_ok"
        else:
            status[i] = "invalid"
            predictions[i] = "INVALID"

    return predictions, n_attempts, status


def run_partition(args, prompt_template: str, accelerator: Accelerator, model, tokenizer):
    test_csv = Path(args.test_csv)
    if not test_csv.exists():
        print(f"[warn] {test_csv} not found — skipping.")
        return

    df = pd.read_csv(test_csv)
    smiles_list = df["rxn_smiles"].astype(str).str.strip().tolist()
    true_labels = df["ec"].astype(str).tolist() if "ec" in df.columns else [""] * len(df)
    partition = test_csv.stem  # used for logging/output naming (e.g. "test")

    prompts = [prompt_template.format(reaction_smiles=s) for s in smiles_list]

    print(f"\n[{partition}] Running zero-shot inference on {len(prompts)} test samples ...")
    t0 = time.time()

    predictions, n_attempts, status = predict_with_retry(
        model, tokenizer, prompts,
        device=accelerator.device,
        batch_size=args.eval_batch_size,
        max_retries=args.max_retries,
    )

    elapsed = time.time() - t0
    n_ok      = status.count("ok")
    n_retry   = status.count("retry_ok")
    n_invalid = status.count("invalid")
    valid_rate = (n_ok + n_retry) / max(1, len(predictions))

    print(f"  Elapsed    : {elapsed:.1f}s")
    print(f"  Valid      : {n_ok + n_retry}/{len(predictions)} ({valid_rate:.1%})")
    print(f"    on 1st try : {n_ok}")
    print(f"    after retry: {n_retry}")
    print(f"  Invalid    : {n_invalid}")

    # ---- metrics (only on valid predictions) ----
    valid_mask = [s != "invalid" for s in status]
    valid_preds  = [p for p, v in zip(predictions, valid_mask) if v]
    valid_labels = [l for l, v in zip(true_labels, valid_mask) if v]

    metrics = {}
    if any(l not in ("", "nan", "none") for l in valid_labels) and valid_preds:
        metrics = compute_classification_metrics(valid_labels, valid_preds)
        print(f"\n{'='*52}")
        print(f"  {partition}  ZERO-SHOT RESULTS (valid predictions only)")
        print(f"{'='*52}")
        print(f"  Accuracy   : {metrics['accuracy']:.4f}")
        print(f"  F1 macro   : {metrics['f1_macro']:.4f}")
        print(f"  F1 weighted: {metrics['f1_weighted']:.4f}")
        print(f"  MCC        : {metrics['mcc']:.4f}")
        print(f"  Valid rate : {valid_rate:.1%}  ({n_ok} first-try, {n_retry} retry, {n_invalid} invalid)")
        print(f"{'='*52}\n")

    # ---- W&B ----
    if wandb.run is not None:
        log = {
            f"{partition}/valid_rate":   valid_rate,
            f"{partition}/n_invalid":    n_invalid,
            f"{partition}/n_retry_ok":   n_retry,
            f"{partition}/n_first_try":  n_ok,
        }
        if metrics:
            log.update({
                f"{partition}/accuracy":    metrics["accuracy"],
                f"{partition}/f1_macro":    metrics["f1_macro"],
                f"{partition}/f1_weighted": metrics["f1_weighted"],
                f"{partition}/mcc":         metrics["mcc"],
            })
            for key in ("accuracy", "f1_macro", "f1_weighted", "mcc"):
                wandb.run.summary[f"{partition}/best_{key}"] = metrics[key]
        wandb.log(log)

    # ---- save TSV ----
    out_dir = Path(args.output_folder)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = wandb.run.id if wandb.run else time.strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"zeroshot_{partition}_{run_id}.tsv"
    pd.DataFrame({
        "true_label":  true_labels,
        "pred":        predictions,
        "n_attempts":  n_attempts,
        "status":      status,
        "smiles":      smiles_list,
    }).to_csv(out_path, sep="\t", index=False)
    print(f"  Saved → {out_path}")

    if wandb.run is not None:
        art = wandb.Artifact(f"zeroshot_{partition}_{run_id}", type="predictions")
        art.add_file(str(out_path))
        wandb.log_artifact(art)


def main():
    args = parse_args()
    accelerator = Accelerator()

    # Load prompt template from prompts.json
    template_dict = build_input_template_from_file(
        template_path=args.prompts_json_path,
        key=args.template_key,
        required_vars={"reaction_smiles"},
        dict_key=args.template_alias,
    )
    prompt_template = next(iter(template_dict.values()))

    # W&B
    if accelerator.is_main_process and not args.disable_wandb:
        run_name = f"zeroshot_{args.model_id.split('/')[-1]}_{time.strftime('%m%d_%H%M')}"
        try:
            wandb.init(
                project=args.wandb_project,
                entity=args.wandb_entity,
                name=run_name,
                group="zeroshot",
                tags=["zeroshot", "TxGemma", args.template_key],
                job_type="predict",
                config={
                    "model_id":     args.model_id,
                    "max_retries":  args.max_retries,
                    "test_csv":     args.test_csv,
                    "template_key": args.template_key,
                    "batch_size":   args.eval_batch_size,
                },
            )
        except Exception as e:
            print(f"[predict] W&B init failed ({e}). Continuing without logging.")
    elif accelerator.is_main_process:
        print("[predict] W&B disabled.")

    # Load base model (no adapter)
    print(f"[predict] Loading base model: {args.model_id}")
    model, tokenizer = build_model_and_tokenizer(
        args.model_id, args.save_directory, args.cache_dir
    )
    model.eval()
    model = model.to(accelerator.device)

    run_partition(args, prompt_template, accelerator, model, tokenizer)

    if accelerator.is_main_process and wandb.run is not None:
        wandb.finish()
    print("\n[predict] All partitions done.")


def parse_args():
    ap = argparse.ArgumentParser(
        description="Zero-shot EC prediction with base TxGemma (no adapter). "
                    "Retries malformed outputs up to --max_retries times.",
        allow_abbrev=False,
    )
    ap.add_argument("--test_csv", type=str,
                    default="./data/ECReact/test.csv",
                    help="CSV file with rxn_smiles (and optionally ec) columns. "
                         "(default: ./data/ECReact/test.csv)")
    ap.add_argument("--output_folder", type=str,
                    default="./outputs/zeroshot",
                    help="Folder to save prediction TSVs. (default: ./outputs/zeroshot)")
    ap.add_argument("--prompts_json_path", type=str,
                    default="./prompts/prompts.json",
                    help="Path to prompts.json. (default: ./prompts/prompts.json)")
    ap.add_argument("--template_key", type=str,
                    default="EC_NUMBER_PROMPT_API",
                    help="Prompt key in prompts.json. (default: EC_NUMBER_PROMPT_API)")
    ap.add_argument("--template_alias", type=str,
                    default="EC_NUMBER",
                    help="Internal alias for the template. (default: EC_NUMBER)")
    ap.add_argument("--model_id", type=str,
                    default="google/txgemma-9b-predict",
                    help="Base TxGemma model ID. (default: google/txgemma-9b-predict)")
    ap.add_argument("--save_directory", type=str,
                    default="./local_txgemma_model",
                    help="Where to cache the downloaded base model. (default: ./local_txgemma_model)")
    ap.add_argument("--cache_dir", type=str,
                    default="./hfcache",
                    help="HuggingFace cache directory. (default: ./hfcache)")
    ap.add_argument("--eval_batch_size", type=int, default=16,
                    help="Batch size for generation. (default: 16)")
    ap.add_argument("--max_retries", type=int, default=5,
                    help="Max retries per sample if prediction is malformed. (default: 5)")
    ap.add_argument("--hf_token", type=str, default=None,
                    help="HuggingFace access token.")
    ap.add_argument("--wandb_project", type=str, default="Gemma4EC-partitions",
                    help="W&B project. (default: Gemma4EC-partitions)")
    ap.add_argument("--wandb_entity", type=str, default=None,
                    help="W&B entity (username or team). Required if W&B is enabled.")
    ap.add_argument("--disable_wandb", action="store_true",
                    help="Disable W&B logging.")
    return ap.parse_args()


if __name__ == "__main__":
    main()
