# gemma4ec/src/templates.py

import os
import json
import re
from typing import Dict, Iterable, Optional

def build_input_template_from_file(
    template_path: str,
    key: str,
    required_vars: Iterable[str],
    dict_key: Optional[str] = None
) -> Dict[str, str]:
    """
    Load a single template from prompts.json and return {"ALIAS": "<template>"}.
    Validates placeholders (e.g., {reaction_smiles}).

    Parameters
    ----------
    template_path (str): Path to the JSON file that stores templates, e.g., 'templates/prompts.json'.
    key(str): The key of the template to load from the JSON (e.g., 'EC_NUMBER_PROMPT_2').
    required_vars (Iterable[str]): Placeholders that must exist in the template (e.g., {'reaction_smiles'}).
    dict_key (str | None): Optional alias for the output dictionary key (e.g., 'EC_NUMBER').
        If None, the original `key` is used.

    Returns
    -------
    Dict[str, str]: A dictionary with a single entry: {dict_key or key: template_string}

    Raises
    ------
    FileNotFoundError: If template_path does not exist.
    KeyError: If `key` is not found in the JSON.
    ValueError: If the template is empty or missing required placeholders.
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found: {template_path}")
    with open(template_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if key not in data:
        raise KeyError(f"Template key '{key}' not found in {template_path}")
    template_str = data[key]
    if not isinstance(template_str, str) or not template_str.strip():
        raise ValueError(f"Template for key '{key}' is empty or invalid.")
    found = set(re.findall(r"{(\w+)}", template_str))
    missing = set(required_vars) - found
    if missing:
        raise ValueError(f"Template '{key}' is missing placeholders: {sorted(missing)}")
    out_key = dict_key if dict_key is not None else key
    return {out_key: template_str}
