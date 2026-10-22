# gemma4ec/src/predict_utils/common.py

import os
import random
from typing import Optional
import pandas as pd
from pathlib import Path
import itertools
import threading
import hashlib

from openai import OpenAI
from google import genai

_GEMINI_KEYS = []
_GEMINI_CLIENTS = []
_GEMINI_ALIVE = []
_GEMINI_LOCK = threading.Lock()

from ..datamod.templates import build_input_template_from_file
from ..datamod.jsonl_builder import create_jsonl_from_df
from ..utils.paths import get_jsonl_path
import re

DEBUG_API = os.environ.get("DEBUG_API", "0") == "1"
_SMILES_RE = re.compile(
    r"Reaction\s+SMILES\s*:\s*(.+)",  # captura todo lo que hay tras los dos puntos
    re.IGNORECASE
)

def key_fingerprint(key: str, n: int = 6) -> str:
    """
    Returns a short, non-reversible fingerprint of an API key.
    Safe to log.
    """
    if not key:
        return "none"
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return h[:n]

def get_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY env var is not set")
    if DEBUG_API:
        print(
            f"[openai] Using API key fingerprint=openai_{key_fingerprint(api_key)}",
            flush=True
        )
    return OpenAI(api_key=api_key)

def _init_gemini_clients():
    global _GEMINI_KEYS, _GEMINI_CLIENTS, _GEMINI_ALIVE

    keys_env = os.environ.get("GEMINI_API_KEYS")
    if not keys_env:
        # fallback legacy
        single = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not single:
            raise RuntimeError("No GEMINI_API_KEYS / GEMINI_API_KEY found")
        _GEMINI_KEYS = [single]
    else:
        _GEMINI_KEYS = [k.strip() for k in keys_env.split(",") if k.strip()]

    if not _GEMINI_KEYS:
        raise RuntimeError("Empty GEMINI_API_KEYS")

    _GEMINI_CLIENTS = [
        (genai.Client(api_key=k), key_fingerprint(k))
        for k in _GEMINI_KEYS
    ]

    _GEMINI_ALIVE = list(_GEMINI_CLIENTS)

    print(
        f"[gemini] Initialized {len(_GEMINI_ALIVE)} Gemini API clients "
        f"({', '.join('gemini_'+fp for _, fp in _GEMINI_ALIVE)})",
        flush=True
    )
  
def get_gemini_client():
    global _GEMINI_ALIVE
    with _GEMINI_LOCK:
        if not _GEMINI_ALIVE:
            _init_gemini_clients()    
        if not _GEMINI_ALIVE:
            raise RuntimeError("All Gemini API keys exhausted")

        client, fingerprint = random.choice(_GEMINI_ALIVE)

    return client, fingerprint

