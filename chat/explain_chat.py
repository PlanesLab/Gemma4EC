#!/usr/bin/env python3
"""
Mechanistic explanations with a Gemma chat model, grounded in computed facts and curated mechanisms.

Input: chat/prompts/chat_inputs.json from chat/prepare_chat.py. Per reaction, three kinds of model call:
  A. choose the EC number: the top candidate of the similarity ranking (prepare_chat.py) when it leads by more than
     --margin; otherwise the model chooses among the candidates within the margin (one call per shuffled order,
     majority vote), and abstains when no vote names one of them. On the 97-reaction evaluation the ranking alone was
     right in 58 cases and the 5-vote choice over all candidates in 44; the vote only helped when scores were close
  B. write MECHANISM + WHY EC for the chosen enzyme, applying the mechanism reference to this reaction; few-shot
     worked examples are given as earlier chat turns
  C. self-check against the facts and rewrite; programmatic checks (cofactors not supported by the facts or the
     reference, residue numbers, foreign EC numbers) decide which version is kept: the rewrite only when it has
     strictly fewer problems, and B is redone with explicit warnings if needed
Records that prepare_chat.py --drop_broken marked with a skip_reason, and abstentions, get no mechanism text.
The summary, caveats, attention and confidence are written by code (prepare_chat.py), not by the model.

Usage:
    python chat/explain_chat.py --model_id google/txgemma-9b-chat --out_prefix chat_out/explanations
"""

import argparse
import json
import os
import random
import re
from collections import Counter
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

