"""
main.py — Fine-tune TxGemma for EC number prediction using LoRA adapters.

Minimal usage (all defaults pre-configured):
    python main.py \
        --wandb_project my_project \
        --wandb_entity my_entity

W&B is optional — to disable it entirely:
    python main.py --disable_wandb

Full usage example:
    python main.py \
        --raw_data_folder data/ \
        --output_folder outputs/checkpoints \
        --model_id google/txgemma-9b-predict \
        --num_train_epochs 5 \
        --batch_size 8 \
        --lora_r 8 \
        --wandb_project my_project \
        --wandb_entity my_entity
"""

import os
import time
import warnings
from pathlib import Path
import argparse
import pandas as pd
import wandb
from accelerate import Accelerator
from datasets import load_dataset
from peft import get_peft_model

from src.config import Config
from src.datamod.templates import build_input_template_from_file
from src.datamod.jsonl_builder import create_jsonl_from_df
from src.utils.paths import get_jsonl_path
from src.utils.seqcheck import run_seq_len_check_with_mode
from src.models.modeling import (
    build_model_and_tokenizer,
    build_peft_config,
    apply_gradient_checkpointing_if_needed,
)
from src.training.sft_trainer import build_trainer
from src.training.manual.train_loop_manual import train_manual
from src.training.callbacks import ECValidationCallback
from src.evaluation.eval import evaluate_model

# ---------------------------------------------------------------------------
# Distributed environment defaults (single-GPU safe, HPC-safe)
# setdefault means: only set if not already set by the launcher (e.g. SLURM)
# ---------------------------------------------------------------------------
os.environ.setdefault("WORLD_SIZE", "1")
os.environ.setdefault("RANK", "0")
os.environ.setdefault("LOCAL_RANK", "0")
os.environ.setdefault("MASTER_ADDR", "localhost")
os.environ.setdefault("MASTER_PORT", "12355")


