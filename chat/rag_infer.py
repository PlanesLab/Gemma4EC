#!/usr/bin/env python3
"""
Hybrid RAG inference for EC number prediction.

Two-stage pipeline
──────────────────
Stage 1  Gemma4EC-Predict (txgemma-9b-predict + LoRA) predicts the EC number
         using the standard EC_NUMBER_PROMPT_2 plain-text format.
Stage 2  Gemma4EC-Chat (txgemma-9b-chat + LoRA) receives the predicted EC,
         retrieves the matching BRENDA sub-subclass entry, and generates a
         mechanistic explanation via a RAG-augmented chat prompt.

The two models are loaded sequentially to avoid OOM on a single GPU node.
The BRENDA index (JSON) is built by chat/build_brenda_index.py.

Usage:
    python chat/rag_infer.py \
        --predict_adapter_dir results/ECReact/results/best \
        --chat_adapter_dir    ./chat/checkpoints/best_model \
        --brenda_index        chat/data/brenda_index.json \
        --input_csv           data/ECReact/test.csv \
        --output_file         ./outputs/rag_predictions.tsv
"""

import gc
import re
import json
import argparse
from pathlib import Path

import torch
import pandas as pd
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# ─────────────────────────── EC helpers ───────────────────────────────────

_EC_RE = re.compile(r'\b(\d+)\.(\d+)\.(\d+)\b')
_ANSWER_MARKER = "Answer:"


def normalize_ec3(ec_str: str) -> str | None:
    """Normalize any EC string to the 3-part non-padded form used as BRENDA keys."""
    parts = ec_str.strip().split('.')
    if len(parts) < 3:
        return None
    try:
        return '.'.join(str(int(p)) for p in parts[:3])
    except ValueError:
        return None


def _parse_ec_raw(decoded: str) -> str:
    """
    Extract EC from predict-model output: take the first line after the last
    'Answer:' marker (matches eval.py parse_ec_raw logic).
    """
    if _ANSWER_MARKER in decoded:
        tail = decoded.rsplit(_ANSWER_MARKER, 1)[-1]
    else:
        tail = decoded
    tail = tail.strip()
    return tail.splitlines()[0].strip() if tail else ""


def _extract_ec_from_text(text: str) -> str | None:
    """Return first EC-like pattern (3-part) found in chat-model generated text."""
    m = _EC_RE.search(text)
    if m:
        return f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    return None


def _format_ec_output(raw: str) -> str:
    """Reformat to zero-padded X.XX.XX form."""
    ec3 = _extract_ec_from_text(raw)
    if ec3 is None:
        return raw.strip()[:20]
    a, b, c = ec3.split('.')
    return f"{a}.{int(b):02d}.{int(c):02d}"


# ─────────────────────────── stage-1 (predict model) ──────────────────────

_PREDICT_PROMPT_TMPL = (
    "Instructions: Given a reaction SMILES, predict the first three parts of its "
    "Enzyme Commission (EC) number (class.subclass.sub-subclass).\n"
    "EC numbers are four-part hierarchical codes (e.g., 1.3.2.4) describing the type "
    "of enzyme and its reaction mechanism.\n"
    "Only output the first three digits (e.g., 1.03.02) representing the enzyme's "
    "general class, subclass, and sub-subclass.\n"
    "Reaction SMILES: {reaction_smiles}\n"
    "Answer:"
)


def _build_predict_prompt(smiles: str) -> str:
    return _PREDICT_PROMPT_TMPL.format(reaction_smiles=smiles)


def _run_predict_stage(
    smiles_list: list[str],
    predict_base_id: str,
    predict_adapter_dir: str,
    batch_size: int,
    hf_token: str | None,
    device: str,
) -> list[str]:
    """Load predict model, run stage-1 inference, unload before returning."""
    print(f"[stage-1] Loading tokenizer: {predict_base_id}")
    tok = AutoTokenizer.from_pretrained(
        predict_base_id, trust_remote_code=True, token=hf_token
    )
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"

    print(f"[stage-1] Loading base model: {predict_base_id}")
    base = AutoModelForCausalLM.from_pretrained(
        predict_base_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        token=hf_token,
    )
    print(f"[stage-1] Loading LoRA adapter: {predict_adapter_dir}")
    model = PeftModel.from_pretrained(base, predict_adapter_dir)
    model.eval()

    ec_preds = []
    for i in tqdm(range(0, len(smiles_list), batch_size), desc="stage-1 predict"):
        batch = smiles_list[i: i + batch_size]
        prompts = [_build_predict_prompt(s) for s in batch]
        enc = tok(
            prompts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=1280,
        ).to(device)

        with torch.no_grad():
            out = model.generate(
                **enc,
                max_new_tokens=8,
                do_sample=False,
                pad_token_id=tok.pad_token_id,
            )

        decoded = tok.batch_decode(out, skip_special_tokens=True)
        for text in decoded:
            ec_preds.append(_parse_ec_raw(text))

    # Unload predict model to free VRAM before loading chat model
    print("[stage-1] Unloading predict model …")
    del model, base
    gc.collect()
    torch.cuda.empty_cache()

    return ec_preds


