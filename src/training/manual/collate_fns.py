
# src/training/manual/collate_fns.py

import random
from typing import Any, Dict, Iterable, Callable, List
import torch
from torch.utils.data.distributed import DistributedSampler

from .text_fewshot_utils import _split_instructions_and_smiles_block, _fmt_shot, _fmt_query_tail

# ============================================
#  Collate (NO-shot -default-)
# ============================================

def _make_collate_fn(tokenizer, formatting_func: Callable[[Dict[str, Any]], str],
                     max_seq_length: int):
    """
    Build a collate function for Causal LM fine-tuning that mirrors SFTTrainer behavior.

    This collate:
      1) Applies `formatting_func` to each example to produce the final training string
         (e.g., "<prompt> <label><eos>").
      2) Tokenizes the batch in one call with dynamic padding to the longest item in
         the batch (`padding="longest"`), plus truncation to `max_seq_length`.
      3) Creates LM labels by cloning `input_ids` and masking padding positions with -100
         so the loss ignores them (HF CE loss convention).
      4) Returns a dict of PyTorch tensors: {"input_ids", "attention_mask", "labels"}.

    Why this design:
      - **Parity with SFTTrainer**: SFTTrainer internally does (format → tokenize → mask pad → labels=input_ids).
        Using the same steps keeps manual loops comparable to Trainer runs.
      - **Dynamic padding**: Minimizes wasted computation vs. padding to a global max length.
      - **Safe truncation**: Ensures batches won't exceed your chosen `max_seq_length`.
      - **Causal LM labeling**: Passing `labels=input_ids` lets HF models handle the internal
        1-token shift; masking pads avoids spurious loss on padding tokens.

    Notes:
      - Ensure the tokenizer has a valid `pad_token_id`. If your model/tokenizer pair does
        not define a pad token, set one beforehand, e.g.:
            tokenizer.pad_token = tokenizer.eos_token
            model.config.pad_token_id = tokenizer.pad_token_id
      - Pair this with a DataLoader using `shuffle=True` and (optionally) a “bucket by length”
        sampler upstream if you want even tighter padding efficiency than per-batch longest.
      - `max_seq_length` should be chosen with your pre-train sequence-length sanity check
        to avoid excessive truncation.

    Args:
        tokenizer: A Hugging Face tokenizer (AutoTokenizer) configured for your model.
        formatting_func: Callable(example_dict) -> str. Produces the training string per sample.
        max_seq_length: int. Maximum total sequence length after tokenization.

    Returns:
        A function `collate(batch: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]`
        suitable for `DataLoader(..., collate_fn=returned_fn)`.

    ADVERTENCIA: Con tu SFTTrainer anterior estabas entrenando prompt+respuesta 
    (labels = input_ids salvo padding). Si quieres seguir comportándose igual en el bucle manual, 
    deja tu collate tal cual (labels = input_ids y enmascarar sólo pad).
    """
    pad_id = tokenizer.pad_token_id
    def collate(batch: Iterable[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        # 1) Format structured examples into plain training strings
        texts = [formatting_func(ex) for ex in batch]
        # 2) Tokenize the whole batch with dynamic padding and truncation
        enc = tokenizer(
            texts, return_tensors="pt", padding="longest",
            truncation=True, max_length=max_seq_length,
        )
        # 3) Build Causal LM labels and mask padding with -100 (ignored by loss)
        # For standard causal LM training, the loss is computed between the model’s next-token prediction 
        # and the same tokens shifted by one position. In Hugging Face models this shift is handled inside the loss 
        # function when you pass labels=input_ids.
        # Masking with -100 tells the loss function to ignore padding tokens (standard PyTorch CE loss convention used by HF).
        labels = enc["input_ids"].clone()
        
        # ignora padding en la loss
        if "attention_mask" in enc:
            labels[enc["attention_mask"] == 0] = -100
        elif pad_id is not None:
            labels[enc["input_ids"] == pad_id] = -100
        enc["labels"] = labels

        # opcional: ids de fila para firmas por época
        if "__row_id__" in batch[0]:
            enc["row_ids"] = torch.tensor([ex["__row_id__"] for ex in batch], dtype=torch.long)
        return enc
    return collate

# ============================================
#  Collate (few-shot on-the-fly)
# ============================================
def _make_collate_fn_fewshot(
    tokenizer,
    formatting_func: Callable[[Dict[str, Any]], str],
    max_seq_length: int,
    *,
    few_shot_ratio: float,
    k_min: int,
    k_max: int,
    pool_inputs: List[str],
    pool_outputs: List[str],
    seed: int,
):
    """
    Build a collate function that performs *few-shot prompting on-the-fly* during
    DataLoader batching.

    When enabled, each example in the batch can be *rewritten* into a few-shot
    composite prompt with probability `few_shot_ratio`. The transformation occurs
    inside the collate function, so the base dataset remains unchanged.

    --- Prompt layout (when few-shot triggers) ---

        <INSTRUCTIONS>
        Reaction SMILES: <shot_1>
        Answer: <y_1>
        Reaction SMILES: <shot_2>
        Answer: <y_2>
        ...
        Reaction SMILES: <query_from_current_sample>
        Answer:

    --- Behavior ---
      - For each batch element, with probability `few_shot_ratio`, we:
          * Extract the instruction header from the current input.
          * Sample k indices (k ~ Uniform[k_min..k_max]) from the training pool
            `pool_inputs` / `pool_outputs`, excluding its own index when possible.
          * Render those examples as few-shot blocks ("Reaction SMILES + Answer").
          * Concatenate them under the same header, followed by the current example's
            SMILES line and an empty “Answer:” placeholder.
          * Leave the corresponding `output_text` unchanged — it will be appended by
            `formatting_func` (e.g. "<label><eos>") after this rewrite.
      - Otherwise (with probability 1 - few_shot_ratio), the example is used as-is
        (zero-shot).
      - This logic is applied independently for every sample at collate time, which
        allows fresh few-shot combinations each epoch simply by reseeding.

    --- Notes ---
      - No dataset modification is needed; everything happens dynamically per batch.
      - Resampling per epoch is achieved by calling this function again with a new seed.
      - Validation/Test loaders should always use the plain zero-shot collate.
      - If in the future you want to exclude few-shot examples from the loss,
        you can extend this collate to mask tokens up to the last “Answer:” marker.

    Args:
      tokenizer: HF tokenizer used for tokenization and padding.
      formatting_func: Callable(example) → str that formats the final "<prompt> <label><eos>" text.
      max_seq_length: Max total sequence length after tokenization.
      few_shot_ratio: Probability that an example becomes few-shot.
      k_min, k_max: Inclusive range for number of few-shot examples (shots).
      pool_inputs, pool_outputs: Lists of all training samples (used as source pool for shots).
      seed: Random seed controlling reproducibility and per-epoch resampling.

    Returns:
      A collate function ready to pass into a PyTorch DataLoader.
      The returned batches contain tokenized tensors:
        {
          "input_ids": LongTensor,
          "attention_mask": LongTensor,
          "labels": LongTensor (pads masked with -100),
          "row_ids": Optional[LongTensor]
        }
    """
    rng = random.Random(seed)
    n = len(pool_inputs)
    pad_id = tokenizer.pad_token_id

    def _upgrade_input(x: str, y: str, idx_guess: int) -> str:
        if n <= 1 or rng.random() >= float(few_shot_ratio):
            return x  # zero-shot
        k = rng.randint(int(k_min), int(k_max))
        # muestreamos con reemplazo evitando (si se conoce) el propio índice
        pool = [*range(0, idx_guess), *range(idx_guess + 1, n)] if 0 <= idx_guess < n else list(range(n))
        shots_idx = [rng.choice(pool) for _ in range(k)]
        instructions, _ = _split_instructions_and_smiles_block(x)
        header = f"{instructions}\n" if instructions else ""
        shot_blocks = [_fmt_shot(pool_inputs[j], pool_outputs[j]) for j in shots_idx]
        query_tail  = _fmt_query_tail(x)
        return (header + "\n".join(shot_blocks + [query_tail])).strip() if header else "\n".join(shot_blocks + [query_tail]).strip()

    def collate(batch: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        # reconstruimos posibles inputs few-shot y luego aplicamos formatting_func
        upgraded_examples: List[Dict[str, Any]] = []
        for ex in batch:
            x, y = ex["input_text"], ex["output_text"]
            idx_guess = int(ex.get("__row_id__", -1))
            x_up = _upgrade_input(x, y, idx_guess)
            upgraded_examples.append({"input_text": x_up, "output_text": y, **({k:v for k,v in ex.items() if k not in ("input_text","output_text")})})

        texts = [formatting_func(ex) for ex in upgraded_examples]
        enc = tokenizer(
            texts, return_tensors="pt", padding="longest",
            truncation=True, max_length=max_seq_length,
        )
        labels = enc["input_ids"].clone()
        if "attention_mask" in enc:
            labels[enc["attention_mask"] == 0] = -100
        elif pad_id is not None:
            labels[enc["input_ids"] == pad_id] = -100
        enc["labels"] = labels
        if "__row_id__" in batch[0]:
            enc["row_ids"] = torch.tensor([ex.get("__row_id__", -1) for ex in batch], dtype=torch.long)
        return enc
    return collate