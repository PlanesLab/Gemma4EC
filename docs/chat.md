# Chat explanations

`bash chat/explain.sh reactions.csv out_dir` explains each Gemma4EC prediction in natural language. The result is
`out_dir/explanations.md` (a readable report) and `out_dir/explanations.json` (everything, including the votes and the
model's self-check).

## Setup (once)

1. **Configuration**: `cp config.sh.example config.sh` and set the paths below.
2. **Atom-mapping environment** (RXNMapper needs its own transformers version):
   ```bash
   python3.11 -m venv envs/rxnmapper
   envs/rxnmapper/bin/pip install -r envs/rxnmapper_requirements.txt
   ```
   Set `RXNMAPPER_PY=envs/rxnmapper/bin/python` in `config.sh`.
3. **Mechanisms**: `bash chat/fetch_mcsa.sh` downloads the [M-CSA](https://www.ebi.ac.uk/thornton-srv/m-csa/)
   entries (about 1,000 curated enzyme mechanisms) and builds `chat/data/mcsa_index.json`.
4. **Reference data** (paths in `config.sh`):
   - `BRENDA_FILE`: the BRENDA flat file (`brenda_<year>_<n>.txt`), free after registration at
     [brenda-enzymes.org](https://www.brenda-enzymes.org/download.php).
   - `METANETX_DIR`: a folder with the MetaNetX tables `chem_prop.tsv`, `reac_prop.tsv` and `reac_smi.csv`
     (the version distributed with [Selenzyme](https://github.com/pablocarb/selenzy), which includes reaction SMILES).
5. **Model access**: request access to [txgemma-9b-chat](https://huggingface.co/google/txgemma-9b-chat).

## What happens

| Step | Script | What it does |
|---|---|---|
| 1 | `infer_attention.py` | Gemma4EC prediction, top-3 alternatives, attention per SMILES token |
| 2 | `chat/reaction_facts.py` | names (MetaNetX), cofactor roles, bonds formed/broken (RXNMapper or substructure matching, whichever needs fewer bond edits), known reactions with the same participants, attention per atom |
| 3 | `chat/prepare_v2.py` | 3–5 candidate enzymes (EC 4 digits) from MetaNetX and BRENDA; a mechanism reference for each (M-CSA entry, else a class description in `chat/mechanism_kb.py`); summary, caveats and confidence written by code |
| 4 | `chat/explain_v2.py` | TxGemma-9B-Chat chooses the enzyme (majority over 5 shuffled asks), writes the mechanism from the reference, then checks its answer against the facts; drafts that mention cofactors or EC numbers not supported by the facts are redone |

Records with inconsistent data (unbalanced, several reaction sites) are flagged in the report and the model is told
to say so instead of inventing steps.

## Options

| Variable | Default | Effect |
|---|---|---|
| `CHAT_MODEL` | `google/txgemma-9b-chat` | any Gemma chat model, e.g. `google/gemma-3-27b-it` |
| `CPU=1` | off | run the chat model on CPU (about 10 minutes per reaction on 11 cores) |
| `LOAD_IN_4BIT=1` | off | 4-bit Gemma4EC in step 1 |
| `VOTES`, `MAX_RETRIES` | 5, 2 | enzyme votes; rewrite attempts |

On a cluster: `slurm/run_mechanistic_v2.sh` (GPU) and `slurm/run_mechanistic_v2_cpu.sh` (CPU).

## Fine-tuning the explainer (optional)

`chat/finetune_explainer.py` fine-tunes TxGemma-9B-Chat with LoRA on explanations written by a larger Gemma
(distillation). Only explanations grounded in an M-CSA entry or a class description, with a consistent enzyme vote,
are kept. Cluster scripts: `slurm/run_facts_array.sh`, `slurm/run_mechanistic_v2.sh` with `CHUNKED=1`,
`slurm/run_finetune_explainer.sh`.

## Limitations

The explanations are model-generated. They are grounded in the computed facts and the curated mechanism, but can
still contain errors, for example details copied from an M-CSA entry for a related substrate. Check them before use.