FEW_SHOT = [
    ("""REACTION: ethanol + NAD+ → acetaldehyde (+ NADH, not listed in the record). NAD+ accepts a hydride and becomes NADH.
BOND CHANGES:
- changed bond C2 (CH2 of ethanol) – O3 (OH of ethanol): single → double
- C2 (CH2 of ethanol) loses 1 H
- O3 (OH of ethanol) loses 1 H
CHOSEN ENZYME: EC 1.1.1.1 alcohol dehydrogenase; reaction: a primary alcohol + NAD+ = an aldehyde + NADH + H+
MECHANISM REFERENCE (class card: NAD(P)+-dependent alcohol dehydrogenase): Alcohol dehydrogenases transfer a hydride from the carbon bearing the hydroxyl group (the carbinol C-H) to C4 of the nicotinamide ring of NAD(P)+, giving the carbonyl product and NAD(P)H; the hydroxyl proton is removed by a general base at the same time. In short-chain dehydrogenases/reductases (SDR) the base is a Tyr; in medium-chain (MDR) enzymes a catalytic Zn2+ binds the alcohol oxygen and lowers its pKa. No covalent intermediate is formed.""",
     """MECHANISM: Ethanol is oxidised at C2, the carbon bearing the hydroxyl group. A general base (a Zn2+-bound alkoxide in medium-chain alcohol dehydrogenases, a Tyr in short-chain ones) removes the proton of the O3 hydroxyl while the hydride on C2 is transferred to C4 of the NAD+ nicotinamide ring. This matches the computed changes: the C2–O3 bond becomes a double bond and C2 and O3 each lose one H, giving acetaldehyde and NADH. NAD+ contributes no atoms to the product; it is only the hydride acceptor.
WHY EC 1.1.1.1: the reaction oxidises a CH–OH group (EC 1.1) with NAD+ as the acceptor (EC 1.1.1), and its participants are those of alcohol dehydrogenase (primary alcohol + NAD+ = aldehyde + NADH)."""),
    ("""REACTION: L-ornithine → putrescine (+ CO2, not listed in the record).
BOND CHANGES:
- broken single bond C2 (CH of L-ornithine) – C (C leaves)
- C2 (CH of L-ornithine) gains 1 H
CHOSEN ENZYME: EC 4.1.1.17 ornithine decarboxylase; reaction: L-ornithine = putrescine + CO2
MECHANISM REFERENCE (class card: PLP-dependent amino-acid decarboxylase): Pyridoxal 5'-phosphate (PLP) is bound to an active-site Lys as an internal aldimine. The substrate alpha-amino group displaces the Lys (transaldimination) to form an external aldimine. The bond between C-alpha and the carboxylate breaks and CO2 leaves; the negative charge is delocalised into the protonated pyridine ring (quinonoid intermediate). Protonation of C-alpha and a second transaldimination release the amine product.""",
     """MECHANISM: The alpha-amino group of L-ornithine displaces the active-site Lys from PLP, forming an external aldimine. The bond between C2 (C-alpha) and the carboxyl carbon then breaks and CO2 is released, with the negative charge delocalised into the PLP pyridine ring (quinonoid intermediate). Protonation of C2 explains why C2 gains one H in the computed changes, and a second transaldimination releases putrescine and regenerates the Lys–PLP aldimine. PLP is not written in the reaction because it is regenerated.
WHY EC 4.1.1.17: the reaction removes a carboxyl group as CO2 by breaking a C–C bond (carboxy-lyase, EC 4.1.1), and L-ornithine → putrescine is exactly the ornithine decarboxylase reaction."""),
    ("""REACTION: acetyl-CoA + choline → acetylcholine (+ CoA, not listed in the record). acetyl-CoA donates its acyl group; CoA is released.
BOND CHANGES:
- new single bond O1 (OH of choline) – C2 (C of acetyl-CoA)
- broken single bond C2 (C of acetyl-CoA) – S (S leaves)
- O1 (OH of choline) loses 1 H
CHOSEN ENZYME: EC 2.3.1.6 choline O-acetyltransferase; reaction: acetyl-CoA + choline = CoA + O-acetylcholine
MECHANISM REFERENCE (class card: Acyl-CoA:alcohol O-acyltransferase): The acceptor hydroxyl group attacks the thioester carbonyl carbon of the acyl-CoA. A conserved active-site His acts as general base, deprotonating the hydroxyl. The tetrahedral oxyanion intermediate collapses, expelling the CoA thiolate and forming the ester bond. CoA is the leaving group.""",
     """MECHANISM: The hydroxyl oxygen O1 of choline, deprotonated by an active-site His acting as general base, attacks the thioester carbonyl carbon C2 of acetyl-CoA. The tetrahedral oxyanion intermediate collapses and expels the CoA thiolate, which matches the computed changes: a new O1–C2 bond, the C2–S bond broken with the CoA part leaving, and O1 losing its H. The product is the ester acetylcholine, and CoA is released.
WHY EC 2.3.1.6: an acyl group is transferred from acyl-CoA to an acceptor (acyltransferase, EC 2.3.1), and acetyl-CoA + choline = CoA + acetylcholine is exactly the choline O-acetyltransferase reaction."""),
    # the reference is a long M-CSA text for a related enzyme with another substrate: use its chemistry, not its details
    ("""REACTION: 4-hydroxyphenylacetate + NADH + O2 → 3,4-dihydroxyphenylacetate + NAD+ + H2O. NADH supplies the reducing equivalents (electrons) and becomes NAD+; O2 is the oxidant.
BOND CHANGES:
- new single bond C3 (CH of 4-hydroxyphenylacetate) – O (O of O2)
- C3 (CH of 4-hydroxyphenylacetate) loses 1 H
CHOSEN ENZYME: EC 1.14.14.9 4-hydroxyphenylacetate 3-monooxygenase; reaction: 4-hydroxyphenylacetate + FADH2 + O2 = 3,4-dihydroxyphenylacetate + FAD + H2O
MECHANISM REFERENCE (analogous enzyme: p-hydroxybenzoate hydroxylase (EC 1.14.13.2), an enzyme of the same sub-subclass): The reduced flavin reacts with O2 to form a C4a-hydroperoxyflavin, stabilised by a Pro backbone amide and a His. The phenolate of p-hydroxybenzoate, deprotonated through a proton relay of a Tyr, a Tyr and a His to the solvent, attacks the distal oxygen of the hydroperoxide in an electrophilic aromatic substitution. The dienone intermediate tautomerises to 3,4-dihydroxybenzoate, and the C4a-hydroxyflavin eliminates water. The flavin moves between an 'in' and an 'out' conformation during catalysis; an Arg binds the carboxylate of the substrate.""",
     """MECHANISM: The mechanism is assumed by analogy to p-hydroxybenzoate hydroxylase, a flavin monooxygenase acting on a different substrate. Reduced flavin (regenerated with electrons from NADH) reacts with O2 to give a flavin hydroperoxide, and the phenolate of 4-hydroxyphenylacetate attacks its distal oxygen, ortho to the hydroxyl group. This matches the computed changes: a new bond from C3 to an oxygen of O2 and the loss of the H on C3, which restores the aromatic ring as the catechol 3,4-dihydroxyphenylacetate. The other oxygen atom of O2 leaves as water.
WHY EC 1.14.14.9: O2 is split between the substrate and water with a reduced flavin as the electron donor (paired donors, one oxygen incorporated, EC 1.14.14), and 4-hydroxyphenylacetate → 3,4-dihydroxyphenylacetate is exactly the 4-hydroxyphenylacetate 3-monooxygenase reaction."""),
    # the record runs opposite to the reference: the answer follows the record, not the reference
    ("""REACTION: acetaldehyde + NADH → ethanol (+ NAD+, not listed in the record). NADH supplies a hydride and becomes NAD+.
BOND CHANGES:
- changed bond C2 (CH of acetaldehyde) – O3 (O of acetaldehyde): double → single
- C2 (CH of acetaldehyde) gains 1 H
- O3 (O of acetaldehyde) gains 1 H
CHOSEN ENZYME: EC 1.1.1.1 alcohol dehydrogenase; reaction: a primary alcohol + NAD+ = an aldehyde + NADH + H+
MECHANISM REFERENCE (class card: NAD(P)+-dependent alcohol dehydrogenase): Alcohol dehydrogenases transfer a hydride from the carbon bearing the hydroxyl group (the carbinol C-H) to C4 of the nicotinamide ring of NAD(P)+, giving the carbonyl product and NAD(P)H; the hydroxyl proton is removed by a general base at the same time. In short-chain dehydrogenases/reductases (SDR) the base is a Tyr; in medium-chain (MDR) enzymes a catalytic Zn2+ binds the alcohol oxygen and lowers its pKa. No covalent intermediate is formed.""",
     """MECHANISM: The record runs in the reduction direction, the reverse of the oxidation the reference describes, so the reference steps apply in reverse. The hydride on C4 of the NADH nicotinamide ring is transferred to C2, the carbonyl carbon of acetaldehyde, and the carbonyl oxygen O3 is protonated by the general acid (the protonated form of the base in the reference). This matches the computed changes: the C2–O3 double bond becomes single and C2 and O3 each gain one H, giving ethanol and NAD+.
WHY EC 1.1.1.1: the enzyme interconverts a CH–OH group and a carbonyl with NAD(H) (EC 1.1.1), and acetaldehyde + NADH = ethanol + NAD+ is the alcohol dehydrogenase reaction read in reverse."""),
]

