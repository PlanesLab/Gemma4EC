# gemma4ec/src/utils/seqcheck.py

import math
from typing import List, Sequence, Dict, Any
import numpy as np

def run_seq_len_check_with_mode(
    *,
    train_ds,
    val_ds,
    tokenizer,
    args,
    is_main_process: bool = True,
) -> Dict[str, Any]:
    """
    Run a fast pre-train sequence-length sanity check and, if training in few-shot mode,
    print an adjusted suggestion for `--max_seq_length` that accounts for on-the-fly
    few-shot prompt expansion.

    What this function does under each training mode:
      • SFT (zero-shot) or Manual (zero-shot):
          - Calls `quick_seq_len_check` to measure raw token lengths of
            "<input_text> <output_text><eos>".
          - Prints truncation rate, padding estimate, and a suggested cap (p99 rounded
            to the nearest multiple).

      • Manual (few-shot on-the-fly collate):
          - First calls `quick_seq_len_check` on the same zero-shot strings (base).
          - Then estimates the **mean length multiplier** due to few-shot mixing:
                E[length multiplier] ≈ (1 - ratio)*1 + ratio*(1 + E[k])
            where `k ~ Uniform[k_min..k_max]` and `ratio = few_shot_ratio`.
          - Prints:
                - the mean multiplier (and the worst-case 1 + k_max),
                - the adjusted suggestion: base_suggested * mean_multiplier,
                - a reminder that you may need extra headroom for worst-case mini-batches.
          - Returns the base results plus a `few_shot` entry with multipliers and
            adjusted suggestions.

    Notes:
      • This is an analytical estimate. It keeps `quick_seq_len_check` fast and avoids
        materializing few-shot prompts. If you aim to *guarantee* zero truncation for
        all micro-batches, consider provisioning for the worst-case multiplier (1+k_max).
      • Validation/Test should remain zero-shot; this function **does not** inflate their
        suggestions.

    Returns:
      A dict identical to `quick_seq_len_check` plus (when few-shot is enabled):
        results["few_shot"] = {
            "multiplier_mean": float,
            "multiplier_worst": float,
            "suggested_train_adjusted_mean": int,
            "suggested_train_adjusted_worst": int,
        }
    """
    # 1) Run the standard (zero-shot) measurement
    base = quick_seq_len_check(
        train_ds=train_ds,
        val_ds=val_ds,
        tokenizer=tokenizer,
        max_seq_length=int(getattr(args, "max_seq_length", 512)),
        subset=(getattr(args, "seqcheck_subset", 20_000) or None),
        batch_size=int(getattr(args, "seqcheck_batch_size", 1024)),
        percentiles=(90, 95, 99),
        suggest_multiple_of=64,
        hard_cap=4096,
        fail_on_truncation=bool(getattr(args, "fail_on_truncation", True)),
        truncation_tolerance=float(getattr(args, "truncation_tolerance", 0.01)),
        is_main_process=is_main_process,
    )

    # 2) If not in few-shot mode, we are done
    if not bool(getattr(args, "few_shot_training", False)):
        return base

    # 3) Few-shot estimates
    k_min = int(getattr(args, "few_shot_k_min", 1))
    k_max = int(getattr(args, "few_shot_k_max", 10))
    ratio = float(getattr(args, "few_shot_ratio", 0.3))

    mult_mean  = _estimate_fewshot_multiplier_mean(k_min, k_max, ratio)
    mult_worst = 1.0 + float(k_max)

    train_info = base.get("train", {})
    base_suggested = int(train_info.get("suggested_max_seq_length", int(getattr(args, "max_seq_length", 512))))

    suggested_mean  = int(round(base_suggested * mult_mean))
    suggested_worst = int(round(base_suggested * mult_worst))

    if is_main_process:
        print(f"\n[seqcheck] Few-shot mode detected "
              f"(ratio={ratio:.2f}, k∈[{k_min},{k_max}]).")
        print(f"  • Expected mean prompt length multiplier ≈ {mult_mean:.2f}")
        print(f"  • Worst-case prompt length multiplier  ≈ {mult_worst:.2f}")
        print(f"  • Base train suggestion (zero-shot)    : {base_suggested}")
        print(f"  • Adjusted suggestion (mean)          : {suggested_mean}")
        print(f"  • Adjusted suggestion (worst-case)    : {suggested_worst}")
        print("  Tip: choose between mean and worst-case depending on your "
              "tolerance to occasional truncation in mixed few-shot batches.")

    base["few_shot"] = dict(
        multiplier_mean=float(mult_mean),
        multiplier_worst=float(mult_worst),
        suggested_train_adjusted_mean=int(suggested_mean),
        suggested_train_adjusted_worst=int(suggested_worst),
    )
    return base

def _build_batch_text(batch: Dict[str, List[str]], eos_token: str) -> List[str]:
    # Mirrors your formatting_func: "<input_text> <output_text><eos>"
    ins  = batch["input_text"]
    outs = batch["output_text"]
    return [f"{i} {o}{eos_token}" for i, o in zip(ins, outs)]

