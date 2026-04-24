# src/training/manual/checkpoint_utils.py

import os
import torch
import torch.distributed as dist

try:
    from peft import PeftModel
    PEFT_AVAILABLE = True
except Exception:
    PEFT_AVAILABLE = False


def reload_best_checkpoint(model, accelerator, checkpoint_dir: str):
    """
    Load a LoRA checkpoint from `checkpoint_dir` into the current model.

    If the model is already a PeftModel (the common case during training),
    the adapter weights are loaded in-place via load_state_dict to avoid
    double-wrapping, which breaks generation and yields 0% accuracy.

    If the model is a plain base model (e.g. during standalone predict),
    PeftModel.from_pretrained wraps it normally.

    All ranks call this function; loading from a shared filesystem means
    no explicit broadcast is needed.
    """
    if checkpoint_dir in (None, "", "None"):
        accelerator.print("[reload_best_checkpoint] No checkpoint provided. Skipping.")
        return model

    if not os.path.isdir(checkpoint_dir):
        raise FileNotFoundError(f"[reload_best_checkpoint] Checkpoint folder not found: {checkpoint_dir}")

    files = set(os.listdir(checkpoint_dir))
    required = {"adapter_config.json"}
    has_weights = ("adapter_model.safetensors" in files) or ("adapter_model.bin" in files)
    if not (required.issubset(files) and has_weights):
        raise RuntimeError(
            f"[reload_best_checkpoint] Not a LoRA-only checkpoint. Found: {sorted(files)}"
        )

    accelerator.print(f"[reload_best_checkpoint] Loading LoRA adapter from: {checkpoint_dir}")

    base = accelerator.unwrap_model(model)

    if PEFT_AVAILABLE and isinstance(base, PeftModel):
        # Model is already a PeftModel — load adapter weights in-place.
        # PeftModel.from_pretrained on an existing PeftModel creates a
        # doubly-wrapped model that breaks generation (0% accuracy).
        weights_path = os.path.join(checkpoint_dir, "adapter_model.safetensors")
        bin_path = os.path.join(checkpoint_dir, "adapter_model.bin")

        if os.path.exists(weights_path):
            try:
                from safetensors.torch import load_file
                state_dict = load_file(weights_path, device=str(accelerator.device))
            except ImportError:
                # Fallback: load to CPU then move
                from safetensors.torch import load_file as _lf
                state_dict = {k: v.to(accelerator.device) for k, v in _lf(weights_path).items()}
        elif os.path.exists(bin_path):
            state_dict = torch.load(bin_path, map_location=accelerator.device)
        else:
            raise FileNotFoundError(f"[reload_best_checkpoint] No adapter weights found in {checkpoint_dir}")

        missing, unexpected = base.load_state_dict(state_dict, strict=False)
        if unexpected:
            accelerator.print(f"[reload_best_checkpoint] Unexpected keys: {unexpected[:5]}")
        accelerator.print(
            f"[reload_best_checkpoint] In-place adapter reload done "
            f"({len(state_dict)} tensors, {len(missing)} non-adapter params skipped)."
        )
    else:
        # Base model not yet wrapped — wrap with PeftModel normally.
        peft_model = PeftModel.from_pretrained(base, checkpoint_dir, is_trainable=False)
        model = peft_model

    accelerator.wait_for_everyone()
    accelerator.print("[reload_best_checkpoint] LoRA adapter loaded on all ranks.")
    return model
