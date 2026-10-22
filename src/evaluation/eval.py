# gemma4ec/src/evaluation/eval.py

import time
import os
import re
import pandas as pd
import torch
import torch.distributed as dist
from torch.utils.data import DataLoader
import wandb
from itertools import chain

from .dataset_eval import Smiles2ECDataset
from ..utils.metrics import compute_classification_metrics

ANSWER_MARKER = "Answer:"
EC_DOTS_RE = re.compile(r"^\d+(?:\.\d+){0,3}$")  # permite 1 a 4 partes

def parse_ec_raw(text: str) -> str:
    """
    Devuelve literalmente la PRIMERA LÍNEA tras *la ÚLTIMA* ocurrencia de 'Answer:'.
    Robusto a prompts que contienen ejemplos con múltiples Answer:
    """
    #tail = text.split(ANSWER_MARKER, 1)[1] if ANSWER_MARKER in text else text
    if ANSWER_MARKER in text:
        # Partir desde el FINAL → la parte relevante del modelo está en la última Answer:
        tail = text.rsplit(ANSWER_MARKER, 1)[-1]
    else:
        tail = text
    tail = tail.strip()
    if not tail:
        return ""
    return tail.splitlines()[0].strip()

def leading_ec_fragment(s: str) -> str:
    """
    Extrae sólo el tramo INICIAL compuesto por dígitos y puntos.
    No exige 3 niveles ni valida nada. Si empieza por letras, quedará "".
    Ej.: '2.3.1porque...' -> '2.3.1'
         '2.3.1CH/CH'     -> '2.3.1'
         'no lo sé'       -> ''
    """
    frag = []
    for ch in s.strip():
        if ch.isdigit() or ch == '.':
            frag.append(ch)
        else:
            break
    return "".join(frag)

def is_well_formed_ec(s) -> bool: # 1–4 partes: d, d.d, d.d.d, d.d.d.d
    if s is None:
        return False
    s = str(s).strip()  # convierte a str y recorta espacios (incluye \t, \n, etc.)
    return bool(EC_DOTS_RE.fullmatch(s))