def _iter_token_lengths(dataset, tokenizer, *, batch_size: int, subset: int | None) -> np.ndarray:
    """Return raw (untruncated) token lengths for the first `subset` items (or all if None)."""
    n = len(dataset)
    if subset is not None and subset > 0:
        n = min(n, subset)

    eos_tok = tokenizer.eos_token or "<eos>"
    lens: List[int] = []
    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        batch = dataset[start:end]  # dict of lists
        texts = _build_batch_text(batch, eos_tok)
        enc = tokenizer(
            texts,
            add_special_tokens=True,
            truncation=False,
            padding=False,
            return_attention_mask=False,
        )
        ids = enc["input_ids"]
        lens.extend(len(x) for x in ids)
    return np.asarray(lens, dtype=np.int32)

def _expected_padding(arr: np.ndarray, L: int) -> float:
    clipped = np.minimum(arr, L)
    return float((L - clipped).mean())

def _round_up_multiple(x: int, m: int) -> int:
    return int(math.ceil(x / float(m)) * m)

def quick_seq_len_check(
    *,
    train_ds,
    val_ds,
    tokenizer,
    max_seq_length: int,
    subset: int | None = 20_000,      # default: fast but representative
    batch_size: int = 1024,
    percentiles: Sequence[int] = (90, 95, 99),
    suggest_multiple_of: int = 64,
    hard_cap: int | None = 4096,      # keep conservative by default
    fail_on_truncation: bool = True,
    truncation_tolerance: float = 0.01,  # 1%
    is_main_process: bool = True,
) -> Dict[str, Any]:
    """
    Measures raw token lengths (no truncation), reports stats, and warns/errors
    if truncation exceeds `truncation_tolerance`. Returns a dict with metrics.
    """
    results: Dict[str, Any] = {}

    for split_name, ds in (("train", train_ds), ("validation", val_ds)):
        arr = _iter_token_lengths(ds, tokenizer, batch_size=batch_size, subset=subset)
        total = int(arr.size)
        if total == 0:
            if is_main_process:
                print(f"[seqcheck:{split_name}] WARNING: dataset appears empty.")
            results[split_name] = {}
            continue

        mn, mx, mean = int(arr.min()), int(arr.max()), float(arr.mean())
        pvals = {p: int(np.percentile(arr, p)) for p in percentiles}
        trunc_rate = float((arr > max_seq_length).sum()) / total

        p99 = pvals.get(99, mx)
        suggested = _round_up_multiple(p99, suggest_multiple_of)
        if hard_cap is not None:
            suggested = min(suggested, hard_cap)

        pad_now = _expected_padding(arr, max_seq_length)
        pad_sug = _expected_padding(arr, suggested)

        results[split_name] = dict(
            total=total,
            min=mn,
            mean=mean,
            max=mx,
            percentiles=pvals,
            truncation_rate=trunc_rate,
            suggested_max_seq_length=suggested,
            expected_padding_now=pad_now,
            expected_padding_suggested=pad_sug,
        )

        if is_main_process:
            print(f"\n[seqcheck:{split_name}] n={total}")
            print(f"  min/mean/max: {mn} / {mean:.1f} / {mx}")
            for p in sorted(pvals):
                print(f"  p{p:>2}: {pvals[p]}")
            print(f"  max_seq_length={max_seq_length} -> truncation={trunc_rate*100:.2f}% | est. pad≈{pad_now:.1f}")
            print(f"  suggested≈p99 (x{suggest_multiple_of}) => {suggested} | est. pad≈{pad_sug:.1f}")

        if fail_on_truncation and trunc_rate > truncation_tolerance:
            raise SystemExit(
                f"[seqcheck:{split_name}] truncation rate {trunc_rate*100:.2f}% "
                f"> tolerance {truncation_tolerance*100:.2f}%. "
                f"Increase --max_seq_length (e.g., {suggested})."
            )

        if (not fail_on_truncation) and (trunc_rate > truncation_tolerance) and is_main_process:
            print(
                f"[seqcheck:{split_name}] WARNING: truncation {trunc_rate*100:.2f}% "
                f"> tolerance {truncation_tolerance*100:.2f}%. "
                f"Consider raising --max_seq_length (e.g., {suggested})."
            )
    return results

# ================================
# Few-shot aware wrapper (new)
# ================================
def _estimate_fewshot_multiplier_mean(k_min: int, k_max: int, ratio: float) -> float:
    """
    Expected mean length multiplier when mixing zero-shot and few-shot on-the-fly.

    We approximate:  E[length] ≈ (1 - r) * 1 + r * (1 + E[k]),
    where r is the few-shot ratio, and k ~ Uniform[k_min..k_max].
    """
    k_mean = (int(k_min) + int(k_max)) / 2.0
    ratio = float(ratio)
    return (1.0 - ratio) * 1.0 + ratio * (1.0 + k_mean)