def main():
    args = parse_args()
    accelerator = Accelerator()

    # ------------------------------------------------------------------
    # W&B setup — optional, warns if not configured
    # ------------------------------------------------------------------
    use_wandb = not args.disable_wandb

    if use_wandb and accelerator.is_main_process:
        if args.wandb_entity is None or args.wandb_project is None:
            warnings.warn(
                "\n[main] W&B is enabled but --wandb_entity or --wandb_project is not set.\n"
                "       Training will continue without W&B logging.\n"
                "       Pass --disable_wandb to silence this warning, or set both flags to enable logging.",
                UserWarning,
            )
            use_wandb = False

    cfg = Config.from_args(args).env_applied()

    # ------------------------------------------------------------------
    # Prompt template / paths
    # ------------------------------------------------------------------
    input_template = build_input_template_from_file(
        template_path=args.prompts_json_path,
        key=args.template_key,
        required_vars={"reaction_smiles"},
        dict_key=args.template_alias,
    )

    raw_dir       = Path(args.raw_data_folder)
    processed_dir = Path(args.processed_data_folder)
    processed_dir.mkdir(parents=True, exist_ok=True)
    Path(args.output_folder).mkdir(parents=True, exist_ok=True)

    train_csv = raw_dir / "train.csv"
    val_csv   = raw_dir / "val.csv"
    test_csv  = raw_dir / "test.csv"

    train_jsonl = get_jsonl_path(str(processed_dir), "train", args.template_alias, args.template_key)
    val_jsonl   = get_jsonl_path(str(processed_dir), "val",   args.template_alias, args.template_key)
    test_jsonl  = get_jsonl_path(str(processed_dir), "test",  args.template_alias, args.template_key)

    # ------------------------------------------------------------------
    # W&B init + JSONL build (main process only)
    # ------------------------------------------------------------------
    if accelerator.is_main_process:
        if use_wandb:
            run_name = args.wandb_run_name or (
                f"{args.wandb_group or 'run'}_{time.strftime('%m%d_%H%M')}"
            )
            try:
                wandb.init(
                    project=args.wandb_project,
                    entity=args.wandb_entity,
                    name=run_name,
                    group=args.wandb_group or None,
                    tags=args.wandb_tags,
                    job_type=args.job_type,
                    config=cfg.wandb_config(),
                )
            except Exception as e:
                warnings.warn(
                    f"[main] W&B init failed ({e}). Training will continue without W&B logging.",
                    UserWarning,
                )
                use_wandb = False
        else:
            print("[main] W&B logging disabled.")

        print(f"[main] Building JSONL files from: {raw_dir}")
        create_jsonl_from_df(str(train_csv), train_jsonl, input_template)
        create_jsonl_from_df(str(val_csv),   val_jsonl,   input_template)

        if args.use_test and test_csv.exists():
            create_jsonl_from_df(str(test_csv), test_jsonl, input_template)
        elif args.use_test:
            print("[main] --use_test was set but test.csv not found; skipping test split.")

        # Log dataset sizes to W&B config (fast line count, -1 for header)
        if use_wandb and wandb.run is not None:
            _sizes = {"data/train_rows": sum(1 for _ in open(train_csv)) - 1}
            if val_csv.exists():
                _sizes["data/val_rows"] = sum(1 for _ in open(val_csv)) - 1
            if test_csv.exists():
                _sizes["data/test_rows"] = sum(1 for _ in open(test_csv)) - 1
            wandb.config.update(_sizes, allow_val_change=True)
            print(f"[main] Dataset sizes logged to W&B: {_sizes}")

    accelerator.wait_for_everyone()

    # ------------------------------------------------------------------
    # Load HF datasets
    # ------------------------------------------------------------------
    data_files = {"train": train_jsonl, "validation": val_jsonl}
    if args.use_test and Path(test_jsonl).exists():
        data_files["test"] = test_jsonl

    data = load_dataset("json", data_files=data_files)

    # ------------------------------------------------------------------
    # Load base model + tokenizer
    # ------------------------------------------------------------------
    print(f"[main] Loading base model : {args.model_id}")
    print(f"[main] Cache directory    : {args.cache_dir}")
    model, tokenizer = build_model_and_tokenizer(
        args.model_id, args.save_directory, args.cache_dir
    )

    # ------------------------------------------------------------------
    # Sequence-length sanity check (aborts early if data is too long)
    # ------------------------------------------------------------------
    if args.seqcheck_enabled:
        run_seq_len_check_with_mode(
            train_ds=data["train"],
            val_ds=data["validation"],
            tokenizer=tokenizer,
            args=args,
            is_main_process=accelerator.is_main_process,
        )

    # ------------------------------------------------------------------
    # Wrap model with LoRA / DoRA / AdaLoRA adapter
    # ------------------------------------------------------------------
    peft_cfg = build_peft_config(
        method=args.adapter_method,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=cfg.target_modules,
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, peft_cfg)
    model = apply_gradient_checkpointing_if_needed(model, args)

    # ------------------------------------------------------------------
    # Train
    # ------------------------------------------------------------------
    if args.trainer_mode == "sft":
        # TRL's SFTTrainer handles Accelerate internally — do NOT call accelerator.prepare()
        trainer = build_trainer(train_ds=data["train"], model=model, args=args)
        trainer.add_callback(
            ECValidationCallback(accelerator, tokenizer, data["validation"], args)
        )
        trainer.train()

        trained_model = trainer.model
        if hasattr(trained_model, "module"):
            trained_model = trained_model.module

    else:
        # Manual loop handles accelerator.prepare() internally
        trained_model = train_manual(
            train_ds=data["train"],
            val_ds=data["validation"],
            model=model,
            tokenizer=tokenizer,
            args=args,
            accelerator=accelerator,
        )

    # ------------------------------------------------------------------
    # Evaluate on validation (and optionally test)
    # ------------------------------------------------------------------
    if accelerator.is_main_process:
        print("[main] Evaluating on validation split ...")

    evaluate_model(
        accelerator, trained_model, tokenizer,
        data["validation"], args,
        split="val", save_predictions=True,
    )
    accelerator.wait_for_everyone()

    if "test" in data:
        if accelerator.is_main_process:
            print("[main] Evaluating on test split ...")
        evaluate_model(
            accelerator, trained_model, tokenizer,
            data["test"], args,
            split="test", save_predictions=True,
        )
        accelerator.wait_for_everyone()

    if accelerator.is_main_process and wandb.run is not None:
        wandb.finish()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fine-tune TxGemma for EC number prediction using LoRA adapters.",
        allow_abbrev=False,
    )

    # --- Data paths (defaults match repo structure) ---
    parser.add_argument("--raw_data_folder", type=str,
                        default="./data",
                        help="Folder containing train.csv, val.csv, and optionally test.csv. "
                             "(default: ./data)")
    parser.add_argument("--processed_data_folder", type=str,
                        default="./outputs/inter_data",
                        help="Directory for intermediate JSONL files. (default: ./outputs/inter_data)")
    parser.add_argument("--output_folder", type=str,
                        default="./outputs/checkpoints",
                        help="Directory for checkpoints, logs, and prediction TSVs. "
                             "Output TSV format: predictions_<split>.EC_NUMBER.EC_NUMBER_PROMPT_1.<timestamp>.tsv "
                             "(default: ./outputs/checkpoints)")
    parser.add_argument("--use_test",
                        type=lambda x: str(x).lower() in {"1", "true", "yes"},
                        default=False,
                        help="If true and test.csv exists, evaluate on test split after training. (default: false)")

    # --- Model ---
    parser.add_argument("--model_id", type=str,
                        default="google/txgemma-2b-predict",
                        help="Base TxGemma model to fine-tune. "
                             "Use google/txgemma-9b-predict for best accuracy (~18GB VRAM). "
                             "Use google/txgemma-2b-predict for lower VRAM (~6GB). "
                             "(default: google/txgemma-2b-predict)")
    parser.add_argument("--save_directory", type=str,
                        default="./local_txgemma_model",
                        help="Where to cache the downloaded base model. (default: ./local_txgemma_model)")
    parser.add_argument("--cache_dir", type=str,
                        default="./hfcache",
                        help="Hugging Face cache directory. (default: ./hfcache)")

    # --- Prompts ---
    parser.add_argument("--prompts_json_path", type=str,
                        default="./prompts/prompts.json",
                        help="Path to prompts.json. (default: ./prompts/prompts.json)")
    parser.add_argument("--template_key", type=str,
                        default="EC_NUMBER_PROMPT_1",
                        help="Prompt template key in prompts.json. (default: EC_NUMBER_PROMPT_1)")
    parser.add_argument("--template_alias", type=str,
                        default="EC_NUMBER",
                        help="Internal alias for the prompt template. (default: EC_NUMBER)")

    # --- Core training hyperparameters ---
    parser.add_argument("--num_train_epochs", type=int, default=5,
                        help="Number of training epochs. (default: 5)")
    parser.add_argument("--batch_size", type=int, default=16,
                        help="Per-device training batch size. Reduce if you run out of VRAM. (default: 16)")
    parser.add_argument("--eval_batch_size", type=int, default=32,
                        help="Per-device batch size for evaluation. Reduce if you run out of VRAM. (default: 32)")
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4,
                        help="Accumulate gradients over N steps before updating. "
                             "Increase to simulate a larger batch size without more VRAM. (default: 4)")
    parser.add_argument("--learning_rate", type=float, default=5e-6,
                        help="Learning rate. (default: 5e-6)")
    parser.add_argument("--weight_decay", type=float, default=0.0,
                        help="Weight decay for optimizer. (default: 0.0)")
    parser.add_argument("--warmup_steps", type=int, default=2,
                        help="Number of warmup steps for the LR scheduler. (default: 2)")
    parser.add_argument("--lr_scheduler_type", type=str, default="linear",
                        choices=["linear", "cosine", "cosine_with_restarts", "polynomial",
                                 "constant", "constant_with_warmup"],
                        help="Learning rate scheduler type. (default: linear)")
    parser.add_argument("--optimizer", type=str, default="paged_adamw_8bit",
                        help="Optimizer. paged_adamw_8bit saves VRAM. (default: paged_adamw_8bit)")
    parser.add_argument("--fp16",
                        type=lambda x: str(x).lower() in {"1", "true", "yes"},
                        default=True,
                        help="Use mixed precision (fp16) training. Disable on GPUs that don't support it. (default: true)")
    parser.add_argument("--max_seq_length", type=int, default=512,
                        help="Maximum token length for inputs. Sequences longer than this are truncated. (default: 512)")
    parser.add_argument("--logging_steps", type=int, default=5,
                        help="Log training loss every N steps. (default: 5)")
    parser.add_argument("--trainer_mode", type=str, choices=["sft", "manual"], default="sft",
                        help="Training loop to use. 'sft' uses TRL's SFTTrainer (recommended). "
                             "'manual' enables few-shot training. (default: sft)")

    # --- LoRA adapter ---
    parser.add_argument("--adapter_method", type=str, default="lora",
                        choices=["lora", "dora", "adalora"],
                        help="Adapter type. lora is the standard choice. (default: lora)")
    parser.add_argument("--lora_r", type=int, default=8,
                        help="LoRA rank. Higher = more capacity but more VRAM. (default: 8)")
    parser.add_argument("--lora_alpha", type=int, default=16,
                        help="LoRA scaling factor. Usually set to 2× lora_r. (default: 16)")
    parser.add_argument("--lora_dropout", type=float, default=0.0,
                        help="Dropout probability for LoRA layers. (default: 0.0)")
    parser.add_argument("--target_modules",
                        type=lambda s: [x.strip() for x in s.split(",")] if s else None,
                        default=None,
                        help="Comma-separated list of modules to apply LoRA to. "
                             "Leave unset to use defaults: q_proj,o_proj,k_proj,v_proj,gate_proj,up_proj,down_proj")
    parser.add_argument("--task_type", type=str, default="CAUSAL_LM",
                        help="PEFT task type. Do not change unless you know what you're doing. (default: CAUSAL_LM)")

    # --- Checkpointing & early stopping ---
    parser.add_argument("--save_best",
                        type=lambda x: str(x).lower() in {"1", "true", "yes"},
                        default=False,
                        help="Save the best checkpoint based on --monitor_metric. (default: false)")
    parser.add_argument("--monitor_metric", type=str, default="mcc",
                        choices=["accuracy", "mcc", "f1_macro", "f1_weighted"],
                        help="Metric to monitor for best checkpoint and early stopping. (default: mcc)")
    parser.add_argument("--greater_is_better",
                        type=lambda x: str(x).lower() in {"1", "true", "yes"},
                        default=True,
                        help="Whether a higher --monitor_metric value is better. (default: true)")
    parser.add_argument("--early_stopping_patience", type=int, default=0,
                        help="Stop training if metric does not improve for N epochs. 0 = disabled. (default: 0)")
    parser.add_argument("--eval_every_epochs", type=int, default=0,
                        help="Run EC validation every N epochs during training. 0 = disabled. (default: 0)")

    # --- Sequence length sanity check ---
    parser.add_argument("--seqcheck_enabled",
                        type=lambda x: str(x).lower() in {"1", "true", "yes"},
                        default=True,
                        help="Run a pre-training check to detect sequences that will be truncated. "
                             "Recommended to keep enabled. (default: true)")
    parser.add_argument("--seqcheck_subset", type=int, default=20000,
                        help="Max samples to scan during the sequence check. (default: 20000)")
    parser.add_argument("--seqcheck_batch_size", type=int, default=1024,
                        help="Batch size for the sequence check tokenization. (default: 1024)")
    parser.add_argument("--fail_on_truncation",
                        type=lambda x: str(x).lower() in {"1", "true", "yes"},
                        default=True,
                        help="Abort training if truncation rate exceeds --truncation_tolerance. (default: true)")
    parser.add_argument("--truncation_tolerance", type=float, default=0.01,
                        help="Allowed fraction of truncated sequences, e.g. 0.01 = 1%%. (default: 0.01)")

    # --- Few-shot training (manual mode only) ---
    parser.add_argument("--few_shot_training",
                        type=lambda x: str(x).lower() in {"1", "true", "yes"},
                        default=False,
                        help="Mix zero-shot and few-shot prompts during training. "
                             "Requires --trainer_mode=manual. (default: false)")
    parser.add_argument("--few_shot_ratio", type=float, default=0.3,
                        help="Fraction of training examples that use few-shot prompts. (default: 0.3)")
    parser.add_argument("--few_shot_k_min", type=int, default=1,
                        help="Minimum number of in-context examples for few-shot prompts. (default: 1)")
    parser.add_argument("--few_shot_k_max", type=int, default=10,
                        help="Maximum number of in-context examples for few-shot prompts. (default: 10)")

    # --- W&B (optional) ---
    parser.add_argument("--disable_wandb", action="store_true",
                        help="Disable Weights & Biases logging entirely.")
    parser.add_argument("--wandb_project", type=str, default=None,
                        help="W&B project name. Required if W&B is enabled.")
    parser.add_argument("--wandb_entity", type=str, default=None,
                        help="W&B entity (username or team). Required if W&B is enabled.")
    parser.add_argument("--wandb_run_name", type=str, default=None,
                        help="Human-readable name for the W&B run. "
                             "Defaults to '<wandb_group>_MMDD_HHMM'. (default: None)")
    parser.add_argument("--wandb_group", type=str, default=None,
                        help="W&B run group to cluster related runs together. (default: None)")
    parser.add_argument("--wandb_tags", type=str, nargs="+",
                        default=["TxGemma", "EC"],
                        help="Tags for the W&B run. (default: TxGemma EC)")
    parser.add_argument("--job_type", type=str, default="finetune",
                        help="W&B job type label. (default: finetune)")
    parser.add_argument("--log_decoded_batches",
                        type=lambda x: str(x).lower() in {"1", "true", "yes"},
                        default=False,
                        help="Log decoded training batches to W&B as an artifact. "
                             "Only works with --trainer_mode=manual. (default: false)")

    # --- Hugging Face ---
    parser.add_argument("--hf_token", type=str, default=None,
                        help="Hugging Face access token. "
                             "If not set, uses the token stored by 'huggingface-cli login'.")

    # --- Advanced / rarely changed ---
    parser.add_argument("--gradient_checkpointing",
                        type=lambda x: str(x).lower() in {"1", "true", "yes"},
                        default=False,
                        help="Enable gradient checkpointing to save VRAM at the cost of speed. (default: false)")
    parser.add_argument("--ddp_find_unused_parameters",
                        type=lambda x: str(x).lower() in {"1", "true", "yes"},
                        default=False,
                        help="Advanced: set to true only if you get DDP unused parameter errors. (default: false)")

    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Sanity checks
    # ------------------------------------------------------------------
    if args.few_shot_training:
        if args.trainer_mode != "manual":
            raise ValueError(
                "--few_shot_training=True requires --trainer_mode=manual. "
                "The default SFT trainer does not support few-shot mixing."
            )
        if not (0.0 <= args.few_shot_ratio <= 1.0):
            raise ValueError("--few_shot_ratio must be between 0.0 and 1.0.")
        if args.few_shot_k_min < 1:
            raise ValueError("--few_shot_k_min must be >= 1.")
        if args.few_shot_k_max < args.few_shot_k_min:
            raise ValueError("--few_shot_k_max must be >= --few_shot_k_min.")

    return args


if __name__ == "__main__":
    main()