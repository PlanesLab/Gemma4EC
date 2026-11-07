# gemma4ec/src/training/callbacks.py

from transformers import TrainerCallback
import os
import math

class ECValidationCallback(TrainerCallback):
    def __init__(self, accelerator, tokenizer, val_ds, args):
        self.accelerator = accelerator
        self.tokenizer = tokenizer
        self.val_ds = val_ds
        self.args = args
        self.monitor = getattr(args, "monitor_metric", "accuracy")
        self.greater_is_better = bool(getattr(args, "greater_is_better", True))
        self.save_best = bool(getattr(args, "save_best", True))
        self.best = None
        self.patience = int(getattr(args, "early_stopping_patience", 0))
        self.no_improve = 0
        self.best_dir = os.path.join(str(getattr(args, "output_folder","./results")), "best")

    def on_epoch_end(self, args, state, control, **kwargs):
        # Solo en main process y si hay validación
        if not self.accelerator.is_main_process or self.val_ds is None:
            return control

        model = kwargs["model"]
        from ..evaluation.eval import evaluate_model

        ep = int(state.epoch) if state.epoch is not None else -1
        self.accelerator.print(f"\n[epoch {ep}] Running EC validation on '{self.monitor}' metric...")

        # Eval -> unpack (preds, labels, smiles, metrics)
        model.eval()
        eval_out = evaluate_model(
            self.accelerator, model, self.tokenizer,
            self.val_ds, self.args, split="val", save_predictions=False,
            epoch=ep,
        )
        model.train()

        _, _, _, metrics = eval_out
        current = float(metrics.get(self.monitor, float('nan')))
        improved = (self.best is None) or ((current > self.best) if self.greater_is_better else (current < self.best))

        self.accelerator.print(f"[epoch {ep}] Validation {self.monitor} = {current:.4f}")
        if self.best is not None:
            self.accelerator.print(f"[epoch {ep}] Previous best {self.monitor} = {self.best:.4f}")
        else:
            self.accelerator.print(f"[epoch {ep}] No previous best — initializing.")

        if improved and not math.isnan(current):
            self.accelerator.print(f"[epoch {ep}] Metric improved! ({'>' if self.greater_is_better else '<'} direction)")
            self.best = current
            self.no_improve = 0

            if self.save_best:
                os.makedirs(self.best_dir, exist_ok=True)
                try:
                    model.save_pretrained(self.best_dir)
                except Exception:
                    # Por si está envuelto por Accelerate/TRL
                    from accelerate import Accelerator
                    Accelerator().unwrap_model(model).save_pretrained(self.best_dir)
                self.accelerator.print(
                    f"[epoch {ep}] 💾 Best model saved to: {self.best_dir} "
                    f"(metric={self.monitor}, value={current:.4f})"
                )
        else:
            self.no_improve += 1
            self.accelerator.print(
                f"[epoch {ep}]  No improvement on '{self.monitor}' for {self.no_improve} eval(s)."
            )
            if self.patience > 0 and self.no_improve >= self.patience:
                self.accelerator.print(
                    f"[early stop] No improvement on '{self.monitor}' for {self.no_improve} evals. Stopping."
                )
                control.should_training_stop = True
        return control