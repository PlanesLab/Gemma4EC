---
base_model: google/txgemma-9b-predict
library_name: peft
---

# Gemma4EC-9B — Rhea_Time adapter

LoRA adapter for Gemma4EC-9B fine-tuned on the **Rhea_Time** benchmark partition. This partition uses a chronological split by reaction entry date, placing the most recently added reactions in the test set to assess temporal generalisation.

## Usage

```bash
git clone https://huggingface.co/PlanesLab/Gemma4EC-9B-Rhea_Time models/Gemma4EC-9B-Rhea_Time
python predict.py --raw_data_file reactions.csv --model_checkpoint_folder models/Gemma4EC-9B-Rhea_Time
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
| Training data | Rhea_Time train split |
| Task | EC number prediction (CAUSAL_LM) |

## Performance

Support-weighted MCC on the Rhea_Time test set: **0.752**

See the [Gemma4EC repository](https://github.com/PlanesLab/Gemma4EC) for full benchmark results.
