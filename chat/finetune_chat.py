#!/usr/bin/env python3
"""
Finetune google/txgemma-9b-chat for EC number prediction using LoRA.

Data format: CSV with columns  rxn_smiles, ec
Output: LoRA adapter saved to --output_dir/best_model/

Launch (single GPU):
    python chat/finetune_chat.py

Launch (multi-GPU via accelerate):
    accelerate launch --num_processes 4 --mixed_precision bf16 chat/finetune_chat.py
"""

import os
import time
import argparse
import warnings
from pathlib import Path

import torch
import pandas as pd
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
    set_seed,
)
from peft import LoraConfig, get_peft_model, TaskType

try:
    import wandb
    HAS_WANDB = True
except ImportError:
    HAS_WANDB = False

# ─────────────────────────── prompt ────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are an expert biochemist and conversational assistant specializing in "
    "enzyme classification and biochemistry. When given a reaction SMILES, "
    "predict the first three parts of the Enzyme Commission (EC) number "
    "(class.subclass.sub-subclass) in the format X.XX.XX with leading zeros "
    "where needed (e.g. 2.03.01). You may also discuss reaction mechanisms, "
    "enzyme function, and related biochemistry topics."
)

# Conversational response templates — varied to prevent mode collapse
_RESPONSE_TEMPLATES = [
    "The EC number for this reaction is {ec}.",
    "This reaction is classified as EC {ec}.",
    "Based on the reaction mechanism, the EC number is {ec}.",
    "EC {ec}.",
    "The enzyme catalyzing this reaction belongs to EC class {ec}.",
]


def _user_message(smiles: str) -> str:
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"What is the EC number for this reaction?\nSMILES: {smiles}"
    )


# ─────────────────────────── data helpers ──────────────────────────────────

def _build_messages(row, idx: int = 0) -> dict:
    template = _RESPONSE_TEMPLATES[idx % len(_RESPONSE_TEMPLATES)]
    return {
        "messages": [
            {"role": "user",      "content": _user_message(row["rxn_smiles"])},
            {"role": "assistant", "content": template.format(ec=str(row["ec"]))},
        ]
    }


def load_csv_as_dataset(csv_path: str) -> Dataset:
    df = pd.read_csv(csv_path)
    return Dataset.from_list([_build_messages(r, i) for i, (_, r) in enumerate(df.iterrows())])


def tokenize_with_label_masking(example, tokenizer, max_length: int) -> dict:
    """
    Apply chat template; set labels=-100 for all prompt tokens so loss is
    computed only on the assistant's response.
    """
    messages = example["messages"]

    full_text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=False
    )
    # Prompt = system + user + generation-prompt marker (no assistant turn)
    prompt_text = tokenizer.apply_chat_template(
        messages[:-1], tokenize=False, add_generation_prompt=True
    )

    full_enc   = tokenizer(full_text,   max_length=max_length, truncation=True)
    prompt_enc = tokenizer(prompt_text, max_length=max_length, truncation=True)

    prompt_len = len(prompt_enc["input_ids"])
    full_ids   = full_enc["input_ids"]
    labels = [-100] * prompt_len + full_ids[prompt_len:]

    return {
        "input_ids":      full_ids,
        "attention_mask": full_enc["attention_mask"],
        "labels":         labels,
    }


class _LabelPaddingCollator:
    """Pad input_ids / attention_mask / labels to the longest sample in batch."""
    def __init__(self, pad_token_id: int):
        self.pad_id = pad_token_id

    def __call__(self, features: list[dict]) -> dict[str, torch.Tensor]:
        max_len = max(len(f["input_ids"]) for f in features)
        batch = {"input_ids": [], "attention_mask": [], "labels": []}
        for f in features:
            pad = max_len - len(f["input_ids"])
            batch["input_ids"].append(f["input_ids"] + [self.pad_id] * pad)
            batch["attention_mask"].append(f["attention_mask"] + [0] * pad)
            batch["labels"].append(f["labels"] + [-100] * pad)
        return {k: torch.tensor(v, dtype=torch.long) for k, v in batch.items()}