# ─────────────────────────── stage-2 (chat model) ─────────────────────────

_STAGE2_SYSTEM = (
    "You are an expert biochemist specializing in enzyme classification. "
    "You will be given a reaction SMILES, an EC number predicted by a specialised "
    "model, and — when available — supporting information from the BRENDA enzyme "
    "database. Your task is to confirm or refine the predicted EC number and provide "
    "a concise mechanistic explanation."
)


def _user_msg(smiles: str, ec1: str, brenda_context: str | None) -> str:
    lines = [
        f"Reaction SMILES: {smiles}",
        f"Predicted EC number: {ec1}",
    ]
    if brenda_context:
        lines.append(f"\nBREND information for EC {ec1}:\n{brenda_context}")
    lines.append(
        "\nConfirm or refine the EC number (X.XX.XX format) and provide a concise "
        "mechanistic explanation: identify the bond(s) broken and formed, the type "
        "of chemistry involved, and the cofactors or cosubstrates required."
        + (" Cite specific details from the BRENDA information above." if brenda_context else "")
    )
    return "\n".join(lines)


def _build_stage2_messages(smiles: str, ec1: str, brenda_context: str | None) -> list[dict]:
    return [
        {"role": "system", "content": _STAGE2_SYSTEM},
        {"role": "user",   "content": _user_msg(smiles, ec1, brenda_context)},
    ]


def _generate_chat_batch(
    model,
    tokenizer,
    messages_list: list[list[dict]],
    max_new_tokens: int,
    device: str,
) -> list[str]:
    prompts = [
        tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        for msgs in messages_list
    ]
    enc = tokenizer(
        prompts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=2048,
    ).to(device)

    with torch.no_grad():
        out = model.generate(
            **enc,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=None,
            top_p=None,
            pad_token_id=tokenizer.pad_token_id,
        )

    generated = out[:, enc["input_ids"].shape[1]:]
    return [tokenizer.decode(g, skip_special_tokens=True).strip() for g in generated]


def _run_chat_stage(
    smiles_list: list[str],
    ec_stage1_list: list[str],
    brenda_index: dict[str, str],
    chat_base_id: str,
    chat_adapter_dir: str,
    batch_size: int,
    max_new_tokens: int,
    hf_token: str | None,
    device: str,
) -> list[dict]:
    """Load chat model, run BRENDA-augmented stage-2, return per-sample dicts."""
    print(f"[stage-2] Loading tokenizer: {chat_base_id}")
    tok = AutoTokenizer.from_pretrained(
        chat_base_id, trust_remote_code=True, token=hf_token
    )
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"

    print(f"[stage-2] Loading base model: {chat_base_id}")
    base = AutoModelForCausalLM.from_pretrained(
        chat_base_id,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        token=hf_token,
    )
    print(f"[stage-2] Loading LoRA adapter: {chat_adapter_dir}")
    model = PeftModel.from_pretrained(base, chat_adapter_dir)
    model.eval()

    results = []
    for i in tqdm(range(0, len(smiles_list), batch_size), desc="stage-2 chat"):
        batch_smiles = smiles_list[i: i + batch_size]
        batch_ec1    = ec_stage1_list[i: i + batch_size]

        msgs_batch = []
        ctx_flags  = []
        for smiles, ec1 in zip(batch_smiles, batch_ec1):
            ec3_key = normalize_ec3(ec1)
            ctx = brenda_index.get(ec3_key) if ec3_key else None
            msgs_batch.append(_build_stage2_messages(smiles, ec1, ctx))
            ctx_flags.append(ctx is not None)

        raw_preds = _generate_chat_batch(model, tok, msgs_batch, max_new_tokens, device)

        for smiles, ec1, raw, has_ctx in zip(batch_smiles, batch_ec1, raw_preds, ctx_flags):
            results.append({
                "rxn_smiles":          smiles,
                "ec_stage1":           ec1,
                "ec_stage2":           _format_ec_output(raw),
                "explanation_stage2":  raw,
                "brenda_context_used": has_ctx,
            })

    del model, base
    gc.collect()
    torch.cuda.empty_cache()

    return results


