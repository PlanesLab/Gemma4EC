#!/usr/bin/env python3
"""
Build mechanistic-explanation prompts for TxGemma-9B-Chat.

For each reaction in attn_out/summary.tsv (written by infer_attention.py), assembles a prompt with:
  - the reaction SMILES, split into numbered reactants and products
  - Gemma4EC's predicted EC sub-subclass and its top-k alternatives with probabilities
  - the BRENDA entries of the predicted sub-subclass (literature/organism markers removed), ranked
    by how similar each enzyme's known reactions (Selenzyme MetaNetX tables) are to the query
  - the tokenized SMILES with Gemma4EC's attention, summarized as the share per molecule and
    the most-attended tokens shown in their SMILES context

Attention comes from <tag>_smiles_attn.npz (EC-generating positions, all layers and heads); if
that file is missing, it falls back to the last-layer bertviz HTML.

Output: chat/prompts/mechanistic_prompts.json. Its BRENDA and ranking helpers are also used by chat/prepare_v2.py.

Usage:
    python chat/build_mechanistic_prompts.py [--attn_dir attn_out] [--brenda_file ...]
"""

import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

_HEADER_RE = re.compile(r'^[A-Z][A-Z_]{3,}$')
TARGET_SECTIONS = {"RECOMMENDED_NAME", "SYSTEMATIC_NAME", "REACTION", "REACTION_TYPE", "SUBSTRATE_PRODUCT"}


# ── BRENDA parsing ─────────────────────────────────────────────────────────────

def normalize_ec3(ec_id) -> str | None:
    parts = str(ec_id).strip().split('.')
    if len(parts) < 3:
        return None
    try:
        return '.'.join(str(int(p)) for p in parts[:3])
    except ValueError:
        return None


