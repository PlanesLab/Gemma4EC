# gemma4ec/src/train.py

import os
from trl import SFTTrainer, SFTConfig
from peft import LoraConfig

from .formatting import formatting_func

def build_trainer(train_ds, model, args) -> SFTTrainer:
    """
    Builds an SFTTrainer using the `model` in main.py
    (LoRA applied and, if applicable, gradient checkpointing enabled).
    Does NOT call get_peft_model nor modify use_cache here.
    
    """
    # Initialize the trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=train_ds,
        args=SFTConfig(
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            warmup_steps=args.warmup_steps,
            num_train_epochs=args.num_train_epochs,
            learning_rate=args.learning_rate,
            fp16=getattr(args, "fp16", False),
            # (Opcional si lo añades en main.py) bf16=getattr(args, "bf16", False),
            logging_steps=args.logging_steps,
            max_seq_length=args.max_seq_length,
            group_by_length=True, # Activa bucketing por longitud para reducir padding -> menos picos de memoria
            #packing=False,                # ¡asegúralo explícitamente!
            accelerator_config={"use_seedable_sampler": False},  
            seed=42, # global seed (dropout, init, etc.)
            output_dir=args.output_folder,
            optim=getattr(args, "optimizer", "adamw_torch"),
            report_to="wandb", 
            lr_scheduler_type=getattr(args, "lr_scheduler_type", "linear"),
            weight_decay=getattr(args, "weight_decay", 0.0),
            gradient_checkpointing=getattr(args, "gradient_checkpointing", False),
            ddp_find_unused_parameters=getattr(args, "ddp_find_unused_parameters", False)
        ),
    
        formatting_func=formatting_func,
    )
    return trainer # model, trainer