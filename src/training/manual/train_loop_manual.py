# gemma4ec/src/train_loop_manual.py

import math
import time
import os
from contextlib import ExitStack
from itertools import chain
from typing import Optional
import wandb

import torch
from torch.utils.data import DataLoader
from transformers import get_scheduler
from accelerate import Accelerator
from tqdm import tqdm

from ...evaluation.eval import evaluate_model
from ..formatting import formatting_func

from .collate_fns import _make_collate_fn, _make_collate_fn_fewshot
from .iterator_debug import _first_signature_from_iterator
from .sampler_utils import _set_epoch_on_sampler, _reseed_for_epoch
from .checkpoint_utils import reload_best_checkpoint

from .batch_logging import _open_decoded_log, _log_decoded_batch, _finalize_decoded_log
from .ops import _pick_optimizer, _pick_scheduler, _token_acc_from_logits, _global_grad_norm

# ------------------------------
# Entrenamiento manual con logs
# ------------------------------
def train_manual(
    *, 
    train_ds,   # data["train"] , datasets.Dataset 
    val_ds=None,  
    model, tokenizer,
    args,
    accelerator: Optional[Accelerator] = None):
    """
    Manual training loop that mirrors SFTTrainer behavior but with transparent logging.
    - Trains on 'data["train"]'
    - Uses labels = input_ids (padding masked), identical to SFT-style causal LM training
    - Periodic logs of loss, LR, tokens/s, token-accuracy, and per-epoch sampler signature
    - Supports EC-number validation at epoch end, early stopping, and best-model checkpointing
    - (Future) Few-shot training support
    """
    accelerator = accelerator or Accelerator()

    # --- Fijar subset determinista de validación (máx 1000 samples) ---
    val_eval_ds = None
    if val_ds is not None:
        n_val = len(val_ds)
        max_eval_samples = 1000
        subset_n = min(n_val, max_eval_samples)
        val_eval_ds = val_ds.select(range(subset_n))

        if accelerator.is_main_process:
            accelerator.print(
                f"[setup] Validation will use a fixed subset of {subset_n}/{n_val} "
                f"samples on every eval."
            )

    # --- Parity/safety with Trainer around padding ---
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token or tokenizer.unk_token
    if getattr(model.config, "pad_token_id", None) is None:
        model.config.pad_token_id = tokenizer.pad_token_id
    pad_id = tokenizer.pad_token_id

    # En un map‐style datasets.Dataset (como el tuyo, no streaming) esto añade una columna de enteros 0..N−1.
    if "__row_id__" not in train_ds.column_names:
        train_ds = train_ds.add_column("__row_id__", list(range(len(train_ds))))

    # --- Collate / DataLoader setup ---
    trainer_mode = str(getattr(args, "trainer_mode", "manual")).lower()
    few_shot_enabled = bool(getattr(args, "few_shot_training", False))

    if few_shot_enabled and trainer_mode != "manual":
        raise ValueError(
            f"Few-shot training is only supported in manual mode, not in trainer_mode='{trainer_mode}'."
        )

    # Common parameters
    max_len = int(getattr(args, "max_seq_length", 512))
    bs = int(getattr(args, "batch_size", 16))

    # Decide which collate to use
    if few_shot_enabled:
        few_shot_ratio = float(getattr(args, "few_shot_ratio", 0.3))
        k_min = int(getattr(args, "few_shot_k_min", 1))
        k_max = int(getattr(args, "few_shot_k_max", 10))
        seed = int(getattr(args, "seed", 42))

        accelerator.print(
            f"[setup] ⚡ Few-shot training ENABLED | ratio={few_shot_ratio}, k∈[{k_min},{k_max}], seed={seed}"
        )

        collate_fn = _make_collate_fn_fewshot(
            tokenizer,
            formatting_func,
            max_len,
            few_shot_ratio=few_shot_ratio,
            k_min=k_min,
            k_max=k_max,
            pool_inputs=train_ds["input_text"],
            pool_outputs=train_ds["output_text"],
            seed=seed,
        )

    else:
        accelerator.print("[setup] Standard zero-shot collate")
        collate_fn = _make_collate_fn(tokenizer, formatting_func, max_len)

    # --- Build DataLoader ---
    train_dl = DataLoader(
        train_ds,
        batch_size=bs,
        shuffle=True,
        drop_last=True,
        collate_fn=collate_fn,
        pin_memory=True,
        #num_workers=2,
    )

    # Optimizer
    optimizer = _pick_optimizer(model, args)
    grad_acc_steps = int(getattr(args, "gradient_accumulation_steps", 1))
    epochs = int(getattr(args, "num_train_epochs", 1))

    # --- Accelerate DDP/AMP: preparar SIN scheduler ---
    model, optimizer, train_dl = accelerator.prepare(model, optimizer, train_dl)

    # --- Ahora que el DataLoader ya está shardead@, calculamos tamaños reales ---
    micro_batches_per_epoch = len(train_dl)                              # post-shard
    steps_per_epoch = math.ceil(micro_batches_per_epoch / max(1, grad_acc_steps))
    total_steps = steps_per_epoch * epochs

    # Scheduler con el nº correcto de optimizer steps (no se pasa a prepare)
    scheduler = _pick_scheduler(optimizer, args, num_training_steps=total_steps)

    # ---- W&B metric definitions (solo en main process) ----
    if accelerator.is_main_process and wandb.run is not None:
        wandb.define_metric("train/global_step")
        wandb.define_metric("train/*", step_metric="train/global_step")
        wandb.define_metric("epoch")
        wandb.define_metric("val/*",  step_metric="epoch")
        wandb.define_metric("test/*", step_metric="epoch")

    # ---- Setup print + W&B log (claridad total del plan de entrenamiento) ----
    if accelerator.is_main_process:
        world = accelerator.num_processes
        eff_global_batch = bs * grad_acc_steps * world
        accelerator.print(
            "[setup] world_size={} | batch_size/device={} | grad_acc_steps={}\n"
            "[setup] micro_batches_per_epoch={} | steps_per_epoch={} | total_steps={}\n"
            "[setup] effective_global_batch={} samples/update".format(
                world, bs, grad_acc_steps,
                micro_batches_per_epoch, steps_per_epoch, total_steps,
                eff_global_batch,
            )
        )
        if wandb.run is not None:
            wandb.log({
                "setup/world_size": world,
                "setup/batch_per_device": bs,
                "setup/grad_acc_steps": grad_acc_steps,
                "setup/micro_batches_per_epoch": micro_batches_per_epoch,
                "setup/steps_per_epoch": steps_per_epoch,
                "setup/total_steps": total_steps,
                "setup/effective_global_batch": eff_global_batch,
            }, step=0)

    # ---- Decoded-batch logging (solo en main process) ----
    decoded_log_f, decoded_log_path = _open_decoded_log(args, accelerator)
    accelerator.print(f"[debug] is_main_process={accelerator.is_main_process} "
                  f"log_decoded_batches={getattr(args,'log_decoded_batches', None)} "
                  f"out_dir={getattr(args,'output_folder', None)} "
                  f"path={decoded_log_path}")

    # === Training ===
    base_seed = 42
    model.train()

    global_step = 0
    log_every = max(1, int(getattr(args, "logging_steps", 50)))

    last_log_t = time.time()
    pbar = tqdm(total=total_steps, disable=not accelerator.is_main_process, dynamic_ncols=True)
    pbar.set_description("train")

    win_loss = 0.0
    win_tokens = 0
    win_acc_correct = 0
    win_acc_total = 0
    cum_tokens = 0

    # --- Early stop & best checkpoint config ---
    best_metric = None
    epochs_without_improve = 0
    monitor = getattr(args, "monitor_metric", "accuracy")
    greater_is_better = bool(getattr(args, "greater_is_better", True))
    eval_every = int(getattr(args, "eval_every_epochs", 0))
    save_best = bool(getattr(args, "save_best", False))
    best_dir = os.path.join(str(getattr(args, "output_folder","./results")), "best")

    for epoch in range(epochs):
        # 2) Multi-GPU: intenta set_epoch sobre el DistributedSampler ya shardeado por Accelerate
        applied = _set_epoch_on_sampler(train_dl, epoch)
        
        # 3) Single-proc / 1 GPU (RandomSampler): resemilla si no pudimos set_epoch
        if not applied:
            _reseed_for_epoch(base_seed, epoch)
        
        # 4) # Firma real del iterador que vamos a consumir: así verificas el reshuffle por época
        (first_batch, sig), it = _first_signature_from_iterator(train_dl, max_batches=2, max_ids=32)
        accelerator.print(f"[epoch {epoch}] set_epoch_applied={applied} | signature={sig}")
        if first_batch is None:
            accelerator.print(f"[epoch {epoch}] empty dataloader. Stopping.")
            break

        micro_steps_processed = 0

        # 5) # ---- Main training loop over batches : Entrenamiento con el mismo iterador (primero el batch ya extraído) ----
        for step, batch in enumerate(chain([first_batch], it), start=0):
            # DDP: all-reduce gradients only on the micro-batch that completes an optimizer update
            # (or the last of the epoch, which feeds the remainder update below). Both forward and
            # backward must run inside no_sync for DDP to skip the all-reduce.
            sync_now = ((step + 1) % max(1, grad_acc_steps) == 0) or (step + 1 == micro_batches_per_epoch)
            sync_ctx = ExitStack()
            if not sync_now:
                sync_ctx.enter_context(accelerator.no_sync(model))

            with accelerator.autocast(): # activa AMP (fp16/bf16) de forma segura según la config de Accelerate. Es lo mismo que hace Trainer cuando le pasas fp16=True/bf16=True: 
                                        # operaciones en media precisión para acelerar y reducir VRAM, manteniendo la estabilidad.
                mb = {k: v.to(accelerator.device) for k, v in batch.items() if k != "row_ids"}
                out = model(**mb) # HF CausalLM devuelve .loss si pasas labels 
                loss = out.loss

            # Logging of the text fed into the model (only main process)
            if decoded_log_f is not None and accelerator.is_main_process:
                _log_decoded_batch(decoded_log_f, tokenizer, mb["input_ids"], epoch, step, max_len, pad_id)

            # --- token-level accuracy (global sync) ---
            if hasattr(out, "logits"):
                c_local, t_local = _token_acc_from_logits(out.logits, mb["labels"])
                _acc_tensor = torch.tensor([c_local, t_local], device=mb["input_ids"].device)

                gathered = accelerator.gather(_acc_tensor)
                
                # Reshape to (num_gpus, 2) and sum across GPUs
                gathered = gathered.view(-1, 2)
                summed = gathered.sum(dim=0)
                c_global, t_global = summed.tolist()

                win_acc_correct += c_global
                win_acc_total += t_global

            mb_tokens_local = int(mb["attention_mask"].sum().item()) if "attention_mask" in mb else int(mb["input_ids"].numel())
            _tok_tensor = torch.tensor([mb_tokens_local], device=mb["input_ids"].device)
            mb_tokens_global = int(accelerator.gather(_tok_tensor).sum().item())
            cum_tokens += mb_tokens_global
            win_tokens += mb_tokens_global

            # --- grad accumulation ---
            loss = loss / max(1, grad_acc_steps) # Así, cada micro-batch aporta 1/N del gradiente medio; cuando sumas N veces, obtienes exactamente el gradiente medio del batch grande.
            accelerator.backward(loss) # (acumulando gradientes en param.grad)
            sync_ctx.close()
            win_loss += loss.item()

             # --- contamos micro-batches de la época ---
            micro_steps_processed += 1

            # cuando completes N micro-batches -> 1 update lógico
            if (step + 1) % grad_acc_steps == 0: # Condición de sincronización de acumulación: tras consumir grad_accum_steps micro-batches, hacemos una actualización real.
         
                # gradient clipping (paridad con SFTTrainer)
                max_gn = float(getattr(args, "max_grad_norm", 1.0))
                grad_norm = accelerator.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad], max_gn
                )

                optimizer.step() # actualiza pesos (en tu caso, principalmente los de LoRA con requires_grad=True). Igual que en SFTTrainer.
                scheduler.step() # avanza el LR scheduler una vez por actualización de optimizador.
                optimizer.zero_grad(set_to_none=True)
                global_step += 1
                pbar.update(1)

                # --- logging cada logging_steps ---
                if (global_step % log_every) == 0:
                    now = time.time()
                    dt = max(1e-9, now - last_log_t)
                    avg_loss = win_loss / log_every
                    mean_token_acc = (win_acc_correct / max(1, win_acc_total)) if win_acc_total > 0 else 0.0
                    lr = scheduler.get_last_lr()[0] if hasattr(scheduler, "get_last_lr") else optimizer.param_groups[0]["lr"]

                    if accelerator.is_main_process and wandb.run is not None:
                        wandb.log({
                            "train/global_step": global_step,
                            "train/num_tokens": cum_tokens,
                            "train/mean_token_accuracy": mean_token_acc,
                            "train/loss": avg_loss,
                            "train/learning_rate": lr,
                            "train/grad_norm": grad_norm,
                        })
                    
                    # consola similar al trainer
                    tok_per_s = win_tokens / dt
                    accelerator.print(
                        f"step {global_step:>6d} | epoch {epoch + (step+1)/(len(train_dl)):.2f} "
                        f"| loss {avg_loss:.4f} | acc {mean_token_acc:.3f} "
                        f"| lr {lr:.2e} | grad_norm {grad_norm:.3f} | tokens/s {tok_per_s:.1f}"
                    )

                    # reset ventana
                    win_loss = 0.0
                    win_tokens = 0
                    win_acc_correct = 0
                    win_acc_total = 0
                    last_log_t = now
                    
                # fin de época temprana si ya llegamos al total (seguridad)
                if global_step >= total_steps:
                    break

        if (micro_steps_processed % grad_acc_steps) != 0 and global_step < total_steps:
            has_grads = any((p.grad is not None) for p in model.parameters() if p.requires_grad)
            if has_grads:
                max_gn = float(getattr(args, "max_grad_norm", 1.0))
                _ = accelerator.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad],
                    max_gn
                )
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                global_step += 1
                pbar.update(1)

        # ---- EC validation at epoch end ----
        if val_eval_ds is not None and eval_every > 0 and ((epoch + 1) % eval_every == 0):
            accelerator.wait_for_everyone() 

            if accelerator.is_main_process:
                accelerator.print( f"\n[epoch {epoch}] Running EC validation on fixed subset "
                    f"of {len(val_eval_ds)} samples (deterministic)."
                )
                
            model.eval()

            preds, labels, smiles, metrics = evaluate_model(
                accelerator, model, tokenizer, val_eval_ds, args,
                split="val", save_predictions=False, epoch=epoch,
            )
            model.train()

            # Solo rank 0 tiene metrics relleno
            current_val = float("nan")
            if accelerator.is_main_process:
                current_val = float(metrics.get(monitor, float("nan")))
                accelerator.print(f"[epoch {epoch}] Validation {monitor} = {current_val:.4f}")
                if best_metric is not None:
                    accelerator.print(f"[epoch {epoch}] Previous best {monitor} = {best_metric:.4f}")
                else:
                    accelerator.print(f"[epoch {epoch}] No previous best — initializing.")

                del metrics
                torch.cuda.empty_cache()

            # --- Broadcast del valor de la métrica a todos los ranks ---
            cur_tensor = torch.tensor([current_val], device=accelerator.device)
            gathered = accelerator.gather(cur_tensor)  # [val_rank0, val_rank1, ...]
            current = float(gathered[0].item()) # from_process=0 asegura que se propaga el valor de rank 0

            improved = (best_metric is None) or ((current > best_metric) if greater_is_better else (current < best_metric))

            if accelerator.is_main_process:
                if improved:
                    accelerator.print(f"[epoch {epoch}] ✅ Metric improved! ({'>' if greater_is_better else '<'} direction)")
                else:
                    accelerator.print(f"[epoch {epoch}] ❌ No improvement on '{monitor}' "
                                    f"(best so far: {best_metric if best_metric is not None else 'N/A'})")

            # Update all ranks with same logic
            if improved:
                best_metric = current
                epochs_without_improve = 0

                if save_best and accelerator.is_main_process:
                    os.makedirs(best_dir, exist_ok=True)
                    try:
                        model.save_pretrained(best_dir)
                    except Exception:
                        accelerator.unwrap_model(model).save_pretrained(best_dir)
                    accelerator.print(f"[epoch {epoch}] 💾 Best model saved to: {best_dir} "
                                    f"(metric={monitor}, value={current:.4f})")
            else:
                epochs_without_improve += 1
                if accelerator.is_main_process:
                    accelerator.print(f"[epoch {epoch}] patience={epochs_without_improve}/"
                                    f"{int(getattr(args,'early_stopping_patience',0))}")

            # --- Early stopping sincronizado ---
            stop_flag = (
                int(getattr(args, "early_stopping_patience", 0)) > 0
                and epochs_without_improve >= int(getattr(args, "early_stopping_patience", 0))
            )
            stop_tensor = torch.tensor([int(stop_flag)], device=accelerator.device)
            stop_gather = accelerator.gather(stop_tensor)   # [flag_rank0, flag_rank1, ...]
            should_stop = bool(int(stop_gather[0].item()))  # todos miran el de rank 0

            if should_stop and accelerator.is_main_process:
                accelerator.print(f"[early stop] No improvement on '{monitor}' for "
                                f"{epochs_without_improve} evals. Stopping.")
               
            accelerator.wait_for_everyone()
            if should_stop:
                break

        if accelerator.is_main_process and wandb.run is not None:
            wandb.log({"epoch": epoch}, commit=False)

        if global_step >= total_steps:
            break

    pbar.close()
    accelerator.print(f"Training finished. total_steps={global_step}")
 
    # Close decoded batch logging and upload the artefact
    _finalize_decoded_log(decoded_log_f, decoded_log_path, accelerator)

    # --- Reload best checkpoint before returning ---
    if getattr(args, "save_best", False):
        accelerator.print("[re-load model] Re-loading best model")
        best_dir = os.path.join(str(getattr(args, "output_folder", "./results")), "best")
        model = reload_best_checkpoint(model, accelerator, best_dir)
        
        # ---- DEBUG: verificar que el best LoRA está cargado ----
        unwrapped = accelerator.unwrap_model(model)
        if accelerator.is_main_process:
            has_lora = any("lora" in n.lower() for n, _ in unwrapped.named_parameters())
            accelerator.print(f"[train][sanity] Best LoRA loaded: {has_lora}")

    try:
        return accelerator.unwrap_model(model)
    except Exception:
        return model