def evaluate_model(
        accelerator,
        model,
        tokenizer,
        eval_data,
        args,
        split: str = "val",
        log_prefix: str | None = None,
        save_predictions: bool = False,
        mode: str = "eval",
        epoch: int | None = None,
        ):
    """
    Run generation, parse EC predictions, optionally compute classification metrics, and log to W&B.
    
    Parameters
    ----------
    eval_data : datasets.Dataset
        HF dataset split with fields ['input_text', 'output_text'].
    split : str
        Logical split name ('val' or 'test'); used for filenames if saving.
    log_prefix : Optional[str]
        If set, metrics are logged as '{log_prefix}/...'. Defaults to split.
    save_predictions : bool
        If True, writes a TSV with predictions for this run.

    Returns
    -------
    (predictions, true_labels, smiles_list, metrics_dict)
    """
    log_prefix = log_prefix or split

    dataset = Smiles2ECDataset(eval_data)

    batch_size = int(getattr(args, "eval_batch_size", 32))   
    dataloader = DataLoader(
        dataset, 
        batch_size=batch_size, 
        shuffle=False
    )
    if mode != "predict":
        dataloader = accelerator.prepare(dataloader) # => DistributedSampler

    # Generation model
    gen_model = accelerator.unwrap_model(model)
    device = accelerator.device
    if not getattr(gen_model, "is_quantized", False) and not getattr(gen_model.config, "quantization_config", None):
        gen_model.to(device)
    gen_model.eval()

    # Free fragmented CUDA memory before generation to avoid OOM spikes
    torch.cuda.empty_cache()

    max_len = int(getattr(args, "max_seq_length", 1280))

    local_predictions = []
    local_true_labels = []
    local_smiles = []
    local_fragments = []
    local_well_formed = []

    with torch.no_grad():
        for batch_inputs, batch_labels, batch_smiles in dataloader:

            # Encode the batch; truncate to training length to prevent OOM from
            # unbounded padding when sequences vary in length across the batch
            inputs = tokenizer(
                batch_inputs,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=max_len,
            )

            # Move inputs to the same device as the model
            inputs = {k: v.to(device) for k, v in inputs.items()}

            # Generate outputs
            outputs = gen_model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs.get("attention_mask"),
                max_new_tokens=8,
                do_sample=False,
                temperature=0.0,
                synced_gpus=(mode != "predict") # ✅ evita desincronizaciones/bloqueos en multi-GPU
            )

            # Decode outputs
            decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)

            for j, out in enumerate(decoded):
                try:
                    raw = parse_ec_raw(out) # el oficial que usamos para hacer los compute_classification_metrics
                    frag = leading_ec_fragment(raw) # para diagnóstico
                    local_predictions.append(raw)
                    local_fragments.append(frag)
                    local_well_formed.append(is_well_formed_ec(raw))
                    local_true_labels.append(str(batch_labels[j]))
                    local_smiles.append(batch_smiles[j])
                except Exception as e:
                    if accelerator.is_main_process:
                        print(f"[eval] Error processing prediction {j}: {e}")
                    continue

    # --- Gather de todos los ranks --- Agrupamos todo en un objeto compacto por rank
    local_obj = (
        local_predictions,
        local_true_labels,
        local_smiles,
        local_fragments,
        local_well_formed,
    )
    if mode != "predict" and dist.is_available() and dist.is_initialized():
        world_size = dist.get_world_size()
        all_objs = [None] * world_size
        dist.all_gather_object(all_objs, local_obj)
    else:
        all_objs = [local_obj]

    # Valores por defecto (para ranks != 0)
    predictions = []
    true_labels = []
    smiles_list = []
    metrics = {}

    # Solo rank 0 aplana y calcula métricas
    if accelerator.is_main_process:
        all_preds  = list(chain.from_iterable(o[0] for o in all_objs)) # todas las predicciones del set, no sólo de un shard.
        all_labels = list(chain.from_iterable(o[1] for o in all_objs))
        all_smiles = list(chain.from_iterable(o[2] for o in all_objs))
        all_frags  = list(chain.from_iterable(o[3] for o in all_objs))
        all_wf     = list(chain.from_iterable(o[4] for o in all_objs))

        predictions = all_preds
        true_labels = all_labels
        smiles_list = all_smiles

        # 1) ¿Hay labels?
        has_non_empty_label = any(
            str(y).strip().lower() not in ("", "nan", "none")
            for y in all_labels
        )

        # 2) Métricas
        if has_non_empty_label:
            metrics = compute_classification_metrics(all_labels, all_preds)

            n_total = len(all_preds)
            n_wf = sum(all_wf)
            wf_rate = n_wf / max(1, n_total)

            if wandb.run is not None:
                log_dict = {
                    f"{log_prefix}/accuracy":     metrics["accuracy"],
                    f"{log_prefix}/f1_macro":     metrics["f1_macro"],
                    f"{log_prefix}/f1_weighted":  metrics["f1_weighted"],
                    f"{log_prefix}/mcc":          metrics["mcc"],
                    f"{log_prefix}/well_formed_rate": wf_rate,
                    f"{log_prefix}/n_samples":    n_total,
                }
                if epoch is not None:
                    log_dict["epoch"] = epoch
                wandb.log(log_dict)

                # Keep best values in the run summary for easy comparison across runs
                for key in ("accuracy", "f1_macro", "f1_weighted", "mcc"):
                    summary_key = f"{log_prefix}/best_{key}"
                    prev = wandb.run.summary.get(summary_key)
                    if prev is None or metrics[key] > prev:
                        wandb.run.summary[summary_key] = metrics[key]

            epoch_tag = f" [epoch {epoch}]" if epoch is not None else ""
            print(f"\n{'='*52}")
            print(f"  {split.upper()} RESULTS{epoch_tag}")
            print(f"{'='*52}")
            print(f"  Accuracy   : {metrics['accuracy']:.4f}")
            print(f"  F1 macro   : {metrics['f1_macro']:.4f}")
            print(f"  F1 weighted: {metrics['f1_weighted']:.4f}")
            print(f"  MCC        : {metrics['mcc']:.4f}")
            print(f"  Well-formed: {n_wf}/{n_total} ({wf_rate:.1%})")
            print(f"{'='*52}\n")
        else:
            print(f"[eval] No ground-truth labels found for split='{split}' "
                  f"(all '', 'nan' or 'none'). Skipping metric computation.")

        # 3) Guardar TSV si procede
        if save_predictions:
            run_id = wandb.run.id if wandb.run else time.strftime("%Y%m%d-%H%M%S")
            alias = getattr(args, "template_alias", "EC_NUMBER")
            key = getattr(args, "template_key", "EC_NUMBER_PROMPT")
            out_name = f"predictions_{split}.{alias}.{key}.{run_id}.tsv"
            out_path = os.path.join(args.output_folder, out_name)

            df = pd.DataFrame({
                "true_label":      all_labels,
                "pred_raw":        all_preds,
                "pred_fragment":   all_frags,
                "pred_well_formed":all_wf,
                "smiles":          all_smiles,
            })
            df.to_csv(out_path, sep="\t", index=False)

            if wandb.run is not None:
                artifact = wandb.Artifact(f"{split}_predictions_{alias}_{key}_{run_id}", type="predictions")
                artifact.add_file(out_path)
                wandb.log_artifact(artifact)

    # Esta función se llama en todos los ranks, pero las listas/métricas solo
    # son útiles en rank 0. El resto recibe listas vacías y metrics = {}.
    return predictions, true_labels, smiles_list, metrics