# ─────────────────────────── main ─────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Hybrid Gemma4EC-Predict + Gemma4EC-Chat RAG inference")
    # predict model
    p.add_argument("--predict_adapter_dir", required=True,
                   help="Path to the Gemma4EC-Predict LoRA adapter "
                        "(e.g. results/ECReact/results/best)")
    p.add_argument("--predict_base_model_id", default="google/txgemma-9b-predict")
    # chat model
    p.add_argument("--chat_adapter_dir", required=True,
                   help="Path to the Gemma4EC-Chat LoRA adapter "
                        "(e.g. gemma4ec/chat/checkpoints/best_model)")
    p.add_argument("--chat_base_model_id", default="google/txgemma-9b-chat")
    # data
    p.add_argument("--brenda_index",
                   default="chat/data/brenda_index.json")
    p.add_argument("--input_csv", default="data/ECReact/test.csv")
    p.add_argument("--output_file",
                   default="./outputs/rag_predictions.tsv")
    # inference
    p.add_argument("--batch_size",     type=int, default=8)
    p.add_argument("--max_new_tokens", type=int, default=256)
    p.add_argument("--skip_stage2",    action="store_true",
                   help="Run stage-1 only (no BRENDA RAG / chat explanation)")
    p.add_argument("--hf_token", default=None)
    return p.parse_args()


def main():
    args = parse_args()

    if args.hf_token:
        from huggingface_hub import login
        login(token=args.hf_token)

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # ── load BRENDA index ──────────────────────────────────────────
    print(f"[rag_infer] Loading BRENDA index: {args.brenda_index}")
    with open(args.brenda_index, 'r', encoding='utf-8') as fh:
        brenda_index: dict[str, str] = json.load(fh)
    print(f"  {len(brenda_index):,} EC-3 entries loaded")

    # ── load input data ────────────────────────────────────────────
    df = pd.read_csv(args.input_csv)
    smiles_list = df["rxn_smiles"].tolist()
    gt_list     = df["ec"].tolist() if "ec" in df.columns else [None] * len(df)
    print(f"[rag_infer] {len(df):,} samples loaded from {args.input_csv}")

    # ── stage 1: predict model ─────────────────────────────────────
    ec_stage1_list = _run_predict_stage(
        smiles_list,
        predict_base_id=args.predict_base_model_id,
        predict_adapter_dir=args.predict_adapter_dir,
        batch_size=args.batch_size,
        hf_token=args.hf_token,
        device=device,
    )

    if args.skip_stage2:
        out = pd.DataFrame({
            "rxn_smiles": smiles_list,
            "ec_stage1":  ec_stage1_list,
        })
        if gt_list[0] is not None:
            out["ec_ground_truth"] = gt_list
        Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(args.output_file, sep='\t', index=False)
        print(f"[rag_infer] Stage-1 only. Saved {len(out):,} rows → {args.output_file}")
        if gt_list[0] is not None:
            acc = (out["ec_stage1"] == out["ec_ground_truth"]).mean()
            print(f"  Stage-1 exact-match: {acc:.4f}")
        return

    # ── stage 2: chat model ────────────────────────────────────────
    results = _run_chat_stage(
        smiles_list,
        ec_stage1_list,
        brenda_index,
        chat_base_id=args.chat_base_model_id,
        chat_adapter_dir=args.chat_adapter_dir,
        batch_size=args.batch_size,
        max_new_tokens=args.max_new_tokens,
        hf_token=args.hf_token,
        device=device,
    )

    # ── build output DataFrame ─────────────────────────────────────
    out = pd.DataFrame(results)
    out["ec_final"] = out["ec_stage2"].where(out["ec_stage2"].notna(), out["ec_stage1"])
    if gt_list[0] is not None:
        out["ec_ground_truth"] = gt_list

    Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output_file, sep='\t', index=False)
    print(f"[rag_infer] Saved {len(out):,} predictions → {args.output_file}")

    if "ec_ground_truth" in out.columns:
        def exact_match(col):
            return (out[col] == out["ec_ground_truth"]).mean()
        print(f"  Stage-1 exact-match: {exact_match('ec_stage1'):.4f}")
        print(f"  Stage-2 exact-match: {exact_match('ec_stage2'):.4f}")
        print(f"  Final   exact-match: {exact_match('ec_final'):.4f}")


if __name__ == "__main__":
    main()
