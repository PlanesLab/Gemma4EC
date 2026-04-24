# src/config.py

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, Optional
from argparse import Namespace
import os

_DEFAULT_TARGET_MODULES = ["q_proj", "o_proj", "k_proj", "v_proj", "gate_proj", "up_proj", "down_proj"]

@dataclass(frozen=True)
class Config:
    # === Paths ===
    raw_data_folder: str
    processed_data_folder: str
    output_folder: str = "./results"
    model_id: str = "google/txgemma-2b-predict"
    save_directory: str = "./local_txgemma_model"
    cache_dir: str = "./cache"

    # === Prompts ===
    prompts_json_path: str = ""
    template_key: str = "EC_NUMBER_PROMPT_1"
    template_alias: str = "EC_NUMBER"

    # === Training ===
    batch_size: int = 16
    eval_batch_size: int = 64
    gradient_accumulation_steps: int = 4
    warmup_steps: int = 2
    num_train_epochs: int = 5
    learning_rate: float = 5e-6
    fp16: bool = True
    logging_steps: int = 5
    max_seq_length: int = 512
    optimizer: str = "paged_adamw_8bit"
    lr_scheduler_type: str = "linear"
    weight_decay: float = 0.0
    trainer_mode: str = "sft"  # 'sft' | 'manual'

    # === PEFT ===
    adapter_method: str = "lora"
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.0
    target_modules: Optional[Iterable[str]] = None
    task_type: str = "CAUSAL_LM"

    # === Seq length check ===
    seqcheck_enabled: bool = True
    seqcheck_subset: int = 20000
    seqcheck_batch_size: int = 1024
    fail_on_truncation: bool = True
    truncation_tolerance: float = 0.01

    # === Few-shot ===
    few_shot_training: bool = False
    few_shot_ratio: float = 0.3
    few_shot_k_min: int = 1
    few_shot_k_max: int = 10

    # === W&B ===
    wandb_project: str = ""
    wandb_entity: str = ""
    wandb_tags: Iterable[str] = field(default_factory=lambda: ["TxGemma", "EC"])
    job_type: str = "finetune"

    # === HF / DDP ===
    hf_token: Optional[str] = None
    use_test: bool = False
    gradient_checkpointing: bool = False
    ddp_find_unused_parameters: bool = False

    # === Derived / resolved ===
    resolved_target_modules: Iterable[str] = field(default_factory=list)

    @staticmethod
    def from_args(args: Namespace) -> "Config":
        """Create Config from argparse.Namespace without breaking existing pipeline."""
        d = vars(args).copy()

        # Resolve target_modules; fall back to defaults if not provided
        tmods = d.get(“target_modules”)
        resolved = tmods if tmods else _DEFAULT_TARGET_MODULES

        # Normalize wandb_tags (may arrive as list, tuple, or string)
        tags = d.get(“wandb_tags”)
        if isinstance(tags, str):
            tags = [tags]
        elif tags is None:
            tags = [“TxGemma”, “EC”]

        return Config(
            raw_data_folder=d["raw_data_folder"],
            processed_data_folder=d["processed_data_folder"],
            output_folder=d.get("output_folder", "./results"),
            model_id=d.get("model_id", "google/txgemma-2b-predict"),
            save_directory=d.get("save_directory", "./local_txgemma_model"),
            cache_dir=d.get("cache_dir", "./cache"),
            prompts_json_path=d["prompts_json_path"],
            template_key=d.get("template_key", "EC_NUMBER_PROMPT_1"),
            template_alias=d.get("template_alias", "EC_NUMBER"),
            batch_size=d.get("batch_size", 16),
            eval_batch_size=d.get("eval_batch_size", 64),
            gradient_accumulation_steps=d.get("gradient_accumulation_steps", 4),
            warmup_steps=d.get("warmup_steps", 2),
            num_train_epochs=d.get("num_train_epochs", 5),
            learning_rate=d.get("learning_rate", 5e-6),
            fp16=d.get("fp16", True),
            logging_steps=d.get("logging_steps", 5),
            max_seq_length=d.get("max_seq_length", 512),
            optimizer=d.get("optimizer", "paged_adamw_8bit"),
            lr_scheduler_type=d.get("lr_scheduler_type", "linear"),
            weight_decay=d.get("weight_decay", 0.0),
            trainer_mode=d.get("trainer_mode", "sft"),
            adapter_method=d.get("adapter_method", "lora"),
            lora_r=d.get("lora_r", 8),
            lora_alpha=d.get("lora_alpha", 16),
            lora_dropout=d.get("lora_dropout", 0.0),
            task_type=d.get("task_type", "CAUSAL_LM"),
            seqcheck_enabled=d.get("seqcheck_enabled", True),
            seqcheck_subset=d.get("seqcheck_subset", 20000),
            seqcheck_batch_size=d.get("seqcheck_batch_size", 1024),
            fail_on_truncation=d.get("fail_on_truncation", True),
            truncation_tolerance=d.get("truncation_tolerance", 0.01),
            few_shot_training=d.get("few_shot_training", False),
            few_shot_ratio=d.get("few_shot_ratio", 0.3),
            few_shot_k_min=d.get("few_shot_k_min", 1),
            few_shot_k_max=d.get("few_shot_k_max", 10),
            wandb_project=d.get("wandb_project", ""),
            wandb_entity=d.get("wandb_entity", ""),
            wandb_tags=tags,
            job_type=d.get("job_type", "finetune"),
            hf_token=d.get("hf_token"),
            use_test=d.get("use_test", False),
            gradient_checkpointing=d.get("gradient_checkpointing", False),
            ddp_find_unused_parameters=d.get("ddp_find_unused_parameters", False),
            target_modules=resolved, # resolved_target_modules
        )

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)

    def wandb_config(self) -> Dict[str, Any]:
        """Return a clean config dict (secrets removed) suitable for wandb.config."""
        d = self.asdict().copy()
        d.pop("hf_token", None)
        return d

    def env_applied(self) -> "Config":
        """Apply optional global side-effects (e.g. HF_TOKEN) and return self."""
        if self.hf_token:
            os.environ["HF_TOKEN"] = self.hf_token
        return self
