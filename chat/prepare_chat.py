#!/usr/bin/env python3
"""
Prepare inputs for the chat explanation pipeline (chat/explain_chat.py). CPU only.

Per reaction (attn_out/summary.tsv + attn_out/reaction_facts.json):
  - candidate EC numbers (4 digits): BRENDA enzymes of the predicted sub-subclass, scored by how many of the
    reaction's participants and cofactors their own reactions mention. MetaNetX supplies the reaction's
    components (names, formulas, cofactor roles, co-product completion) via reaction_facts.py, not candidates
  - a plain-language summary, bond changes in words, caveats and attention, all written by code from the facts
  - a mechanism reference for every candidate (chat/mechanism_kb.py: class card > M-CSA exact > M-CSA analog), with
    residue numbers removed (they belong to one crystal structure, and the model copied them onto other enzymes)
    and cut to --max_ref_chars
  - a record check (reaction_facts.py): with --drop_broken, records that lose > 50% of their heavy atoms, show no
    bond change are not explained (written with a skip_reason instead)

Usage (gemma4ec env):
    python chat/prepare_chat.py [--attn_dir attn_out] [--out chat/prompts/chat_inputs.json]
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
from rdkit import Chem, RDLogger

sys.path.insert(0, str(Path(__file__).parent))
from brenda_refs import live_enzymes, normalize_ec3, parse_brenda_for_ec3s  # noqa: E402
from mechanism_kb import MechanismKB  # noqa: E402

RDLogger.DisableLog('rdApp.*')

# what each cofactor role does, and the co-product it leaves (usually omitted from reaction records)
ROLE_TEXT = [
    (r"^acyl-CoA", "donates its acyl group; CoA is released", "CoA"),
    (r"^coenzyme A", "is the CoA acceptor/leaving group", None),
    (r"^NADP\+", "accepts a hydride and becomes NADPH", "NADPH"),
    (r"^NAD\+", "accepts a hydride and becomes NADH", "NADH"),
    (r"^NADPH", "supplies the reducing equivalents (electrons) and becomes NADP+", "NADP+"),
    (r"^NADH", "supplies the reducing equivalents (electrons) and becomes NAD+", "NAD+"),
    (r"^FMNH2|^FADH2", "is the reduced flavin that supplies electrons", "FMN/FAD"),
    (r"^FAD|^FMN", "is an oxidised flavin electron acceptor", None),
    (r"^ATP", "is the phosphoryl/adenylyl donor", "ADP or AMP"),
    (r"^CDP-activated", "donates its phospho-head group; CMP is released", "CMP"),
    (r"^S-adenosyl", "donates a methyl group", "S-adenosyl-L-homocysteine"),
    (r"^O2", "is the oxidant", None),
]
CHECK_TERMS = {
    "biotin": r"biotin", "thiamine diphosphate": r"thiamin|\bTPP\b|\bThDP\b", "PLP": r"\bPLP\b|pyridoxal",
    "NAD(P)": r"\bNAD", "FAD": r"\bFAD", "FMN": r"\bFMN", "heme/P450": r"\bhaem|\bheme|P450|Compound I|\bFe\b|iron",
    "ATP": r"\bATP\b|\bADP\b", "CoA": r"\bCoA\b|coenzyme A", "SAM": r"adenosylmethionine|\bSAM\b",
    "zinc": r"\bZn|zinc", "magnesium": r"\bMg|magnesium", "manganese": r"\bMn2|manganese",
}


def short(name, n=48):
    return name if len(name) <= n else name[:n - 1] + "…"


def keywords(mol_info):
    """Lower-case words that identify the participants in enzyme reaction text."""
    kw = set()
    for m in mol_info:
        if m.get("role") and not m["role"].startswith(("CDP", "acyl-CoA")):
            continue
        if m.get("class"):
            kw.add(m["class"].lower())
        for w in re.split(r"[^a-z]+", m["name"].lower()):
            if len(w) >= 6 and w not in {"unknown", "metanetx", "connectivity"}:
                kw.add(w)
    return kw


def changes_in_words(mapping, names):
    out = []
    lab = lambda m: names.get(m, m)
    for c in mapping.get("changes", []):
        c2 = re.sub(r"\((Reactant \d+|Product \d+), ([^)]*)\)", lambda m: f"({m.group(2)} of {short(lab(m.group(1)), 40)})", c)
        c2 = re.sub(r"(\b[A-Z][a-z]?)1\d{5}\b", r"\1", c2)          # private ids of atoms that leave
        c2 = c2.replace("(the ", "(").replace(" leaves with a co-product not listed in the record)", " leaves)")
        c2 = c2.replace("FORMED", "new").replace("BROKEN", "broken").replace("CHANGED", "changed")
        out.append(c2)
    return out


def separate_sites(mapping, mols_by_label):
    """Number of separate reaction sites (centre atoms > 2 bonds apart) on the main substrate."""
    left = mapping.get("mapped_rxn", "").partition('>>')[0]
    if not left:
        return 1
    centre = {int(n) for n in re.findall(r"\b[A-Z][a-z]?(\d+) \(Reactant", ' '.join(mapping.get("changes", []))) if int(n) < 100000}
    best = 1
    for smi in left.split('.'):
        m = Chem.MolFromSmiles(smi)
        if m is None:
            continue
        idx = [a.GetIdx() for a in m.GetAtoms() if a.GetAtomMapNum() in centre]
        if len(idx) < 2:
            continue
        dm = Chem.GetDistanceMatrix(m)
        comps, seen = 0, set()
        for i in idx:
            if i in seen:
                continue
            comps += 1
            stack = [i]
            while stack:
                k = stack.pop()
                if k in seen:
                    continue
                seen.add(k)
                stack += [j for j in idx if j not in seen and dm[k][j] <= 1]
        best = max(best, comps)
    return best


def build_summary(f, role_of, ec3=None):
    mols = f["molecules"]
    subs = [m for m in mols if m["label"].startswith("Reactant") and (not m["role"] or m["role"].startswith(("acyl-CoA", "CDP")))]
    cos = [m for m in mols if m["label"].startswith("Reactant") and m not in subs and m["role"] not in ("H+", "H2O")]
    prods = [m for m in mols if m["label"].startswith("Product")]
    omitted = []
    comp = f.get("completion")
    for m in ([] if comp else cos + subs):     # a completed record already lists its co-products
        for pat, _, coprod in ROLE_TEXT:
            if m["role"] and re.search(pat, m["role"]) and coprod:
                omitted.append(coprod)
    o2 = any(m["role"] and m["role"].startswith("O2") for m in cos)
    chg = ' '.join(f["mapping"].get("changes", []))
    if comp:
        pass
    elif o2 and re.search(r"O\d+ \(Reactant \d+, O\)", chg) and "FORMED" in chg:
        omitted.append("H2O (second O atom of O2)")
    elif o2:
        omitted.append("H2O2 or H2O")
    gone = f["mapping"].get("reactant_atoms_not_in_products", {})
    acid = "carboxylic acid/carboxylate"
    # CO2 is inferred only for a predicted carboxy-lyase: elsewhere a lost carboxylate is a dropped co-product
    if not comp and (ec3 or "").startswith("4.1.1") and len(subs) == 1 and gone and \
            sum(m.get("groups", {}).get(acid, 0) for m in subs) > sum(p.get("groups", {}).get(acid, 0) for p in prods):
        omitted.append("CO2")
    text = (' + '.join(short(m["name"]) for m in subs + cos) + " → " + ' + '.join(short(m["name"]) for m in prods)
            + (f" (+ {', '.join(dict.fromkeys(omitted))}, not listed in the record)" if omitted else "") + "."
            + (f" Participants not in the record ({', '.join(short(n, 40) for n in comp['added_reactants'] + comp['added_products'])}) "
               f"were added from MetaNetX reaction {comp['mnx']}." if comp else ""))
    roles = []
    for m in cos + subs:
        for pat, what, _ in ROLE_TEXT:
            if m["role"] and re.search(pat, m["role"]):
                roles.append(f"{short(m['name'], 40)} {what}")
                break
    if roles:
        text += " " + "; ".join(roles) + "."
    return text


AA3 = "Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val"


def clean_reference(text, max_chars):
    """Residue numbers out ('Lys123' -> 'a Lys', 'His-57' -> 'a His'), then cut at a sentence end."""
    text = re.sub(rf"\b(?:the |a |an )?({AA3})[- ]?\d+[A-Z]?(?:({AA3}))?\b", lambda m: ("an " if m.group(1)[0] in "AEIOU" else "a ") + m.group(1) + (f"→{m.group(2)} mutation" if m.group(2) else ""), text)
    if len(text) > max_chars:
        cut = text[:max_chars]
        text = cut[:cut.rfind(". ") + 1] if ". " in cut else cut.rstrip() + " …"
    return text


def attention_line(a):
    if not a:
        return "Attention: not available."
    c, frac = a["share"].get("reaction-centre atoms", 0.0), a["centre_atom_fraction"]
    enr = c / frac if frac else 0
    verdict = "enriched on the reaction centre" if enr >= 1.5 else "depleted on the reaction centre" if enr < 0.7 else \
        "roughly proportional to the number of centre atoms"
    cof = a["share"].get("cofactor/cosubstrate atoms (outside the centre)", 0.0)
    return (f"Attention: the reaction-centre atoms are {frac:.0%} of all heavy atoms and received {c:.0%} of Gemma4EC's "
            f"attention (x{enr:.1f}, {verdict}); cofactor/cosubstrate atoms received {cof:.0%}. "
            "Attention shows what the model looked at, not what caused the prediction.")


def caveats(f, n_sites, known_ec4s):
    out = []
    chk = f.get("record_check") or {}
    if chk.get("heavy_atoms_lost", 0) > 0.5:
        out.append(f"The record loses {chk['heavy_atoms_lost']:.0%} of its heavy atoms between substrates and products: "
                   "it is a fragment of the real reaction.")
    if chk and chk.get("n_bond_changes") == 0:
        out.append("No bond changes were found: the record may list the same molecules on both sides.")
    if chk.get("unnamed_main"):
        out.append(f"{chk['unnamed_main']} main participant(s) have no database name.")
    for m in f["molecules"]:
        if m.get("name_match") == "same connectivity only; stereo or protonation differs" and not m.get("role") \
                and "@" in m["smiles"]:
            out.append(f"The name of {m['label']} ({short(m['name'], 40)}) comes from a MetaNetX entry that only shares "
                       f"its connectivity; check it against the formula {m['formula']}.")
    mp = f["mapping"]
    if mp.get("unmapped_product_atoms"):
        out.append(f"The product has {mp['unmapped_product_atoms']} atom(s) with no source in the reactants: the record is "
                   "unbalanced or mis-drawn.")
    # a record completed from MetaNetX is a curated whole reaction: several sites there (ligases, transferases) are real
    if n_sites > 1 and not f.get("completion"):
        out.append(f"The substrate changes at {n_sites} separate sites, which a single enzymatic step rarely does: the "
                   "record may merge several steps.")
    if "error" in mp:
        out.append("Atom mapping failed; bond changes are unknown.")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attn_dir", default="attn_out")
    ap.add_argument("--brenda_file", default=os.environ.get("BRENDA_FILE", "data/external/brenda_2026_1.txt"))
    ap.add_argument("--n_candidates", type=int, default=5)
    ap.add_argument("--max_ref_chars", type=int, default=700)
    ap.add_argument("--drop_broken", action="store_true", help="do not explain records that fail the record check")
    ap.add_argument("--out", default="chat/prompts/chat_inputs.json")
    args = ap.parse_args()
    attn_dir = Path(args.attn_dir)

    df = pd.read_csv(attn_dir / "summary.tsv", sep='\t')
    facts = {f["rxn_id"]: f for f in json.load(open(attn_dir / "reaction_facts.json"))}
    ec3_set = {normalize_ec3(e) for e in df["predicted_ec"]}   # candidates come from the predicted class only
    ec3_set.discard(None)
    print(f"BRENDA for {sorted(ec3_set)} …", flush=True)
    brenda = parse_brenda_for_ec3s(Path(args.brenda_file), ec3_set)
    by_ec4 = {e["ec4"]: e for v in brenda.values() for e in v}
    kb = MechanismKB()

    records = []
    for _, row in df.iterrows():
        rid, smiles = int(row["reaction"]), row["rxn_smiles"]
        f = facts[rid]
        ec3 = normalize_ec3(row["predicted_ec"])
        names = {m["label"]: m["name"] for m in f["molecules"]}
        roles = [m["role"] for m in f["molecules"] if m["label"].startswith("Reactant")]
        role_of = {m["label"]: m["role"] for m in f["molecules"]}

        # candidates: known reactions first, then BRENDA enzymes of the class, scored on how many
        # of this reaction's participants and cofactors their own reactions mention
        kw = keywords(f["molecules"])
        cof_kw = {t for r in roles if r for t in ("cdp", "coa", "nadp", "nad+", "fmn", "fad", "atp", "o2")
                  if t in r.lower().replace("-", "")}
        cands = {}
        # Candidates come from BRENDA alone: the enzymes of the predicted sub-subclass, scored on
        # how many of this reaction's participants and cofactors their own reactions mention.
        # MetaNetX is used only for the reaction's components (names, formulas, cofactor roles,
        # co-product completion), computed upstream in reaction_facts.py.
        for e in live_enzymes([dict(x) for x in brenda.get(ec3, [])], 10_000):
            text = (e["name"] + " " + ' '.join(e["reactions"])).lower() + " " + e.get("substrates_text", "")
            kwf = sum(w in text for w in kw) / max(len(kw), 1)
            cof = sum(t in text for t in cof_kw) / max(len(cof_kw), 1) if cof_kw else 0
            score = kwf + 0.3 * cof
            if not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", e["ec4"]):
                continue
            if e["ec4"] not in cands or cands[e["ec4"]]["score"] < score:
                cands.setdefault(e["ec4"], {"ec4": e["ec4"]}).update(score=max(score, cands.get(e["ec4"], {}).get("score", 0)))
        top = sorted(cands.values(), key=lambda c: -c["score"])[:args.n_candidates]
        mols_sub = [Chem.MolFromSmiles(m["smiles"]) for m in f["molecules"]
                    if m["label"].startswith("Reactant") and not (m["role"] or "").startswith(("NAD", "FAD", "FMN", "O2", "H"))]
        for c in top:
            b = by_ec4.get(c["ec4"], {})
            c["name"] = b.get("name") or "(not in BRENDA)"
            c["reaction"] = (b.get("reactions") or [""])[0][:220]
            enz_text = c["name"] + " " + ' '.join(b.get("reactions", []))
            sel = kb.select(c["ec4"], roles, mols_sub, f["mapping"].get("changes", []), enz_text)
            c["reference"] = dict(zip(("kind", "title", "text", "source"), sel)) if sel else None
            if c["reference"]:
                c["reference"]["text"] = clean_reference(c["reference"]["text"], args.max_ref_chars)

        if not top:
            print(f"rxn{rid:02d}  EC {ec3}: no candidate EC numbers (sub-subclass empty or transferred); skipped", flush=True)
            continue
        n_sites = separate_sites(f["mapping"], None)
        rec = {
            "rxn_id": rid, "rxn_smiles": smiles, "true_ec": normalize_ec3(row["true_ec"]), "predicted_ec": ec3,
            "topk_ec": row.get("topk_ec", ""), "record_check": f.get("record_check"), "completion": f.get("completion"),
            "skip_reason": None if (f.get("record_check") or {}).get("ok", True) or not args.drop_broken
            else "record fails the check: " + json.dumps(f["record_check"]),
            "summary": build_summary(f, role_of, ec3),
            "changes": changes_in_words(f["mapping"], names),
            "groups": None,
            "caveats": caveats(f, n_sites, []),
            "attention": attention_line(f.get("attention_atoms")),
            "candidates": top,
            "allowed_text": ' '.join([m["name"] + " " + (m["role"] or "") for m in f["molecules"]]),
            "check_terms": CHECK_TERMS,
        }
        records.append(rec)
        print(f"rxn{rid:02d}  EC {ec3}  candidates {[c['ec4'] for c in top]}  "
              f"refs {[c['reference']['kind'] if c['reference'] else '-' for c in top]}", flush=True)
    Path(args.out).write_text(json.dumps(records, indent=1, ensure_ascii=False))
    print(f"Saved {len(records)} → {args.out}")


if __name__ == "__main__":
    main()