TASK_B = ("Write two parts. MECHANISM: 3-5 sentences explaining THIS reaction exactly as written, left to right: the "
          "substrates and products and the bond changes listed above are the facts to explain. Name the atoms and groups "
          "that change and the role of each cofactor or cosubstrate. Use the mechanism reference as a guide only: if it "
          "describes the reverse direction, say so and apply its steps in reverse; if it describes a different kind of "
          "change than the bond changes show, say so and describe only what the bond changes show. Never give residue "
          "numbers; name a residue type only if the reference names it, otherwise describe its role (e.g. 'a general "
          "base'). Do not copy details of the reference that concern another substrate. WHY EC <number>: 1-2 sentences. Use only the information above; do not add cofactors, metals or "
          "steps that are not in it. If the reference is for an analogous enzyme, say the mechanism is assumed by analogy.")
AA = "Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val"


def case_block(r, cand):
    ref = cand.get("reference")
    ref_txt = (f"MECHANISM REFERENCE ({'M-CSA entry for this enzyme' if ref['kind'] == 'exact' else 'class card' if ref['kind'] == 'class' else 'analogous enzyme'}: "
               f"{ref['title']}): {ref['text']}") if ref else \
        "MECHANISM REFERENCE: none available. Describe only what the bond changes show; do not propose residues or cofactors."
    cav = ("\nDATA PROBLEMS (computed): " + ' '.join(r["caveats"]) +
           " Because of these, first say in one sentence that the record looks inconsistent, then explain only the part "
           "of the change that the mechanism reference accounts for; do not invent steps for the rest.") if r.get("caveats") else ""
    return (f"REACTION: {r['summary']}\nBOND CHANGES:\n" + '\n'.join(f"- {c}" for c in r["changes"]) +
            f"\nCHOSEN ENZYME: EC {cand['ec4']} {cand['name']}; reaction: {cand['reaction']}\n{ref_txt}{cav}")


