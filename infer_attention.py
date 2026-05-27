#!/usr/bin/env python3
"""
infer_attention.py — Gemma4EC inference + BertViz attention on reaction SMILES.

Samples 10 reactions from the raw test partition, predicts EC numbers with
the fine-tuned Gemma4EC adapter, and saves per-reaction:
  - BertViz head_view HTML  (interactive, open in a browser)
  - attention heatmap PNG   (avg attention of EC tokens to input, SMILES highlighted)
  - summary.tsv             (smiles / true_ec / predicted_ec / correct flags)

Setup (one-time — install bertviz into the gemma4ec env):
    conda activate gemma4ec
    pip install bertviz

Usage (defaults are ready to run from the Gemma4EC/ directory):
    conda activate gemma4ec
    python infer_attention.py

GPU with < 20 GB VRAM — add --load_in_4bit (uses bitsandbytes NF4):
    python infer_attention.py --load_in_4bit

Use a Rhea partition adapter instead:
    python infer_attention.py --adapter_path results/Rhea_Stratified/results/best
    python infer_attention.py --adapter_path results/Rhea_Time/results/best
    python infer_attention.py --adapter_path results/Rhea_Scaffold/results/best

Run with no adapter (base model only, zero-shot):
    python infer_attention.py --adapter_path ""

Output goes to ./attn_out/ by default.
"""

import os
import re
import json
import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch

# ── defaults ──────────────────────────────────────────────────────────────────

_HERE = Path(__file__).parent

BASE_MODEL = "google/txgemma-9b-predict"
ADAPTER    = str(_HERE / "results/ECReact/results/best")
TEST_CSV   = str(_HERE / "data/ECReact/test.csv")
PROMPTS    = str(_HERE / "prompts/prompts.json")
TEMPLATE   = "EC_NUMBER_PROMPT_2"
ANSWER_MK  = "Answer:"


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base_model_path", default=BASE_MODEL,
                   help="Path to the base TxGemma snapshot dir")
    p.add_argument("--adapter_path", default=ADAPTER,
                   help="Path to LoRA adapter dir (set to '' for base model only)")
    p.add_argument("--test_csv",    default=TEST_CSV)
    p.add_argument("--prompts_json", default=PROMPTS)
    p.add_argument("--template_key", default=TEMPLATE)
    p.add_argument("--output_dir",  default="./attn_out")
    p.add_argument("--n",   type=int, default=10, help="Reactions to sample")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max_tokens", type=int, default=400,
                   help="Max prompt tokens (SMILES are long; truncated if needed)")
    p.add_argument("--load_in_4bit", action="store_true",
                   help="4-bit NF4 quantization — needed if GPU VRAM < 20 GB")
    return p.parse_args()


# ── model loading ─────────────────────────────────────────────────────────────

def load_model_and_tokenizer(base_path, adapter_path, load_in_4bit):
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    from peft import PeftModel

    print(f"[load] Tokenizer from {base_path}")
    tok = AutoTokenizer.from_pretrained(base_path)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    if load_in_4bit:
        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        print("[load] Base model (4-bit NF4) …")
        model = AutoModelForCausalLM.from_pretrained(
            base_path,
            quantization_config=quant,
            attn_implementation="eager",   # needed for output_attentions
            device_map="auto",
        )
    else:
        print("[load] Base model (bfloat16) …")
        model = AutoModelForCausalLM.from_pretrained(
            base_path,
            torch_dtype=torch.bfloat16,
            attn_implementation="eager",
            device_map="cuda:0",
        )

    if adapter_path:
        print(f"[load] LoRA adapter: {adapter_path}")
        model = PeftModel.from_pretrained(model, adapter_path, is_trainable=False)

    model.eval()
    print("[load] Ready.\n")
    return model, tok


# ── EC string parsing ─────────────────────────────────────────────────────────

def parse_ec(text: str) -> str:
    """Extract the EC prediction from the full decoded output."""
    tail = text.rsplit(ANSWER_MK, 1)[-1] if ANSWER_MK in text else text
    tail = tail.strip()
    return tail.splitlines()[0].strip() if tail else ""


# ── SMILES token span ─────────────────────────────────────────────────────────

def smiles_token_span(prompt: str, tok, max_tokens: int):
    """
    Return (start_tok_idx, end_tok_idx) of the SMILES within the truncated
    token sequence, using character-level offset mapping from the fast tokenizer.
    Returns (None, None) if the tokenizer does not support offset mapping.
    """
    try:
        enc = tok(
            prompt,
            truncation=True,
            max_length=max_tokens,
            return_offsets_mapping=True,
        )
    except Exception:
        return None, None

    offsets = enc["offset_mapping"]

    sm_marker  = "Reaction SMILES:"
    ans_marker = "\nAnswer:"

    sm_pos = prompt.find(sm_marker)
    if sm_pos == -1:
        return None, None
    char_start = sm_pos + len(sm_marker) + 1   # +1 skips the space after ':'

    ans_pos   = prompt.find(ans_marker)
    char_end  = ans_pos if ans_pos != -1 else len(prompt)

    tok_start = next((i for i, (s, e) in enumerate(offsets) if e > char_start),  None)
    tok_end   = next((i for i, (s, e) in enumerate(offsets) if s >= char_end), len(offsets))

    return tok_start, tok_end


