# gemma4ec/src/jsonl_builder.py

import os
import json
import pandas as pd
from typing import Dict, Optional

def create_jsonl_from_df(
    file_path: str,
    output_path: str,
    input_template: Dict[str, str],
    cell_description_df: Optional[pd.DataFrame] = None
) -> None:
    """
    Build a .jsonl dataset from a CSV/TXT with columns: rxn_smiles, ec.
    Renders the selected prompt (expects {reaction_smiles}) into input_text.

    Parameters
    ----------
    file_path (str): Path to the input csv file.
    output_path (str): Path to the output JSONL file.
    input_template (Dict[str, str]): A dictionary with a single key and a prompt string containing placeholders
        (e.g., {"EC_NUMBER": "Instructions: ... {reaction_smiles} ..."}).
    cell_description_df (pd.DataFrame, optional):
        If provided, should contain 'Cell line Name' and 'Cell description' columns
        to enrich cell line descriptions in the template.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    df = pd.read_csv(file_path)  # autodetects delimiter (',' default)
    if "rxn_smiles" not in df.columns or "ec" not in df.columns:
        raise ValueError("Input file must contain columns: 'rxn_smiles' and 'ec'.")
    if len(input_template) != 1:
        raise ValueError("input_template must contain exactly one key.")
    template_str = next(iter(input_template.values()))
    # Optional future: support {cell_line}. For now we ignore cell_description_df.
    with open(output_path, "w") as jsonl_file:
        for _, row in df.iterrows():
            input_text = template_str.format(reaction_smiles=row["rxn_smiles"])
            data_point = {
                "input_text": input_text,
                "output_text": str(row["ec"])
            }
            jsonl_file.write(json.dumps(data_point, ensure_ascii=False) + "\n")
    print(f"Data has been successfully written to {output_path}")


