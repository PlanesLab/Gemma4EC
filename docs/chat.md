# Chat explanations

```bash
bash chat/explain.sh reactions.csv out_dir     # -> out_dir/explanations.md, explanations.json
```

`reactions.csv` needs a `rxn_smiles` column. On a cluster: `IN=reactions.csv OUT=out_dir sbatch slurm/run_chat.sh`.

## Setup

1. `cp config.sh.example config.sh` and set the paths below.
2. RXNMapper environment:
   ```bash
   python3.11 -m venv envs/rxnmapper
   envs/rxnmapper/bin/pip install -r envs/rxnmapper_requirements.txt
   ```
   Set `RXNMAPPER_PY=envs/rxnmapper/bin/python` in `config.sh`.
3. `bash chat/fetch_mcsa.sh` downloads the [M-CSA](https://www.ebi.ac.uk/thornton-srv/m-csa/) mechanisms.
4. In `config.sh`: `BRENDA_FILE` (BRENDA flat file, free registration at
   [brenda-enzymes.org](https://www.brenda-enzymes.org/download.php)) and `METANETX_DIR` (`chem_prop.tsv`,
   `reac_prop.tsv`, `reac_smi.csv`, as distributed with [Selenzyme](https://github.com/pablocarb/selenzy)).
5. Request access to [txgemma-9b-chat](https://huggingface.co/google/txgemma-9b-chat).

## Steps

| Step | Script | |
|---|---|---|
| 1 | `infer_attention.py` | Gemma4EC prediction and attention |
| 2 | `chat/reaction_facts.py` | molecule names (MetaNetX), bonds formed/broken (RXNMapper), attention per atom |
| 3 | `chat/prepare_chat.py` | 3–5 candidate enzymes (MetaNetX, BRENDA) with a mechanism reference each (M-CSA or `chat/mechanism_kb.py`) |
| 4 | `chat/explain_chat.py` | TxGemma-9B-Chat picks the enzyme, writes the mechanism and checks it against the facts |

## Options

| Variable | Default | |
|---|---|---|
| `CHAT_MODEL` | `google/txgemma-9b-chat` | any Gemma chat model |
| `CPU=1` | off | chat model on CPU |
| `LOAD_IN_4BIT=1` | off | 4-bit Gemma4EC in step 1 |
| `VOTES`, `MAX_RETRIES` | 5, 2 | enzyme votes, rewrite attempts |

## Evaluation

100 ECReact reactions with EC4 ground truth (`chat/eval/set/`):

```bash
IN=chat/eval/set/reactions.csv OUT=chat/eval/set/run sbatch slurm/run_chat.sh
python chat/evaluate_chat.py --run chat/eval/set/run --truth chat/eval/set/reactions.csv --out results/chat_eval
python chat/audit_explanations.py --run chat/eval/set/run --out results/chat_eval
python chat/eval/make_rating_sheet.py chat/eval/set/run/explanations.json --out chat/eval/ratings \
       --with_truth --truth_csv chat/eval/set/reactions.csv
python chat/eval/llm_rate.py chat/eval/ratings --model gpt-4.1        # and --model gemini-3.8-flash
python figures/chat_validation_figure.py                               # figures/chat/fig_chat_validation.png
python figures/chat_reaction_panels.py --rxn 9 --attn_dir out_dir --out figures/chat/rxn09   # reaction + attention panels
```

Explanations are model-generated and can contain errors; check them before use.