def call_api_model(
    model_name: str,
    prompt: str,
    temperature: float = 0.0,
    max_output_tokens: Optional[int] = None,
) -> str:
    """
    Generic dispatcher: decides whether to call OpenAI or Gemini based on model_name.
    If max_output_tokens is None, we let the backend use its default limit.
    """
    if DEBUG_API:
        print(f"[debug_api] call_api_model -> model_name={model_name}, "
              f"max_output_tokens={max_output_tokens}", flush=True)

    if model_name.startswith("gemini-"):
        return call_gemini_model(
            model_name=model_name,
            prompt=prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
    else:
        return call_openai_model(
            model_name=model_name,
            prompt=prompt,
            max_output_tokens=max_output_tokens,
        )


# ---------------------------------------------------------------------------
# OpenAI free-allowance guard (data-sharing complimentary tokens)
# ---------------------------------------------------------------------------
# When OPENAI_FREE_ONLY=1, every OpenAI call reserves tokens in a per-day ledger
# shared by all jobs (file lock) and refuses to run once the day's complimentary
# allowance for the model's group would be exceeded. Allowances reset 00:00 UTC.
OPENAI_RESERVE = 2000  # tokens reserved per call before the real usage is known


def _openai_group(model_name: str) -> str:
    return "mini" if ("mini" in model_name or "nano" in model_name) else "large"


def _openai_ledger(delta: int, model_name: str) -> None:
    if os.environ.get("OPENAI_FREE_ONLY", "0") != "1":
        return
    import fcntl
    import json as _json
    from datetime import datetime, timezone

    group = _openai_group(model_name)
    cap = int(os.environ.get(f"OPENAI_DAILY_CAP_{group.upper()}",
                             950_000 if group == "large" else 9_500_000))
    ledger_dir = Path(os.environ.get("OPENAI_USAGE_LEDGER", Path.home() / ".gemma4ec_openai_usage"))
    ledger_dir.mkdir(parents=True, exist_ok=True)
    path = ledger_dir / f"{datetime.now(timezone.utc):%Y-%m-%d}_{group}.json"
    with open(path, "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        used = int((_json.loads(f.read() or "{}")).get("tokens", 0))
        if delta > 0 and used + delta > cap:
            raise RuntimeError(f"OPENAI_DAILY_CAP_REACHED ({group}: {used}/{cap} tokens today)")
        f.seek(0)
        f.truncate()
        f.write(_json.dumps({"tokens": max(0, used + delta), "cap": cap}))
        fcntl.flock(f, fcntl.LOCK_UN)

def call_openai_model(
    model_name: str,
    prompt: str,
    max_output_tokens: Optional[int] = None,
) -> str:
    """
    Calls OpenAI models using:
    - responses.create for GPT-5+
    - chat.completions.create for legacy chat models

    Always returns a plain text string.
    """
    client = get_openai_client()
    final_text = ""
    used_tokens = None
    _openai_ledger(OPENAI_RESERVE, model_name)

    # =========================
    # GPT-5+ → responses API
    # =========================
    if model_name.startswith(("gpt-5", "gpt-6")):
        if DEBUG_API:
            print(f"[debug_openai] Using responses API for model={model_name}", flush=True)
            print("[debug_openai] Prompt head:\n"
                  + prompt[:400] + "\n----- END PROMPT HEAD -----", flush=True)

        kwargs = {
            "model": model_name,
            "input": prompt
        }
        if max_output_tokens is not None:
            kwargs["max_output_tokens"] = max_output_tokens

        try:
            response = client.responses.create(**kwargs)
        except Exception:
            _openai_ledger(-OPENAI_RESERVE, model_name)
            raise
        used_tokens = getattr(getattr(response, "usage", None), "total_tokens", None)

        # 🔹 Extraer texto de forma robusta
        text_parts = []
        
        for item in response.output:
            if getattr(item, "type", None) == "message":
                for part in getattr(item, "content", []):
                    if getattr(part, "type", None) == "output_text":
                        text_parts.append(part.text)

        final_text = " ".join(text_parts).strip()

    # =================================
    # Modelos antiguos → chat API
    # =================================
    else:
        if DEBUG_API:
            print(f"[debug_openai] Using chat.completions for model={model_name}", flush=True)
            print("[debug_openai] Prompt head:\n"
                  + prompt[:400] + "\n----- END PROMPT HEAD -----", flush=True)

        kwargs = dict(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
        )

        if max_output_tokens is not None:
            if model_name.startswith(("o", "gpt-4.1")):
                kwargs["max_completion_tokens"] = max_output_tokens
            else:
                kwargs["max_tokens"] = max_output_tokens

        try:
            completion = client.chat.completions.create(**kwargs)
        except Exception:
            _openai_ledger(-OPENAI_RESERVE, model_name)
            raise
        used_tokens = getattr(getattr(completion, "usage", None), "total_tokens", None)
        final_text = completion.choices[0].message.content or ""

    # =========================
    # DEBUG COMÚN (AQUÍ VA TU PREVIEW)
    # =========================
    if DEBUG_API:
        content_preview = final_text or ""
        print(f"[debug_openai] message.content repr={repr(content_preview)}", flush=True)
        print(
            f"[debug_openai] message.content[:200]={content_preview[:200]!r}",
            flush=True
        )

    # replace the reservation with the real usage (keep it if usage is missing)
    if used_tokens is not None:
        _openai_ledger(int(used_tokens) - OPENAI_RESERVE, model_name)
    return final_text.strip()

def call_gemini_model(
    model_name: str,
    prompt: str,
    temperature: float = 0.0,
    max_output_tokens: Optional[int] = None,
) -> str:
    """
    Calls a Gemini model and returns the text.
    Uses the official `google-genai` library.
    """
    client, fingerprint = get_gemini_client()
    print(
        f"[gemini] Using API key fingerprint=gemini_{fingerprint} "
        f"model={model_name}",
        flush=True
    )
    if DEBUG_API:
        print(
            "[debug_gemini] Prompt head:\n"
            + prompt[:400]
            + "\n----- END PROMPT HEAD -----",
            flush=True,
        )

    config = {
        "temperature": temperature,
    }
    if max_output_tokens is not None:
        config["max_output_tokens"] = max_output_tokens

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config,
        )

    except Exception as e:
        msg = str(e).lower()

        is_quota = "quota" in msg or "exceeded" in msg or "resource_exhausted" in msg
        # Free tier: per-minute limits are transient → back off and retry the same key
        if is_quota and not re.search(r"per_?day|perday|daily", msg):
            raise RuntimeError("GEMINI_RATE_LIMITED (per-minute quota)")

        # Daily quota exhausted → remove key from pool until the job is re-run
        if is_quota:
            with _GEMINI_LOCK:
                print(
                    f"[gemini] 🔥 Quota exhausted for key gemini_{fingerprint}, "
                    f"removing from pool",
                    flush=True
                )
                global _GEMINI_ALIVE
                _GEMINI_ALIVE = [
                    (c, fp) for (c, fp) in _GEMINI_ALIVE
                    if fp != fingerprint
                ]
                print(
                    f"[gemini] Remaining keys: "
                    f"{[fp for _, fp in _GEMINI_ALIVE]}",
                    flush=True
                )
            raise RuntimeError("GEMINI_KEY_EXHAUSTED")
        raise
    
    # -------------------------
    # Parse response text
    # -------------------------
    if DEBUG_API:
        print(f"[debug_gemini] Raw response type={type(response)}", flush=True)
        print(f"[debug_gemini] dir(response)[:15]={dir(response)[:15]}", flush=True)
        txt = getattr(response, "text", None)
        print(f"[debug_gemini] response.text repr={repr(txt)[:200]}", flush=True)

    text = getattr(response, "text", None)
    if text is None:
        text = "".join(
            part.text
            for cand in getattr(response, "candidates", [])
            for part in getattr(getattr(cand, "content", None), "parts", [])
            if hasattr(part, "text")
        )
    return (text or "").strip()

def build_jsonl_from_raw(
    raw_data_file: str,
    processed_data_folder: str,
    prompts_json_path: str,
    template_key: str,
    template_alias: str,
) -> Path:
    """
    Mimics the logic from predict.py:
    - Loads the template from prompts.json
    - Builds the JSONL path
    - Generates the JSONL with input_text/output_text
    Returns the path to the generated JSONL.
    """
    input_template = build_input_template_from_file(
        template_path=prompts_json_path,
        key=template_key,           # p.ej. EC_NUMBER_PROMPT_2
        required_vars={"reaction_smiles"},
        dict_key=template_alias     # p.ej. EC_NUMBER
    )

    processed_dir = Path(processed_data_folder)
    processed_dir.mkdir(parents=True, exist_ok=True)

    jsonl_file_path = get_jsonl_path(
        str(processed_dir),
        "predict",
        template_alias,
        template_key,
    )

    print(f"[openai_predict] Building JSONL from: {raw_data_file} -> {jsonl_file_path}")
    create_jsonl_from_df(raw_data_file, jsonl_file_path, input_template)
    return jsonl_file_path

def extract_smiles_from_input(input_text: str) -> str:
    """
    Extracts the Reaction SMILES from the *last* 'Reaction SMILES: ...'
    line in the prompt (useful when there are few-shot examples + final query).
    """
    matches = _SMILES_RE.findall(input_text)
    if not matches:
        return ""
    # Nos quedamos con el ÚLTIMO (la query final)
    tail = matches[-1]
    # Solo la primera línea por si hay saltos
    line = tail.strip().splitlines()[0]
    # Por si hubiera 'Answer:' en la misma línea
    line = line.split("Answer:", 1)[0].strip()
    return line

def write_predictions_tsv(
    out_path: Path,
    true_labels,
    pred_raw,
    pred_fragments,
    pred_well_formed,
    smiles,
    n_attempts,
    status
):
    df_out = pd.DataFrame({
    "true_label":       true_labels,
    "pred_raw":         pred_raw,
    "pred_fragment":    pred_fragments,
    "pred_well_formed": pred_well_formed,
    "smiles":           smiles,
    "n_attempts":       n_attempts,
    "status":           status
    })
    df_out.to_csv(out_path, sep="\t", index=False)
    print(f"[predict_common] Saved TSV with {len(df_out)} rows to: {out_path}")