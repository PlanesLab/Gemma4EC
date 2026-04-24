# gemma4ec/src/training/manual/batch_logging.py 
 
import os, time
import wandb

def _open_decoded_log(args, accelerator):
    """
    Open the log file (only in the main process) if --log_decoded_batches=true.
    Returns (file_handle, path) or (None, None).
    """
    want = bool(getattr(args, "log_decoded_batches", False))
    if not want:
        if accelerator.is_main_process:
            print("[decoded-log] desactivado (--log_decoded_batches=false)")
        return None, None
    out_dir = str(getattr(args, "output_folder", "./results"))
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "decoded_inputs.log")
    print(f"[decoded-log] abriendo fichero en {path}")
    f = open(path, "a", encoding="utf-8")
    f.write(f"# Decoded inputs log — {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    return f, path

def _log_decoded_batch(log_f, tokenizer, input_ids, epoch, batch_idx, max_len, pad_id):
    if log_f is None:
        return
    ids = input_ids.detach().to("cpu").tolist()
    texts = tokenizer.batch_decode(ids, skip_special_tokens=False)
    log_f.write(f"\n## epoch={epoch} batch={batch_idx} max_len={max_len}\n")
    for i, (seq_ids, txt) in enumerate(zip(ids, texts)):
        eff_len = sum(1 for t in seq_ids if (pad_id is None) or (t != pad_id))
        log_f.write(f"[sample {i}] eff_len={eff_len}\n")
        log_f.write(txt.replace("\r", "") + "\n")

def _finalize_decoded_log(log_f, path, accelerator):
    if log_f is None:
        return
    log_f.flush(); log_f.close()
    if accelerator.is_main_process and wandb.run is not None and path is not None:
        art = wandb.Artifact("decoded_inputs", type="text")
        art.add_file(path)
        wandb.log_artifact(art)

