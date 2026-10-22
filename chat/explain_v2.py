#!/usr/bin/env python3
"""
v2 mechanistic explanations with a Gemma chat model, grounded in computed facts and curated mechanisms.

Input: chat/prompts/v2_inputs.json from chat/prepare_v2.py. Per reaction, three kinds of model call:
  A. choose the EC number among 3-5 candidates (short answer); self-consistency: one call per shuffled candidate
     order, majority vote
  B. write MECHANISM + WHY EC for the chosen enzyme, applying the mechanism reference to this reaction; few-shot
     worked examples are given as earlier chat turns
  C. self-check against the facts and rewrite; programmatic checks (cofactors not supported by the facts or the
     reference, foreign EC numbers) decide which version is kept, and B is redone with explicit warnings if needed
The summary, caveats, attention and confidence are written by code (prepare_v2.py), not by the model.

Usage:
    python chat/explain_v2.py --model_id google/txgemma-9b-chat --out_prefix chat/prompts/v2_txgemma9b
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
]

TASK_B = ("Write two parts. MECHANISM: 3-5 sentences applying the mechanism reference to THIS reaction: name the atoms and "
          "groups that change, the role of each cofactor or cosubstrate, and catalytic residues only if the reference "
          "gives them. WHY EC <number>: 1-2 sentences. Use only the information above; do not add cofactors, metals or "
          "steps that are not in it. If the reference is for an analogous enzyme, say the mechanism is assumed by analogy.")


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


def check(text, r, cand):
    """Problems a reader could verify: cofactors/metals not supported by the facts or reference; foreign EC numbers."""
    ref = cand.get("reference") or {}
    allowed = ' '.join([r["summary"], ' '.join(r["changes"]), r["allowed_text"], cand["name"], cand["reaction"],
                        ref.get("text", ""), ref.get("title", "")])
    issues = [f"mentions {term}, which is not in the facts or the reference"
              for term, pat in r["check_terms"].items() if re.search(pat, text) and not re.search(pat, allowed)]
    ec3 = '.'.join(cand["ec4"].split('.')[:3])
    for ec in re.findall(r"\b\d+\.\d+\.\d+(?:\.\d+)?\b", text):
        if ec != cand["ec4"] and ec != ec3 and not cand["ec4"].startswith(ec + '.'):
            issues.append(f"names EC {ec}, which is not the chosen enzyme")
    if not re.search(r"MECHANISM:", text) or not re.search(r"WHY EC", text):
        issues.append("does not follow the MECHANISM / WHY EC format")
    return issues


class Chat:
    def __init__(self, model_id, adapter=None, load_in_4bit=False, cpu=False):
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
        if adapter:
            from peft import PeftModel
            self.model = PeftModel.from_pretrained(self.model, adapter)
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


def choose_ec(chat, r, n_votes, rng):
    cands = r["candidates"]
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
        return cands[0], votes, raw
    best = max(votes.items(), key=lambda kv: (kv[1], -[c["ec4"] for c in cands].index(kv[0])))[0]
    return next(c for c in cands if c["ec4"] == best), votes, raw


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
        if revised:
            r_issues = check(revised, r, cand)
            log.append({"stage": f"revised{attempt}", "critique": critique.split("REVISED:", 1)[0].strip(),
                        "text": revised, "issues": r_issues})
            if len(r_issues) < len(best_issues) or (len(r_issues) == len(best_issues) and len(revised) > 0.5 * len(best)):
                best, best_issues = revised, r_issues
        if not best_issues:
            break
        warn = ("\nIMPORTANT: a previous answer was rejected because it " + "; ".join(best_issues) +
                ". Do not repeat these errors.")
    return best, best_issues, log


def confidence(r, cand, votes, issues):
    n = sum(votes.values()) or 1
    agree = votes.get(cand["ec4"], 0) / n
    ref_kind = (cand.get("reference") or {}).get("kind")
    pts = 0
    pts += 2 if "known" in cand else 0
    pts += 1 if agree >= 0.8 else 0
    pts += 1 if ref_kind in ("exact", "class") else 0
    pts -= len(r["caveats"]) + (1 if issues else 0)
    level = "high" if pts >= 3 else "medium" if pts >= 1 else "low"
    why = [f"{votes.get(cand['ec4'], 0)}/{n} votes for EC {cand['ec4']}",
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
    ap.add_argument("--inputs", default="chat/prompts/v2_inputs.json")
    ap.add_argument("--model_id", default="google/txgemma-9b-chat")
    ap.add_argument("--out_prefix", default="chat/prompts/v2_txgemma9b")
    ap.add_argument("--votes", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max_retries", type=int, default=2)
    ap.add_argument("--adapter", default=None, help="LoRA adapter from chat/finetune_explainer.py")
    ap.add_argument("--load_in_4bit", action="store_true")
    ap.add_argument("--cpu", action="store_true", help="run on CPU (float32)")
    args = ap.parse_args()
    rng = random.Random(args.seed)
    torch.manual_seed(args.seed)

    if args.cpu:
        torch.set_num_threads(int(os.environ.get("SLURM_CPUS_PER_TASK", os.cpu_count())))
    chat = Chat(args.model_id, args.adapter, args.load_in_4bit, args.cpu)
    records = json.load(open(args.inputs))
    md = [f"# Gemma4EC explanations, v2 ({args.model_id.rstrip('/').split('/')[-1]}"
          f"{' + ' + args.adapter if args.adapter else ''})\n"]
    for r in records:
        cand, votes, raw = choose_ec(chat, r, args.votes, rng)
        text, issues, log = explain(chat, r, cand, args.max_retries)
        level, why = confidence(r, cand, votes, issues)
        r.update(chosen_ec4=cand["ec4"], votes=dict(votes), vote_answers=raw, explanation=text,
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
        print(f"rxn{r['rxn_id']:02d}  chose {cand['ec4']} votes {dict(votes)}  issues {len(issues)}  conf {level}", flush=True)
        # save after every reaction so partial results can be read while the job runs
        done = [x for x in records if "explanation" in x]
        Path(args.out_prefix + ".json").write_text(json.dumps(done, indent=1, ensure_ascii=False))
        Path(args.out_prefix + ".md").write_text('\n'.join(md))

    print(f"Saved → {args.out_prefix}.json / .md")


if __name__ == "__main__":
    main()
