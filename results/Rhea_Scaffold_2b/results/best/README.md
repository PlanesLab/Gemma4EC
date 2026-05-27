---
base_model: google/txgemma-2b-predict
library_name: peft
---

# Gemma4EC-2B — Rhea_Scaffold adapter

LoRA adapter for Gemma4EC-2B fine-tuned on the **Rhea_Scaffold** benchmark partition (Murcko scaffold split (chemical novelty)).

## Usage

```bash
git clone https://huggingface.co/PlanesLab/Gemma4EC-2B-Rhea_Scaffold models/Gemma4EC-2B-Rhea_Scaffold
python predict.py \
  --raw_data_file reactions.csv \
  --model_checkpoint_folder models/Gemma4EC-2B-Rhea_Scaffold \
  --model_id google/txgemma-2b-predict
```

## Model details

| Property | Value |
|---|---|
| Base model | `google/txgemma-2b-predict` |
| Adapter method | LoRA |
| LoRA rank (r) | 16 |
| LoRA alpha | 16 |
| LoRA dropout | 0.1 |
| Target modules | q, k, v, o, gate, up, down proj |
| Training data | Rhea_Scaffold train split |
| Task | EC number prediction (CAUSAL_LM) |

See the [Gemma4EC repository](https://github.com/PlanesLab/Gemma4EC) for full benchmark results.