# ── inference + attentions ────────────────────────────────────────────────────

@torch.no_grad()
def run_single(model, tok, prompt, max_tokens, max_new_tokens=8):
    """
    Generate the EC prediction and run a separate forward pass to get
    attention weights over the full sequence (prompt + generated tokens).

    Returns
    -------
    predicted_ec  str
    attention     list[Tensor]  shape [num_heads, full_len, full_len] per layer, on CPU
    tokens        list[str]     full token list
    prompt_len    int           number of prompt tokens
    """
    device = next(model.parameters()).device

    enc = tok(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=max_tokens,
    ).to(device)
    prompt_len = enc.input_ids.shape[1]

    # ── generation (no attention needed here, keep it fast) ──────────────────
    gen_ids = model.generate(
        input_ids=enc.input_ids,
        attention_mask=enc.attention_mask,
        max_new_tokens=max_new_tokens,
        do_sample=False,
    )  # [1, prompt_len + new_toks]

    full_text    = tok.decode(gen_ids[0], skip_special_tokens=True)
    predicted_ec = parse_ec(full_text)

    # ── forward pass for attentions on the full sequence ─────────────────────
    full_mask = torch.ones_like(gen_ids)
    out = model(input_ids=gen_ids, attention_mask=full_mask, output_attentions=True)

    # Keep batch dim for BertViz ([1, heads, seq, seq]); heatmap squeezes it itself
    attention      = [a.cpu().float() for a in out.attentions]
    attention_2d   = [a.squeeze(0) for a in attention]   # [heads, seq, seq] for heatmap
    tokens         = tok.convert_ids_to_tokens(gen_ids[0].tolist())

    return predicted_ec, attention, attention_2d, tokens, prompt_len


# ── BertViz HTML ──────────────────────────────────────────────────────────────

def save_bertviz_html(attention, tokens, path: Path,
                      sm_start: int = None, prompt_len: int = None):
    """Save an interactive BertViz head_view HTML showing only SMILES + EC tokens.

    Uses the last layer and slices the attention matrix to
    [sm_start : total_seq_len] so the visualisation shows:
      • the SMILES tokens (orange in the PNG heatmap)
      • the '\\nAnswer:' separator tokens
      • the generated EC number tokens
    keeping files small (< 200 KB) and the view focused.
    """
    try:
        from bertviz import head_view

        last    = attention[-1]              # [1, heads, seq, seq]
        seq_len = last.shape[-1]

        # Slice window: from first SMILES token to end of sequence
        tok_s = sm_start if sm_start is not None else 0
        tok_e = seq_len

        attn_slice  = last[:, :, tok_s:tok_e, tok_s:tok_e]
        toks_slice  = tokens[tok_s:tok_e]

        # Round to 4 d.p. to keep the JSON compact
        attn_np = attn_slice.numpy().round(4)
        import torch as _torch
        attn_tensor = _torch.tensor(attn_np)

        html = head_view([attn_tensor], toks_slice, html_action="return")
        path.write_text(html.data, encoding="utf-8")
        n_shown = tok_e - tok_s
        print(f"  [html]  {path.name}  ({n_shown} tokens: SMILES+EC, last layer)")
    except ImportError:
        print("  [html]  SKIP — install bertviz: pip install bertviz")
    except Exception as exc:
        print(f"  [html]  SKIP ({exc})")


# ── attention heatmap PNG ─────────────────────────────────────────────────────

