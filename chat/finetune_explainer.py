#!/usr/bin/env python3
"""
LoRA fine-tuning of a Gemma chat model (default TxGemma-9B-Chat) on teacher explanations from chat/explain_v2.py
(distillation: a larger Gemma runs the v2 pipeline on training-split reactions; only answers that pass the checks
are kept).

Two kinds of example per reaction, in the exact format explain_v2.py uses at inference:
  - EC choice:   ec_prompt (two candidate orders)                 -> chosen EC number
  - explanation: few-shot turns + case block + task               -> MECHANISM / WHY EC text
Loss is computed on the answer tokens only.

Usage:
    python chat/finetune_explainer.py --teacher 'chat/ft_data/teacher_chunk*.json' --out_dir chat/ft_adapter
"""

import argparse
import glob
import json
import random
import sys
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, get_cosine_schedule_with_warmup

sys.path.insert(0, str(Path(__file__).parent))
from explain_v2 import TASK_B, case_block, ec_prompt, few_shot_turns  # noqa: E402


def keep(r):
    """Teacher answers worth learning from."""
    if r.get("unresolved_issues"):
        return False
    cand = next(c for c in r["candidates"] if c["ec4"] == r["chosen_ec4"])
    known = [c["ec4"] for c in r["candidates"] if "known" in c and c["ec4"].startswith(r["true_ec"] + ".")]
    if known and r["chosen_ec4"] not in known:
        return False
    if not r["chosen_ec4"].startswith(r["true_ec"] + "."):
        return False
    n = sum(r["votes"].values()) or 1
    # only mechanisms grounded in M-CSA for this enzyme or a class card; analogies to other enzymes can be wrong
    return r["votes"].get(r["chosen_ec4"], 0) / n >= 0.6 and (cand.get("reference") or {}).get("kind") in ("exact", "class")


def examples(records, rng):
    out = []
    for r in records:
        cand = next(c for c in r["candidates"] if c["ec4"] == r["chosen_ec4"])
        for k in range(2):
            order = r["candidates"][:] if k == 0 else rng.sample(r["candidates"], len(r["candidates"]))
            out.append(([{"role": "user", "content": ec_prompt(r, order)}], r["chosen_ec4"]))
        out.append((few_shot_turns() + [{"role": "user", "content": case_block(r, cand) + "\n\n" + TASK_B}],
                    r["explanation"]))
    return out


def encode(tok, messages, answer, max_len):
    prompt = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
    a_ids = tok(answer + "<end_of_turn>\n", add_special_tokens=False)["input_ids"]
    ids = (p_ids + a_ids)[-max_len:]
    labels = ([-100] * len(p_ids) + a_ids)[-max_len:]
    return torch.tensor(ids), torch.tensor(labels)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--teacher", default="chat/ft_data/teacher_chunk*.json")
    ap.add_argument("--model_id", default="google/txgemma-9b-chat")
    ap.add_argument("--out_dir", default="chat/ft_adapter")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--grad_accum", type=int, default=8)
    ap.add_argument("--max_len", type=int, default=3072)
    ap.add_argument("--lora_r", type=int, default=16)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    torch.manual_seed(args.seed)

    records = [r for f in sorted(glob.glob(args.teacher)) for r in json.load(open(f))]
    kept = [r for r in records if keep(r)]
    print(f"teacher records: {len(records)}, kept after checks: {len(kept)}", flush=True)
    rng.shuffle(kept)
    n_val = max(1, len(kept) // 10)
    val_r, train_r = kept[:n_val], kept[n_val:]

    tok = AutoTokenizer.from_pretrained(args.model_id)
    model = AutoModelForCausalLM.from_pretrained(args.model_id, dtype=torch.bfloat16, device_map="auto")
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(r=args.lora_r, lora_alpha=2 * args.lora_r, lora_dropout=0.05,
                                             target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                                             "gate_proj", "up_proj", "down_proj"],
                                             task_type="CAUSAL_LM"))
    model.print_trainable_parameters()
    train = [encode(tok, m, a, args.max_len) for m, a in examples(train_r, rng)]
    val = [encode(tok, m, a, args.max_len) for m, a in examples(val_r, rng)]
    print(f"train examples {len(train)}, val examples {len(val)}", flush=True)

    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr, weight_decay=0.0)
    steps = args.epochs * len(train) // args.grad_accum
    sched = get_cosine_schedule_with_warmup(opt, max(1, steps // 20), max(1, steps))
    dev = model.get_input_embeddings().weight.device

    def val_loss():
        model.eval()
        tot = 0.0
        with torch.no_grad():
            for ids, lab in val:
                tot += model(input_ids=ids[None].to(dev), labels=lab[None].to(dev)).loss.item()
        model.train()
        return tot / max(len(val), 1)

    best = float("inf")
    model.train()
    for ep in range(args.epochs):
        rng.shuffle(train)
        for i, (ids, lab) in enumerate(train):
            loss = model(input_ids=ids[None].to(dev), labels=lab[None].to(dev)).loss / args.grad_accum
            loss.backward()
            if (i + 1) % args.grad_accum == 0 or i + 1 == len(train):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step(); sched.step(); opt.zero_grad()
            if (i + 1) % 50 == 0:
                print(f"epoch {ep} step {i + 1}/{len(train)} loss {loss.item() * args.grad_accum:.3f}", flush=True)
        vl = val_loss()
        print(f"epoch {ep} val loss {vl:.4f}", flush=True)
        if vl < best:
            best = vl
            model.save_pretrained(args.out_dir)
            tok.save_pretrained(args.out_dir)
            print(f"  saved adapter → {args.out_dir}", flush=True)
    Path(args.out_dir, "train_info.json").write_text(json.dumps(
        {"teacher_files": sorted(glob.glob(args.teacher)), "records": len(records), "kept": len(kept),
         "val_reactions": [r["rxn_smiles"] for r in val_r], "best_val_loss": best, "args": vars(args)}, indent=1))


if __name__ == "__main__":
    main()