# ─────────────────────────── main ──────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Finetune txgemma-9b-chat for EC number prediction"
    )
    # paths
    p.add_argument("--train_csv",   default="data/ECReact/train.csv")
    p.add_argument("--val_csv",     default="data/ECReact/val.csv")
    p.add_argument("--model_id",    default="google/txgemma-9b-chat")
    p.add_argument("--save_dir",    default="./chat/base_model",
                   help="Where to cache the downloaded base model weights")
    p.add_argument("--output_dir",  default="./chat/checkpoints")
    p.add_argument("--hf_token",    default=None)
    # LoRA — keep rank low to preserve conversational ability
    p.add_argument("--lora_r",       type=int,   default=8)
    p.add_argument("--lora_alpha",   type=int,   default=16)
    p.add_argument("--lora_dropout", type=float, default=0.05)
    # training — conservative LR to avoid overwriting base chat behaviour
    p.add_argument("--batch_size",   type=int,   default=4)
    p.add_argument("--grad_accum",   type=int,   default=4)
    p.add_argument("--epochs",       type=int,   default=5)
    p.add_argument("--lr",           type=float, default=5e-5)
    p.add_argument("--max_seq_len",  type=int,   default=1024)
    p.add_argument("--patience",     type=int,   default=3,
                   help="Early stopping patience (epochs)")
    p.add_argument("--seed",         type=int,   default=42)
    # W&B
    p.add_argument("--wandb_project",  default=None)
    p.add_argument("--wandb_entity",   default="miramon_team")
    p.add_argument("--wandb_run_name", default=None)
    p.add_argument("--disable_wandb",  action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    set_seed(args.seed)

    # ── HuggingFace login ───────────────────────────────────────────
    if args.hf_token:
        from huggingface_hub import login
        login(token=args.hf_token)

    # ── W&B ────────────────────────────────────────────────────────
    use_wandb = (
        HAS_WANDB
        and not args.disable_wandb
        and bool(args.wandb_project)
    )
    if use_wandb:
        run_name = args.wandb_run_name or f"chat_{time.strftime('%m%d_%H%M')}"
        wandb.init(
            project=args.wandb_project,
            entity=args.wandb_entity,
            name=run_name,
            tags=["TxGemma", "chat", "EC"],
        )
    elif not args.disable_wandb and not args.wandb_project:
        warnings.warn(
            "[finetune_chat] --wandb_project not set; W&B logging disabled.",
            UserWarning,
        )
    report_to = "wandb" if use_wandb else "none"

    # ── tokenizer ──────────────────────────────────────────────────
    print(f"[finetune_chat] Loading tokenizer: {args.model_id}")
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_id,
        cache_dir=args.save_dir,
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # ── model (bfloat16, no device_map for DDP compatibility) ──────
    print(f"[finetune_chat] Loading model: {args.model_id}")
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        cache_dir=args.save_dir,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )
    model.config.use_cache = False

    # ── LoRA ───────────────────────────────────────────────────────
    lora_cfg = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, lora_cfg)
    model.enable_input_require_grads()
    model.print_trainable_parameters()

    # ── datasets ───────────────────────────────────────────────────
    print("[finetune_chat] Building datasets …")
    tok_fn = lambda ex: tokenize_with_label_masking(ex, tokenizer, args.max_seq_len)

    train_ds = load_csv_as_dataset(args.train_csv).map(
        tok_fn, remove_columns=["messages"]
    )
    val_ds = load_csv_as_dataset(args.val_csv).map(
        tok_fn, remove_columns=["messages"]
    )
    print(f"  train: {len(train_ds):,}  val: {len(val_ds):,}")

    # ── trainer ────────────────────────────────────────────────────
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        bf16=True,
        fp16=False,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        save_total_limit=3,
        report_to=report_to,
        dataloader_num_workers=4,
        group_by_length=True,
        ddp_find_unused_parameters=False,
        gradient_checkpointing=True,
        seed=args.seed,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=_LabelPaddingCollator(tokenizer.pad_token_id),
        callbacks=[EarlyStoppingCallback(early_stopping_patience=args.patience)],
    )

    trainer.train()

    # ── save ───────────────────────────────────────────────────────
    best_dir = Path(args.output_dir) / "best_model"
    trainer.save_model(str(best_dir))
    tokenizer.save_pretrained(str(best_dir))
    print(f"[finetune_chat] Adapter saved → {best_dir}")

    if use_wandb and wandb.run is not None:
        wandb.finish()


if __name__ == "__main__":
    main()