def save_heatmap(
    attention, tokens, prompt_len,
    sm_start, sm_end,
    predicted_ec, true_ec, rxn_smiles, path: Path,
):
    """
    Two-panel figure:
      top   — avg attention of EC-generation tokens to every input position
              (grey = instruction, orange = SMILES, teal = generated EC)
      bottom — zoom into the SMILES token region only
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        seq_len = attention[0].shape[-1]

        # [num_layers, num_heads, seq_len, seq_len]
        stacked = torch.stack(attention)

        # Positions that belong to the generated EC number
        ec_pos = list(range(prompt_len, seq_len))
        if not ec_pos:
            ec_pos = [seq_len - 1]

        # Average across layers, heads, and EC token positions → [seq_len]
        avg = stacked[:, :, ec_pos, :].mean(dim=(0, 1, 2)).numpy()
        avg /= avg.sum() + 1e-9

        # ── colours ──────────────────────────────────────────────────────────
        colors = []
        for i in range(seq_len):
            if sm_start is not None and sm_start <= i < (sm_end or seq_len):
                colors.append("#e76f51")   # orange → SMILES
            elif i >= prompt_len:
                colors.append("#2a9d8f")   # teal   → generated EC
            else:
                colors.append("#adb5bd")   # grey   → instruction text

        # ── figure ───────────────────────────────────────────────────────────
        fig, axes = plt.subplots(
            2, 1,
            figsize=(max(16, seq_len // 4), 8),
            gridspec_kw={"height_ratios": [3, 2]},
        )

        # Top panel — full sequence
        ax0 = axes[0]
        ax0.bar(range(seq_len), avg, color=colors, width=1.0, edgecolor="none")
        step = max(1, seq_len // 50)
        ax0.set_xticks(range(0, seq_len, step))
        ax0.set_xticklabels(
            [tokens[i][:8] for i in range(0, seq_len, step)],
            rotation=90, fontsize=5,
        )
        ax0.set_ylabel("Avg attention weight", fontsize=9)
        ax0.set_title(
            f"Attention of EC tokens to input  |  True: {true_ec}  →  Predicted: {predicted_ec}\n"
            f"Orange = SMILES (tok {sm_start}–{sm_end})   "
            f"Teal = generated EC   Grey = instruction",
            fontsize=9,
        )

        # Bottom panel — zoom into SMILES region
        ax1 = axes[1]
        if sm_start is not None and sm_end is not None:
            se = min(sm_end, seq_len)
            sm_avg = avg[sm_start:se]
            sm_tok = tokens[sm_start:se]

            ax1.bar(range(len(sm_avg)), sm_avg, color="#e76f51",
                    width=1.0, edgecolor="none")
            step2 = max(1, len(sm_avg) // 40)
            ax1.set_xticks(range(0, len(sm_avg), step2))
            ax1.set_xticklabels(
                [sm_tok[i][:10] for i in range(0, len(sm_avg), step2)],
                rotation=90, fontsize=6,
            )
            ax1.set_ylabel("Attn (SMILES only)", fontsize=8)
            ax1.set_title(
                f"Zoom: SMILES region  ({se - sm_start} tokens shown)",
                fontsize=8,
            )
        else:
            ax1.text(0.5, 0.5, "SMILES span not detected",
                     ha="center", va="center", transform=ax1.transAxes)

        plt.tight_layout()
        plt.savefig(path, dpi=150)
        plt.close()
        print(f"  [png]   {path.name}")

    except ImportError:
        print("  [png]   SKIP — install matplotlib: pip install matplotlib")
    except Exception as exc:
        print(f"  [png]   SKIP ({exc})")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(args.prompts_json) as f:
        template = json.load(f)[args.template_key]

    df = pd.read_csv(args.test_csv)
    sampled = df.sample(n=args.n, random_state=args.seed).reset_index(drop=True)
    print(f"Sampled {args.n} reactions (seed={args.seed}) from {args.test_csv}\n")

    model, tok = load_model_and_tokenizer(
        args.base_model_path,
        args.adapter_path or None,
        args.load_in_4bit,
    )

    rows = []
    for i, row in sampled.iterrows():
        smiles  = row["rxn_smiles"]
        true_ec = str(row["ec"])
        prompt  = template.format(reaction_smiles=smiles)

        print(f"── reaction {i+1:02d}/{args.n}  true EC: {true_ec} ──")
        print(f"   SMILES length: {len(smiles)} chars")

        predicted_ec, attention, attention_2d, tokens, prompt_len = run_single(
            model, tok, prompt, args.max_tokens
        )
        print(f"   predicted:     {predicted_ec}")

        sm_start, sm_end = smiles_token_span(prompt, tok, args.max_tokens)

        tag = f"rxn{i+1:02d}"
        save_bertviz_html(attention, tokens,           out_dir / f"{tag}_bertviz.html",
                          sm_start=sm_start, prompt_len=prompt_len)
        save_heatmap(
            attention_2d, tokens, prompt_len,
            sm_start, sm_end,
            predicted_ec, true_ec, smiles,
            out_dir / f"{tag}_attn.png",
        )

        rows.append({
            "reaction":     i + 1,
            "rxn_smiles":   smiles,
            "true_ec":      true_ec,
            "predicted_ec": predicted_ec,
            "correct_L3":   predicted_ec.strip() == true_ec.strip(),
            "correct_L1":   (bool(predicted_ec) and bool(true_ec)
                             and predicted_ec[0] == true_ec[0]),
            "smiles_tok_start": sm_start,
            "smiles_tok_end":   sm_end,
            "total_tokens":     len(tokens),
        })

        torch.cuda.empty_cache()

    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "summary.tsv", sep="\t", index=False)

    n   = len(summary)
    l3  = summary["correct_L3"].sum()
    l1  = summary["correct_L1"].sum()
    print(f"\n{'═'*52}")
    print(f"  Level-3 accuracy : {l3}/{n}  ({l3/n:.0%})")
    print(f"  Level-1 accuracy : {l1}/{n}  ({l1/n:.0%})")
    print(f"  Output           : {out_dir}/")
    print(f"{'═'*52}")


if __name__ == "__main__":
    main()