def clean_brenda_text(text: str) -> str:
    """Drop organism/literature markers (#12#, <34>) and the bracketed commentary after a reaction."""
    text = re.split(r'\s\((?=#)', text)[0]
    text = re.sub(r'#[\d,]+#\s*|<[\d,]+>|\{[^}]*\}', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def parse_brenda_for_ec3s(brenda_file: Path, ec3_set: set[str]) -> dict[str, list[dict]]:
    """Return {ec3: [enzyme entries]} for the requested EC sub-subclasses only."""
    classes: dict[str, list[dict]] = defaultdict(list)
    current_id, current_section, current_data, buf = None, None, {}, []

    def flush():
        if buf and current_section in TARGET_SECTIONS:
            current_data.setdefault(current_section, []).append(' '.join(buf))
        buf.clear()

    with open(brenda_file, encoding='utf-8', errors='replace') as fh:
        for raw in fh:
            line = raw.rstrip('\n')
            stripped = line.strip()
            if stripped == '///':
                flush()
                ec3 = normalize_ec3(current_id) if current_id else None
                if ec3 in ec3_set:
                    uniq = lambda xs: list(dict.fromkeys(clean_brenda_text(x) for x in xs if clean_brenda_text(x)))
                    classes[ec3].append({
                        "ec4":        current_id,
                        "name":       (uniq(current_data.get("RECOMMENDED_NAME", [])) or [""])[0],
                        "systematic": (uniq(current_data.get("SYSTEMATIC_NAME", [])) or [""])[0],
                        "types":      uniq(current_data.get("REACTION_TYPE", []))[:3],
                        "reactions":  uniq(current_data.get("REACTION", []))[:2],
                        # all substrate/product pairs, lower case, for keyword matching (prepare_v2.py)
                        "substrates_text": ' '.join(uniq(current_data.get("SUBSTRATE_PRODUCT", [])))[:200_000].lower(),
                    })
                current_id, current_section, current_data = None, None, {}
                buf = []
                continue
            if line.startswith('ID\t'):
                flush()
                current_id, current_section, current_data = line[3:].strip(), None, {}
                buf = []
                continue
            if current_id is None:
                continue
            if stripped and '\t' not in line and _HEADER_RE.match(stripped):
                flush()
                current_section = stripped
                continue
            if current_section not in TARGET_SECTIONS:
                continue
            if not stripped:
                flush()
            elif line.startswith('\t'):
                buf.append(stripped)
            elif '\t' in line:
                flush()
                content = line.partition('\t')[2].strip()
                if content:
                    buf.append(content)
    return classes


# ── ranking BRENDA enzymes by similarity of their known reactions to the query ──

def _rxn_fp(smiles: str):
    """Reaction difference fingerprint (what changes between reactants and products)."""
    from rdkit.Chem import rdChemReactions
    try:
        l, r = smiles.replace('->>', '>>').split('>>', 1)
        return rdChemReactions.CreateDifferenceFingerprintForReaction(
            rdChemReactions.ReactionFromSmarts(f"{l}>>{r}", useSmiles=True))
    except Exception:
        return None


def _rxn_sim(a, b) -> float:
    # A structural fingerprint was tried too: it penalizes MetaNetX reactions for listing CO2/H+
    # that ECReact omits, and pushed exact matches down (e.g. EC 4.1.1.86 for 2,4-diaminobutanoate).
    from rdkit import DataStructs
    return DataStructs.TanimotoSimilarity(a, b)


def load_reference_reactions(ref_dir: Path, ec3_set: set[str]) -> dict[str, list[tuple[str, object]]]:
    """{ec4: [(reaction SMILES, fingerprint)]} from Selenzyme's MetaNetX tables, for EC4s in the given EC3s."""
    from rdkit import RDLogger
    RDLogger.DisableLog('rdApp.*')
    smi = pd.read_csv(ref_dir / "reac_smi.csv", dtype=str).dropna().set_index("RID")["SMILES"]
    prop = pd.read_csv(ref_dir / "reac_prop.tsv", sep='\t', comment='#', header=None, dtype=str, usecols=[0, 3])
    by_ec4 = defaultdict(list)
    for rid, ecs in prop.dropna().itertuples(index=False):
        if rid not in smi.index:
            continue
        for ec in ecs.split(';'):
            if ec.count('.') == 3 and normalize_ec3(ec) in ec3_set:
                fp = _rxn_fp(smi[rid])
                if fp is not None:
                    by_ec4[ec].append((smi[rid], fp))
    return by_ec4


def rank_enzymes(query_smiles: str, enzymes: list[dict], ref: dict, max_enzymes: int) -> list[dict]:
    """Order enzymes by the Tanimoto similarity of their closest known reaction to the query; drop deleted/transferred EC numbers."""
    q = _rxn_fp(query_smiles)
    live = [e for e in enzymes if not re.search(r'\b(deleted|transferred)\b', e["name"], re.I)]
    for e in live:
        sims = [_rxn_sim(q, fp) for _, fp in ref.get(e["ec4"], [])] if q is not None else []
        e.update(similarity=max(sims) if sims else None)
    return sorted(live, key=lambda e: -(e["similarity"] if e["similarity"] is not None else -1))[:max_enzymes]


def format_brenda(ec3: str, enzymes: list[dict], max_chars: int) -> str:
    if not enzymes:
        return f"No BRENDA entry found for EC {ec3}."
    lines = []
    for e in enzymes:
        sim = e.get("similarity")
        head = f"- EC {e['ec4']} {e['name']}" + (f" [similarity to query: {sim:.2f}]" if sim is not None else "")
        if e["systematic"]:
            head += f" (systematic: {e['systematic']})"
        lines.append(head)
        if e["types"]:
            lines.append(f"  type: {'; '.join(e['types'])}")
        for r in e["reactions"]:
            lines.append(f"  reaction: {r[:250]}")
    text = '\n'.join(lines)
    return text if len(text) <= max_chars else text[:max_chars].rsplit('\n- ', 1)[0] + "\n[... more enzymes in this sub-subclass]"


# ── attention ─────────────────────────────────────────────────────────────────

def load_attention(attn_dir: Path, tag: str, sm_start: int, sm_end: int):
    """(tokens, weights, char_spans or None). Prefers the .npz from infer_attention.py."""
    npz = attn_dir / f"{tag}_smiles_attn.npz"
    if npz.exists():
        d = np.load(npz, allow_pickle=True)
        return list(d["tokens"]), d["weights"].astype(float), d["char_spans"]
    html_path = attn_dir / f"{tag}_bertviz.html"   # legacy: last layer only, last query token
    if not html_path.exists():
        return [], np.array([]), None
    m = re.search(r'params\s*=\s*(\{.*?\});', html_path.read_text(encoding='utf-8'), re.DOTALL)
    if not m:
        return [], np.array([]), None
    entry = json.loads(m.group(1))['attention'][0]
    # the HTML is sliced to start at the first SMILES token
    n = sm_end - sm_start
    row = np.array(entry['attn'], dtype=np.float32).mean(axis=(0, 1))[-1][:n]
    return entry['left_text'][:n], row / (row.sum() or 1.0), None


def molecule_spans(smiles: str):
    """[(label, smiles, char_start, char_end)] for each reactant and product."""
    out, pos = [], 0
    left, _, right = smiles.partition('>>')
    for side, label in ((left, "Reactant"), (right, "Product")):
        for k, mol in enumerate(side.split('.'), 1):
            out.append((f"{label} {k}", mol, pos, pos + len(mol)))
            pos += len(mol) + 1
        pos += 1  # second '>' of '>>' (the loop already skipped the first)
    return out


def mol_of(span, mols):
    s, e = span
    mid = (s + e) / 2
    for label, _, a, b in mols:
        if a <= mid < b:
            return label
    return "arrow"


def format_attention(smiles, tokens, weights, spans, top_n):
    if len(weights) == 0:
        return "Attention not available.", ""
    mols = molecule_spans(smiles)
    tok_line = ' '.join(f"{t.strip() or '_'}[{w:.0%}]" if w >= 0.01 else (t.strip() or '_')
                        for t, w in zip(tokens, weights))
    lines = []
    if spans is not None:
        share = defaultdict(float)
        for sp, w in zip(spans, weights):
            share[mol_of(sp, mols)] += w
        lines.append("Attention share per molecule: " +
                     ", ".join(f"{lab} {share[lab]:.0%}" for lab, *_ in mols if share[lab] >= 0.005))
    lines.append(f"Most attended tokens (of {len(tokens)}):")
    for i in np.argsort(-weights)[:top_n]:
        if spans is not None:
            s, e = int(spans[i][0]), int(spans[i][1])
            ctx = f"{smiles[max(0, s - 10):s]}«{smiles[s:e]}»{smiles[e:e + 10]}"
            lines.append(f"  {weights[i]:.1%}  {mol_of((s, e), mols)}: ...{ctx}...")
        else:
            lines.append(f"  {weights[i]:.1%}  token '{tokens[i].strip()}' (#{i + 1})")
    return '\n'.join(lines), tok_line


# ── prompt template ────────────────────────────────────────────────────────────

PROMPT_TEMPLATE = """\
You are an expert enzymologist and mechanistic chemist.

Gemma4EC, a TxGemma-9B model fine-tuned to classify enzymatic reactions (about 0.91 MCC at the sub-subclass level on held-out reactions), was given the reaction below and predicted its EC sub-subclass. Check its prediction with your own chemical reasoning; do not assume it is correct.

Reaction SMILES: {rxn_smiles}
{molecules}

Gemma4EC prediction: EC {ec}
Alternatives considered (beam-search probability): {alternatives}

BRENDA enzymes in EC {ec}, most similar first (similarity = Tanimoto between reaction difference fingerprints of the query and the enzyme's closest known reaction, 1 = identical; a shared cofactor change such as NAD+ -> NADH alone can give high values):
{brenda_info}

Gemma4EC attention over the reaction SMILES (averaged over all layers and heads, from the positions that generate the EC number; % of the attention on the SMILES):
{attention_summary}
Tokenized SMILES (attention shown where >= 1%):
{smiles_tokens}

Answer in these sections:
1. Transformation: which bonds are broken and formed, and which groups change, comparing reactants and products.
2. Mechanism: the likely catalytic mechanism, cofactors or cosubstrates (e.g. NAD(P)+, ATP, CoA) and their role.
3. EC assessment: is the reaction consistent with EC {ec}? Name the BRENDA enzyme(s) above that best match it, or say if an alternative fits better.
4. Attention: do the most attended tokens fall on the reaction centre or on cofactor/spectator groups? Attention shows what the model looked at, not proof of what drove the prediction.
5. Confidence: high, medium or low, and why.
Be concise and specific; refer to atoms and groups in the SMILES."""


# ── facts-based prompt (chat/reaction_facts.py output) ────────────────────────

FACTS_TEMPLATE = """\
You are an expert enzymologist and mechanistic chemist.

Gemma4EC, a TxGemma-9B model fine-tuned to classify enzymatic reactions (about 0.91 MCC at the EC sub-subclass level on held-out reactions), predicted the EC sub-subclass of the reaction below. Explain the reaction and assess the prediction; do not assume it is correct.

All facts below were computed with cheminformatics tools (RDKit, RXNMapper atom mapping, MetaNetX/BRENDA lookups). Base your answer on them and do not re-derive bond changes from the SMILES yourself. If the facts look inconsistent (low mapping confidence, unbalanced record, implausible product), say so instead of inventing chemistry.

Reaction SMILES (for reference only): {rxn_smiles}

## Participants
{participants}
Note: reaction records in this dataset often omit co-products (e.g. NAD(P)H, CoA, CMP, H2O, H2O2).

## Atom-mapped changes ({map_conf})
{changes}
{provenance}
Functional groups (reactants that donate atoms vs products; pure cofactors excluded): {groups}

## Known reactions in MetaNetX with the same participants (match = shared-participant Jaccard, 1 = identical)
{known}

## Gemma4EC prediction
EC {ec}; alternatives (beam-search probability): {alternatives}

## BRENDA enzymes in EC {ec}, most similar first
(similarity = Tanimoto between reaction difference fingerprints of the query and the enzyme's closest known reaction; a shared cofactor change alone can give high values)
{brenda_info}

## Gemma4EC attention projected onto atoms (averaged over layers and heads, from the positions generating the EC)
{attention}

## Task
Answer in these sections:
1. What happens: one or two sentences in plain chemical terms (substrate → product, which group is converted, the role of each cosubstrate).
2. Mechanism: the established catalytic mechanism of this enzyme type (cofactor chemistry and key steps), consistent with the computed changes.
3. EC assessment: does the reaction fit EC {ec}? Name the best-matching EC number (4 digits) from the known reactions or the BRENDA list and justify it with the participants and changes. Say so if an alternative fits better.
4. Attention: is attention enriched on the reaction centre, on the cofactor, or diffuse? Use the numbers. Attention shows what the model looked at, not proof of what drove the prediction.
5. Caveats and confidence: data issues, and an overall confidence (high, medium or low) with the reason.
Be concise (under 350 words) and specific."""


def format_facts(f: dict) -> dict:
    mols = f["molecules"]
    part = []
    for m in mols:
        role = f"cofactor/cosubstrate: {m['role']}" if m["role"] else "substrate/product"
        note = "" if m.get("name_match") in ("exact", "same stereo, different protonation", "none", None) else \
               f" [name from a MetaNetX entry with {m['name_match']}: check it against the formula]"
        part.append(f"{m['label']}: {m['name']}{note} | {m['formula']} | {role}")
    mp = f["mapping"]
    if "error" in mp:
        changes, prov, conf = f"Atom mapping failed ({mp['error']}).", "", "n/a"
    else:
        conf = (f"RXNMapper, confidence {mp['confidence']}" if mp["method"] == "RXNMapper" else
                "maximum-common-substructure mapping, chosen because it needs fewer bond edits than RXNMapper")
        changes = '\n'.join(f"- {c}" for c in mp["changes"]) or "- no bond changes detected"
        src = '; '.join(f"{p} atoms come from " + ', '.join(f"{r} ({n})" for r, n in c.items())
                        for p, c in mp["product_atom_sources"].items())
        gone = ', '.join(f"{r}: {n} heavy atoms" for r, n in mp["reactant_atoms_not_in_products"].items())
        prov = f"Provenance: {src}." + (f"\nReactant atoms that reach no listed product (leave in omitted co-products): {gone}." if gone else "") \
               + (f"\nProduct atoms without a reactant source (unbalanced record): {mp['unmapped_product_atoms']}." if mp["unmapped_product_atoms"] else "")
    # cosubstrates that donate atoms to a product (acyl-CoA, CDP-X) count as substrates here
    donors = {r for src in mp.get("product_atom_sources", {}).values() for r, n in src.items() if n > 1}
    tot = {"R": defaultdict(int), "P": defaultdict(int)}
    for m in mols:
        if not m["role"] or m["label"] in donors:
            for g, n in m["groups"].items():
                tot[m["label"][0]][g] += n
    lost = [g for g in tot["R"] if tot["P"].get(g, 0) < tot["R"][g]]
    gained = [g for g in tot["P"] if tot["R"].get(g, 0) < tot["P"][g]]
    groups = f"lost: {', '.join(lost) or 'none'}; gained: {', '.join(gained) or 'none'}"
    known = '\n'.join(f"- EC {', '.join(k['ec'])} (match {k['match']}, {k['mnx']}): {k['equation']}"
                      for k in f["known_reactions"]) or "- none with match >= 0.5"
    a = f.get("attention_atoms") or {}
    if a:
        sh = a["share"]
        c = sh.get("reaction-centre atoms", 0.0)
        frac = a["centre_atom_fraction"]
        lines = [f"- reaction-centre atoms are {frac:.0%} of all heavy atoms and received {c:.0%} of the attention"
                 + (f" (enrichment x{c / frac:.1f})" if frac else "")]
        lines += [f"- {k}: {v:.0%}" for k, v in sh.items() if k != "reaction-centre atoms"]
        lines.append("- most attended atoms: " + '; '.join(
            f"{t['atom']} ({t['env']}{', centre' if t['in_centre'] else ''}) {t['weight']:.1%}" for t in a["top_atoms"]))
        attention = '\n'.join(lines)
    else:
        attention = "not available"
    return dict(participants='\n'.join(part), map_conf=conf, changes=changes, provenance=prov,
                groups=groups, known=known, attention=attention)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attn_dir", default="attn_out")
    ap.add_argument("--brenda_file", default=os.environ.get("BRENDA_FILE", "data/external/brenda_2026_1.txt"))
    ap.add_argument("--out_file", default="chat/prompts/mechanistic_prompts.json")
    ap.add_argument("--ref_dir", default=os.environ.get("METANETX_DIR", "data/external/metanetx"),
                    help="Selenzyme MetaNetX tables (reac_smi.csv, reac_prop.tsv) used to rank BRENDA enzymes")
    ap.add_argument("--max_enzymes", type=int, default=12)
    ap.add_argument("--brenda_chars", type=int, default=3000)
    ap.add_argument("--top_tokens", type=int, default=12)
    ap.add_argument("--facts", default=None,
                    help="reaction_facts.json from chat/reaction_facts.py: use the facts-based prompt")
    args = ap.parse_args()
    attn_dir, out_file = Path(args.attn_dir), Path(args.out_file)

    df = pd.read_csv(attn_dir / "summary.tsv", sep='\t')
    ec3_set = {e for e in df['predicted_ec'].map(normalize_ec3) if e}
    print(f"Fetching BRENDA entries for: {sorted(ec3_set)}")
    brenda = parse_brenda_for_ec3s(Path(args.brenda_file), ec3_set)
    ref = load_reference_reactions(Path(args.ref_dir), ec3_set)
    print(f"  {sum(len(v) for v in ref.values())} reference reactions for {len(ref)} EC4s")

    facts = {f["rxn_id"]: f for f in json.load(open(args.facts))} if args.facts else {}

    records = []
    for _, row in df.iterrows():
        rxn_id, smiles = int(row['reaction']), row['rxn_smiles']
        ec3 = normalize_ec3(row['predicted_ec']) or str(row['predicted_ec'])
        tag = f"rxn{rxn_id:02d}"
        tokens, weights, spans = load_attention(attn_dir, tag, int(row['smiles_tok_start']), int(row['smiles_tok_end']))
        attn_summary, tok_line = format_attention(smiles, tokens, weights, spans, args.top_tokens)
        topk = [t.split(':') for t in str(row.get('topk_ec', '') or '').split(';') if ':' in t]
        alts = ', '.join(f"EC {normalize_ec3(e) or e} ({float(p):.0%})" for e, p in topk) or "not recorded"
        molecules = '\n'.join(f"{lab}: {mol}" for lab, mol, *_ in molecule_spans(smiles))
        enzymes = rank_enzymes(smiles, [dict(e) for e in brenda.get(ec3, [])], ref, args.max_enzymes)
        brenda_info = format_brenda(ec3, enzymes, args.brenda_chars)

        if args.facts:
            prompt = FACTS_TEMPLATE.format(ec=ec3, rxn_smiles=smiles, alternatives=alts, brenda_info=brenda_info,
                                           **format_facts(facts[rxn_id]))
        else:
            prompt = PROMPT_TEMPLATE.format(ec=ec3, rxn_smiles=smiles, molecules=molecules, alternatives=alts,
                                            brenda_info=brenda_info, attention_summary=attn_summary,
                                            smiles_tokens=tok_line or "N/A")
        records.append({
            "rxn_id": rxn_id, "rxn_smiles": smiles,
            "true_ec": normalize_ec3(row['true_ec']) or row['true_ec'],   # not shown to the model
            "predicted_ec": ec3, "topk_ec": alts,
            "smiles_tokens": [t for t in tokens], "attention_vector": [round(float(w), 4) for w in weights],
            "brenda_summary": brenda_info, "prompt": prompt,
        })
        print(f"  {tag}  EC {ec3}  {len(tokens)} SMILES tokens  "
              f"({'npz' if spans is not None else 'bertviz fallback'})")

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nSaved {len(records)} prompts → {out_file}")


if __name__ == "__main__":
    main()
