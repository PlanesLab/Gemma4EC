"""
predict.py — Run EC number prediction with a fine-tuned Gemma4EC adapter.

Authors: Joseba Sancho, Josefina Arcagni
Date: 2025-02-25

Minimal usage:
    python predict.py \
        --raw_data_file reactions.csv \
        --model_checkpoint_folder models/Gemma4EC-9B-Predict

Full usage:
    python predict.py \
        --raw_data_file reactions.csv \
        --processed_data_folder outputs/inter_data \
        --output_folder outputs/results \
        --model_checkpoint_folder models/Gemma4EC-9B-Predict \
        --model_id google/txgemma-9b-predict
"""

import os
import argparse
from pathlib import Path

import wandb
from accelerate import Accelerator
from datasets import load_dataset

from src.datamod.templates import build_input_template_from_file
from src.datamod.jsonl_builder import create_jsonl_from_df
from src.utils.paths import get_jsonl_path
from src.models.modeling import build_model_and_tokenizer
from src.evaluation.eval import evaluate_model
from src.training.manual.checkpoint_utils import reload_best_checkpoint

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
    # Prompt template
    # ------------------------------------------------------------------
    input_template = build_input_template_from_file(
        template_path=args.prompts_json_path,
        key=args.template_key,
        required_vars={"reaction_smiles"},
        dict_key=args.template_alias,
    )

    # ------------------------------------------------------------------
    # Output paths
    # ------------------------------------------------------------------
    processed_dir = Path(args.processed_data_folder)
    processed_dir.mkdir(parents=True, exist_ok=True)
    Path(args.output_folder).mkdir(parents=True, exist_ok=True)

    jsonl_path = get_jsonl_path(
        str(processed_dir),
        "predict",
        args.template_alias,
        args.template_key,
    )

    # ------------------------------------------------------------------
    # Optional W&B logging (main process only)
    # ------------------------------------------------------------------
    if accelerator.is_main_process and args.wandb_entity is not None:
        tags = ["predict", "Gemma4EC", "script:predict.py"]
        mid = args.model_id.lower()
        if "9b-predict" in mid:
            tags.append("model:txgemma-9b-predict")
        elif "2b-predict" in mid:
            tags.append("model:txgemma-2b-predict")
        else:
            tags.append(f"model:{args.model_id}")
        tags.append("train:few-shot" if args.few_shot_trained else "train:no-shot")
        if args.wandb_tags:
            tags.extend(args.wandb_tags)

        wandb.init(
            project=args.wandb_project,
            entity=args.wandb_entity,
            tags=tags,
            job_type="predict",
            config={
                "model_id": args.model_id,
                "template_key": args.template_key,
                "template_alias": args.template_alias,
                "eval_batch_size": args.eval_batch_size,
                "checkpoint_folder": args.model_checkpoint_folder,
            },
        )

    # ------------------------------------------------------------------
    # Build JSONL (main process) then wait for all ranks
    # ------------------------------------------------------------------
    if accelerator.is_main_process:
        print(f"[predict] Building JSONL: {args.raw_data_file} → {jsonl_path}")
        create_jsonl_from_df(args.raw_data_file, jsonl_path, input_template)
    accelerator.wait_for_everyone()

    # ------------------------------------------------------------------
    # Load dataset
    # ------------------------------------------------------------------
    data = load_dataset("json", data_files={"pred": jsonl_path})

    # ------------------------------------------------------------------
    # Load base model + tokenizer
    # ------------------------------------------------------------------
    print(f"[predict] Loading base model : {args.model_id}")
    print(f"[predict] Cache directory    : {args.cache_dir}")
    model, tokenizer = build_model_and_tokenizer(
        args.model_id,
        args.save_directory,
        args.cache_dir,
    )

    # ------------------------------------------------------------------
    # Load fine-tuned LoRA adapter
    # ------------------------------------------------------------------
    print(f"[predict] Loading adapter from: {args.model_checkpoint_folder}")
    model = reload_best_checkpoint(model, accelerator, args.model_checkpoint_folder)

    # ------------------------------------------------------------------
    # Run inference
    # ------------------------------------------------------------------
    if accelerator.is_main_process:
        print("[predict] Running inference ...")
    evaluate_model(
        accelerator,
        model,
        tokenizer,
        data["pred"],
        args,
        split="pred",
        save_predictions=True,
    )
    accelerator.wait_for_everyone()

    if accelerator.is_main_process:
        print(f"[predict] Done. Results saved to: {args.output_folder}")
        if wandb.run is not None:
            wandb.finish()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Predict EC numbers using a fine-tuned Gemma4EC adapter.",
        allow_abbrev=False,
    )

    # --- Required ---
    parser.add_argument("--raw_data_file", type=str, required=True,
                        help="CSV file with a 'rxn_smiles' column.")
    parser.add_argument("--model_checkpoint_folder", type=str, required=True,
                        help="Path to the LoRA adapter folder "
                             "(must contain adapter_model.safetensors + adapter_config.json). "
                             "Download from: https://huggingface.co/PlanesLab/Gemma4EC-9B-Predict")

    # --- Paths (defaults match the repo structure) ---
    parser.add_argument("--processed_data_folder", type=str,
                        default="./outputs/inter_data",
                        help="Directory for intermediate JSONL files. (default: ./outputs/inter_data)")
    parser.add_argument("--output_folder", type=str,
                        default="./outputs/results",
                        help="Directory where the prediction TSV will be saved. "
                             "Filename format: predictions_pred.EC_NUMBER.EC_NUMBER_PROMPT_<prompt_number>.<timestamp>.tsv "
                             "(default: ./outputs/results)")
    parser.add_argument("--save_directory", type=str,
                        default="./local_txgemma_model",
                        help="Where to cache the downloaded base model. (default: ./local_txgemma_model)")
    parser.add_argument("--cache_dir", type=str,
                        default="./hfcache",
                        help="Hugging Face cache directory. (default: ./hfcache)")
    parser.add_argument("--prompts_json_path", type=str,
                        default="./prompt_examples/prompts.json",
                        help="Path to prompts.json. (default: ./prompt_examples/prompts.json)")

    # --- Model ---
    parser.add_argument("--model_id", type=str,
                        default="google/txgemma-9b-predict",
                        help="Base TxGemma model to load. "
                             "Use google/txgemma-2b-predict if you have <18GB VRAM. "
                             "(default: google/txgemma-9b-predict)")

    # --- Prompts ---
    parser.add_argument("--template_key", type=str,
                        default="EC_NUMBER_PROMPT_2",
                        help="Prompt template to use from prompts.json. "
                             "EC_NUMBER_PROMPT_2 is the recommended default.")
    parser.add_argument("--template_alias", type=str,
                        default="EC_NUMBER",
                        help="Internal alias for the prompt template. (default: EC_NUMBER)")

    # --- Inference ---
    parser.add_argument("--eval_batch_size", type=int,
                        default=32,
                        help="Batch size for inference. Reduce if you run out of VRAM. (default: 32)")

    # --- Hugging Face ---
    parser.add_argument("--hf_token", type=str,
                        default=None,
                        help="Hugging Face access token. "
                             "If not provided, uses the token stored by 'huggingface-cli login'.")

    # --- W&B (fully optional — disabled by default) ---
    parser.add_argument("--wandb_entity", type=str,
                        default=None,
                        help="Weights & Biases entity name. Leave unset to disable W&B logging entirely.")
    parser.add_argument("--wandb_project", type=str,
                        default="Gemma4EC-predictions",
                        help="W&B project name. Only used if --wandb_entity is set. (default: Gemma4EC-predictions)")
    parser.add_argument("--wandb_tags", type=str, nargs="+",
                        default=None,
                        help="Extra tags to add to the W&B run (optional).")
    parser.add_argument("--few_shot_trained",
                        type=lambda x: x.lower() in {"1", "true", "yes"},
                        default=False,
                        help="Set to true if this adapter was trained with few-shot prompts. (default: false)")

    # --- Internal / advanced ---
    parser.add_argument("--ddp_find_unused_parameters",
                        type=lambda x: x.lower() in {"1", "true", "yes"},
                        default=False,
                        help="Advanced: passed to TrainingArguments for DDP compatibility. (default: false)")

    return parser.parse_args()


if __name__ == "__main__":
    main()