def ec_prompt(r, order):
    lines = []
    for i, c in enumerate(order, 1):
        extra = " This exact reaction is listed for it in MetaNetX." if "known" in c else ""
        lines.append(f"{i}. EC {c['ec4']} {c['name']}. Reaction: {c['reaction']}.{extra}")
    return (f"REACTION: {r['summary']}\nBOND CHANGES:\n" + '\n'.join(f"- {c}" for c in r["changes"]) +
            "\n\nCandidate enzymes:\n" + '\n'.join(lines) +
            "\n\nWhich candidate enzyme catalyses this reaction? Compare the substrates, cofactors and bond changes "
            "with each candidate's reaction. Answer with the EC number only.")


ATOM = r"[A-Z][a-z]?\d+"
SEP = r"(?:\s*,\s*|\s*and\s+|\s*or\s+|\s*/\s*)+"     # ", and " is one separator
ATOM_RUN = rf"{ATOM}(?:{SEP}{ATOM})*"
GAIN_V = r"gains?|gaining|picks up|is protonated|accepts a proton|accepts a hydride|receives a proton"
LOSE_V = r"loses?|losing|is deprotonated|donates|gives up|releases a proton|releases a hydride"
PRE_GAIN = r"protonation of|protonates"              # these two take the atom after the verb
PRE_LOSE = r"deprotonation of|deprotonates"


def h_ledger(changes):
    """{atom: 'gains'|'loses'} as the atom mapping computed it, e.g. 'O46 (OH of X) loses 1 H'."""
    out = {}
    for c in changes:
        m = re.match(rf"\s*({ATOM})\b.*?\b(gains|loses)\s+\d+\s+H\b", c)
        if m:
            out[m.group(1)] = m.group(2)
    return out


H_WORD = re.compile(r"\b(?:H|hydrogens?|protons?|hydrides?)\b")
NOT_H = re.compile(r"\b(?:bonds?|charges?|electrons?|groups?|atoms?)\b")


def about_hydrogen(after):
    """True when a gain/lose verb is about hydrogen, not a bond, charge or group."""
    h, other = H_WORD.search(after), NOT_H.search(after)
    return bool(h) and (other is None or h.start() < other.start())


