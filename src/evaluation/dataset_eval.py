# gemma4ec/src/evaluation/dataset_eval.py

from torch.utils.data import Dataset

SMILES_START = "Reaction SMILES: "
SMILES_END_MARKER = "\nAnswer:"  # for EC prompts

def extract_smiles(input_text: str) -> str:
    """
    Extrae SIEMPRE el SMILES del ÚLTIMO bloque 'Reaction SMILES:'
    ignorando los de los ejemplos en el prompt.
    """
    # buscar la ÚLTIMA aparición
    start = input_text.rfind(SMILES_START)
    #start = input_text.find(SMILES_START)
    if start == -1:
        return ""
    start += len(SMILES_START)
    end = input_text.find(SMILES_END_MARKER, start)
    if end == -1:
        end = len(input_text)
    return input_text[start:end].strip()

class Smiles2ECDataset(Dataset):
    """
    Minimal PyTorch Dataset for reaction-SMILES → EC label tasks.

    - Expects each item to be a dict with keys: "input_text" and "output_text".
    - The reaction SMILES string is extracted from `input_text` using the markers
    defined below (defaults match the EC-number prompts you use):
        * start marker:  "Reaction SMILES: "
        * end marker:    "
    Answer:"

    - Returns a tuple: (input_text, label_str, smiles_str)
    """
    def __init__(self, data):
        self.data = data

    def __len__(self):
        return len(self.data)
        
    def __getitem__(self, idx):
        item = self.data[idx]
        input_text = str(item["input_text"])
        output_text = str(item["output_text"])
        smiles = extract_smiles(input_text)
        return input_text, output_text, smiles
    
