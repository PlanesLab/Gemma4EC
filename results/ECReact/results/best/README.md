---
base_model: google/txgemma-9b-predict
library_name: peft
---

# Gemma4EC-9B — ECReact adapter

This is the **LoRA adapter** for [Gemma4EC-9B](https://huggingface.co/PlanesLab/Gemma4EC-9B-Predict), fine-tuned on the [ECReact-1.0](https://github.com/rxn4chemistry/biocatalysis-model/blob/main/data/ecreact-1.0.csv) dataset for Enzyme Commission (EC) number prediction from biochemical reaction SMILES.

## Usage

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

base = AutoModelForCausalLM.from_pretrained("google/txgemma-9b-predict")
model = PeftModel.from_pretrained(base, "PlanesLab/Gemma4EC-9B-Predict")
```

Or clone this adapter and use it with the Gemma4EC inference scripts:

```bash
git clone https://huggingface.co/PlanesLab/Gemma4EC-9B-Predict models/Gemma4EC-9B-Predict
python predict.py --raw_data_file reactions.csv --model_checkpoint_folder models/Gemma4EC-9B-Predict
```

## Model details

| Property | Value |
|---|---|
| Base model | `google/txgemma-9b-predict` |
| Adapter method | LoRA |
| LoRA rank (r) | 16 |
| LoRA alpha | 16 |
| LoRA dropout | 0.1 |
| Target modules | q, k, v, o, gate, up, down proj |
| Training data | ECReact-1.0 (train split, ~49 k reactions) |
| Task | EC number prediction (CAUSAL_LM) |

## Performance

Overall support-weighted MCC on the ECReact test set: **0.903**

See the [Gemma4EC repository](https://github.com/PlanesLab/Gemma4EC) for full benchmark results.