def h_contradictions(text, changes):
    """Atoms the text says gain H where the mapping says they lose it, or the reverse."""
    led = h_ledger(changes)
    if not led:
        return []
    issues = {}

    def flag(atoms, said):
        for a in atoms:
            if a in led and led[a] != said:
                issues[a] = f"says {a} {said} H, but the computed changes say it {led[a]} H"

    # read backwards from the verb: matching the atom run forwards backtracks catastrophically
    tail = re.compile(rf"({ATOM_RUN})\s*(?:each|both|then|also|respectively)?\s*$", re.I)
    for m in re.finditer(rf"\b({GAIN_V}|{LOSE_V})\b", text, re.I):
        verb = m.group(1)
        gains = re.fullmatch(GAIN_V, verb, re.I) is not None
        if gains == (re.fullmatch(LOSE_V, verb, re.I) is not None):
            continue                                   # both lists or neither: not an assertion
        if not about_hydrogen(text[m.end():m.end() + 40]):
            continue
        run = tail.search(text[max(0, m.start() - 80):m.start()])
        if run:
            flag(re.findall(ATOM, run.group(1)), "gains" if gains else "loses")
    for m in re.finditer(rf"\b({PRE_GAIN}|{PRE_LOSE})\s+({ATOM_RUN})", text, re.I):
        gains = re.fullmatch(PRE_GAIN, m.group(1), re.I) is not None
        flag(re.findall(ATOM, m.group(2)), "gains" if gains else "loses")
    return list(issues.values())


def imported_cofactors(text, r, cand):
    """Cofactors stated as fact that come only from a class/analogous reference, unhedged."""
    ref = cand.get("reference") or {}
    if not ref or ref.get("kind") == "exact":
        return []
    facts = ' '.join([r["summary"], ' '.join(r["changes"]), r["allowed_text"], cand["name"], cand["reaction"]])
    reftxt = (ref.get("text") or "") + " " + (ref.get("title") or "")
    issues = []
    for term, pat in (r.get("check_terms") or {}).items():
        if not (re.search(pat, text) and re.search(pat, reftxt)) or re.search(pat, facts):
            continue
        hedged = any(re.search(pat, s) and re.search(r"analog|analogy|reference|assumed|by comparison", s, re.I)
                     for s in re.split(r"(?<=[.;])\s+", text))
        if not hedged:
            issues.append(f"states {term} as this reaction's chemistry, but it appears only in the "
                          f"{ref.get('kind', 'non-exact')} reference")
    return issues


def check(text, r, cand):
    """Problems a reader could verify: cofactors/metals not supported by the facts or reference; foreign EC numbers."""
    ref = cand.get("reference") or {}
    allowed = ' '.join([r["summary"], ' '.join(r["changes"]), r["allowed_text"], cand["name"], cand["reaction"],
                        ref.get("text", ""), ref.get("title", "")])
    issues = [f"mentions {term}, which is not in the facts or the reference"
              for term, pat in r["check_terms"].items() if re.search(pat, text) and not re.search(pat, allowed)]
    for res in sorted(set(re.findall(rf"\b(?:{AA})[- ]?\d+[A-Z]?\b", text))):
        issues.append(f"gives the residue number {res}")
    if re.search(r"(?im)^\s*(step \d|revised:|check this explanation)", text):
        issues.append("contains the self-check instructions")
    ec3 = '.'.join(cand["ec4"].split('.')[:3])
    for ec in re.findall(r"\b\d+\.\d+\.\d+(?:\.\d+)?\b", text):
        if ec != cand["ec4"] and ec != ec3 and not cand["ec4"].startswith(ec + '.'):
            issues.append(f"names EC {ec}, which is not the chosen enzyme")
    if not re.search(r"MECHANISM:", text) or not re.search(r"WHY EC\s*\d", text):
        # the EC must actually be a number: the model sometimes copies the prompt's "<number>"
        # placeholder through, which a bare "WHY EC" test accepts
        issues.append("does not follow the MECHANISM / WHY EC <ec> format")
    issues += h_contradictions(text, r["changes"])
    issues += imported_cofactors(text, r, cand)
    return issues


class Chat:
    def __init__(self, model_id, load_in_4bit=False, cpu=False):
        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
        self.tok = AutoTokenizer.from_pretrained(model_id, token=token)
        # CPU (no GPU free): float32, since these Xeons have no native bf16
        kw = dict(dtype=torch.float32, device_map="cpu", token=token) if cpu else \
            dict(dtype=torch.bfloat16, device_map="auto", token=token)
        if load_in_4bit:      # e.g. Gemma-3-27B on a 24 GB GPU
            from transformers import BitsAndBytesConfig
            kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                           bnb_4bit_compute_dtype=torch.bfloat16)
        try:
            self.model = AutoModelForCausalLM.from_pretrained(model_id, **kw)
        except (ValueError, KeyError):           # Gemma 3 checkpoints are image-text-to-text
            from transformers import AutoModelForImageTextToText
            self.model = AutoModelForImageTextToText.from_pretrained(model_id, **kw)
        self.model.eval()

    def __call__(self, messages, max_new_tokens=400, temperature=0.0):
        enc = self.tok.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt",
                                           return_dict=True).to(self.model.device)
        gen = dict(max_new_tokens=max_new_tokens, do_sample=temperature > 0)
        if temperature > 0:
            gen.update(temperature=temperature, top_p=0.95)
        with torch.no_grad():
            out = self.model.generate(**enc, **gen)
        return self.tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def few_shot_turns():
    turns = []
    for case, answer in FEW_SHOT:
        turns += [{"role": "user", "content": case + "\n\n" + TASK_B}, {"role": "assistant", "content": answer}]
    return turns


def choose_ec(chat, r, n_votes, rng, margin=0.2):
    """(candidate or None, votes, raw answers, how): the ranking's top candidate when it leads by > margin, else the
    majority vote among the candidates within the margin; None (abstain) when no vote names one of them."""
    ranked = r["candidates"]
    if len(ranked) == 1 or ranked[0]["score"] - ranked[1]["score"] > margin:
        return ranked[0], Counter(), [], "similarity"
    cands = [c for c in ranked if ranked[0]["score"] - c["score"] <= margin]
    valid = {c["ec4"] for c in cands}
    votes, raw = Counter(), []
    for k in range(n_votes):
        order = cands[:] if k == 0 else rng.sample(cands, len(cands))
        ans = chat([{"role": "user", "content": ec_prompt(r, order)}], max_new_tokens=24)
        raw.append(ans)
        m = re.findall(r"\d+\.\d+\.\d+\.\d+", ans)
        pick = next((x for x in m if x in valid), None)
        if pick is None:     # answered with the list position
            pos = re.match(r"\s*(\d+)\b", ans)
            if pos and 1 <= int(pos.group(1)) <= len(order):
                pick = order[int(pos.group(1)) - 1]["ec4"]
        if pick:
            votes[pick] += 1
    if not votes:
        return None, votes, raw, "abstain"
    best = max(votes.items(), key=lambda kv: (kv[1], -[c["ec4"] for c in cands].index(kv[0])))[0]
    return next(c for c in cands if c["ec4"] == best), votes, raw, "vote"


def explain(chat, r, cand, max_retries=2):
    base = few_shot_turns()
    case = case_block(r, cand)
    log = []
    warn = ""
    best, best_issues = None, None
    for attempt in range(max_retries + 1):
        draft = chat(base + [{"role": "user", "content": case + "\n\n" + TASK_B + warn}], max_new_tokens=450)
        issues = check(draft, r, cand)
        log.append({"stage": f"draft{attempt}", "text": draft, "issues": issues})
        if best is None or len(issues) < len(best_issues):
            best, best_issues = draft, issues
        # self-check and rewrite
        critique = chat([{"role": "user", "content":
                          f"Check this explanation against the facts and the mechanism reference.\n\nFACTS AND REFERENCE:\n{case}\n\n"
                          f"EXPLANATION:\n{draft}\n\nStep 1: list every statement in the explanation that contradicts or is "
                          "not supported by the facts or the reference (write 'none' if all are supported). Step 2: after a "
                          "line 'REVISED:', write the corrected explanation in the same format (MECHANISM: ... WHY EC ...: ...)."}],
                        max_new_tokens=650)
        revised = critique.split("REVISED:", 1)[1].strip() if "REVISED:" in critique else ""
        # anything before the first MECHANISM: is commentary that leaked into the rewrite
        revised = revised[revised.find("MECHANISM:"):] if "MECHANISM:" in revised else revised
        if revised:
            r_issues = check(revised, r, cand)
            log.append({"stage": f"revised{attempt}", "critique": critique.split("REVISED:", 1)[0].strip(),
                        "text": revised, "issues": r_issues})
            if len(r_issues) < len(best_issues):      # a rewrite is kept only if it fixes something
                best, best_issues = revised, r_issues
        if not best_issues:
            break
        warn = ("\nIMPORTANT: a previous answer was rejected because it " + "; ".join(best_issues) +
                ". Do not repeat these errors.")
    return best, best_issues, log


def confidence(r, cand, votes, issues):
    n = sum(votes.values()) or 1
    agree = votes.get(cand["ec4"], 0) / n if votes else 1.0     # no vote: the ranking's top candidate led clearly
    ref_kind = (cand.get("reference") or {}).get("kind")
    pts = 0
    pts += 2 if "known" in cand else 0
    pts += 1 if agree >= 0.8 else 0
    pts += 1 if ref_kind in ("exact", "class") else 0
    pts -= len(r["caveats"]) + (1 if issues else 0)
    level = "high" if pts >= 3 else "medium" if pts >= 1 else "low"
    why = [f"{votes.get(cand['ec4'], 0)}/{n} votes for EC {cand['ec4']}" if votes else
           f"EC {cand['ec4']} leads the similarity ranking clearly",
           "the exact reaction is listed for this EC in MetaNetX" if "known" in cand else "no database entry with these exact participants",
           {"exact": "mechanism from the M-CSA entry for this enzyme", "class": "mechanism from a class reference",
            "analog": "mechanism by analogy to a related enzyme"}.get(ref_kind, "no mechanism reference")]
    if r["caveats"]:
        why.append(f"{len(r['caveats'])} data caveat(s)")
    if issues:
        why.append("the explanation still has unverified statements")
    return level, why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", default="chat/prompts/chat_inputs.json")
    ap.add_argument("--model_id", default="google/txgemma-9b-chat")
    ap.add_argument("--out_prefix", default="chat_out/explanations")
    ap.add_argument("--votes", type=int, default=5)
    ap.add_argument("--margin", type=float, default=0.2, help="ranking-score lead above which no vote is taken")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max_retries", type=int, default=2)
    ap.add_argument("--load_in_4bit", action="store_true")
    ap.add_argument("--cpu", action="store_true", help="run on CPU (float32)")
    args = ap.parse_args()
    Path(args.out_prefix).parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    torch.manual_seed(args.seed)

    if args.cpu:
        torch.set_num_threads(int(os.environ.get("SLURM_CPUS_PER_TASK", os.cpu_count())))
    chat = Chat(args.model_id, load_in_4bit=args.load_in_4bit, cpu=args.cpu)
    records = json.load(open(args.inputs))
    md = [f"# Gemma4EC explanations ({args.model_id.rstrip('/').split('/')[-1]})\n"]
    for r in records:
        for i, c in enumerate(r.get("candidates", []), 1):
            c["similarity_rank"] = i
        if r.get("skip_reason"):
            r.update(chosen_ec4=None, selection="skipped", votes={}, explanation="", final_text="", draft_text="",
                     n_votes=0, unresolved_issues=[], log=[], confidence="none", model_id=args.model_id)
            md += [f"## Reaction {r['rxn_id']}: not explained\n", f"`{r['rxn_smiles']}`\n", f"{r['skip_reason']}\n", "---\n"]
            print(f"rxn{r['rxn_id']:02d}  skipped: {r['skip_reason']}", flush=True)
            continue
        cand, votes, raw, how = choose_ec(chat, r, args.votes, rng, args.margin)
        if cand is None:
            text = ("No candidate enzyme fits this reaction (every vote rejected the candidates), so no mechanism is "
                    "proposed. The computed bond changes are listed above.")
            r.update(chosen_ec4=None, selection=how, votes=dict(votes), vote_answers=raw, explanation=text,
                     final_text=text, draft_text=text, draft_issues=[], n_votes=sum(votes.values()),
                     unresolved_issues=[], log=[], confidence="low", confidence_reasons=["abstained"],
                     model_id=args.model_id)
            md += [f"## Reaction {r['rxn_id']}: Gemma4EC predicts EC {r['predicted_ec']}\n", f"`{r['rxn_smiles']}`\n",
                   f"**What happens.** {r['summary']}\n", text + "\n", "---\n"]
            print(f"rxn{r['rxn_id']:02d}  abstained (votes {raw})", flush=True)
            continue
        text, issues, log = explain(chat, r, cand, args.max_retries)
        level, why = confidence(r, cand, votes, issues)
        # the first draft, before any self-check rewrite: the faithfulness metric is reported
        # before and after this step, so both texts have to survive into the JSON
        draft0 = next((e for e in log if e["stage"] == "draft0"), {})
        # candidates arrive sorted by similarity; record the rank explicitly so the evaluator
        # does not have to assume the order is meaningful
        for i, c in enumerate(r.get("candidates", []), 1):
            c["similarity_rank"] = i
        r.update(chosen_ec4=cand["ec4"], selection=how, votes=dict(votes), vote_answers=raw, explanation=text,
                 final_text=text, draft_text=draft0.get("text", ""), draft_issues=draft0.get("issues", []),
                 n_votes=sum(votes.values()),
                 unresolved_issues=issues, log=log, confidence=level, confidence_reasons=why, model_id=args.model_id)
        truth = (f"true {r['true_ec']}, " + ("correct" if r["predicted_ec"] == r["true_ec"] else "WRONG")
                 if r.get("true_ec") else "true EC not given")
        ref = cand.get("reference") or {}
        md += [f"## Reaction {r['rxn_id']}: Gemma4EC predicts EC {r['predicted_ec']} ({truth})\n",
               f"`{r['rxn_smiles']}`\n",
               f"**What happens.** {r['summary']}\n",
               "**Bond changes (atom mapping).**\n" + '\n'.join(f"- {c}" for c in r["changes"]) + "\n",
               f"**Enzyme.** EC {cand['ec4']} {cand['name']} ({votes.get(cand['ec4'], 0)}/{sum(votes.values())} votes; "
               f"candidates: {', '.join(c['ec4'] for c in r['candidates'])}).\n",
               text.replace("MECHANISM:", "**Mechanism.**").replace("WHY EC", "**Why EC") .replace(
                   f"**Why EC {cand['ec4']}:", f"**Why EC {cand['ec4']}.**") + "\n",
               f"*Mechanism source: {ref.get('source', 'none')}.*\n" if ref else "*No curated mechanism available.*\n",
               f"**Attention.** {r['attention'].removeprefix('Attention: ')}\n",
               "**Caveats.** " + (' '.join(r["caveats"]) if r["caveats"] else "none detected.") + "\n",
               f"**Confidence: {level}** ({'; '.join(why)}).\n",
               (f"*Unverified statements left: {'; '.join(issues)}.*\n" if issues else ""), "---\n"]
        print(f"rxn{r['rxn_id']:02d}  chose {cand['ec4']} ({how}) votes {dict(votes)}  issues {len(issues)}  conf {level}",
              flush=True)
        # save after every reaction so partial results can be read while the job runs
        done = [x for x in records if "explanation" in x]
        Path(args.out_prefix + ".json").write_text(json.dumps(done, indent=1, ensure_ascii=False))
        Path(args.out_prefix + ".md").write_text('\n'.join(md))

    print(f"Saved → {args.out_prefix}.json / .md")


if __name__ == "__main__":
    main()
