#!/usr/bin/env python3
"""Audit explanation text: invented facts, what the self-check revision repairs, hedging vs mechanism.

Usage: python chat/audit_explanations.py --run chat/eval/set/run --out results/chat_eval
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

# "by analogy to EC x" is how the model reaches for a mechanism it was not given. It is not an
# error — sometimes it is the honest answer — but a mechanism asserted for a neighbouring enzyme
# is a different claim from one derived from these bond changes, so it is counted separately.
HEDGE = re.compile(r"\b(by analogy|analogous|similar to|assumed|presumably|likely|appears to|"
                   r"may be|might be|probably|typical(?:ly)?)\b", re.I)


def facts_text(r):
    """Two senses of "supported", because they give very different numbers and mean different things.

    computed  the reaction itself: species, bond changes, the MetaNetX summary. A cofactor absent
              here is absent from the chemistry the model was asked to explain.
    shown     also the literature reference retrieved for the enzyme it chose. A cofactor that
              appears only here was not invented out of nothing, but it was imported from a
              neighbouring enzyme rather than read off this reaction.
    """
    computed = " ".join([r.get("summary", ""), " ".join(r.get("changes") or []), r.get("allowed_text", "")])
    # the reference of the CHOSEN candidate, not candidates[0]: the model departs from the
    # similarity top-1 on about a third of reactions, and then they are different enzymes
    chosen = r.get("chosen_ec4")
    cand = next((c for c in (r.get("candidates") or []) if c.get("ec4") == chosen), {})
    ref = cand.get("reference") or {}
    return computed, computed + " " + ref.get("text", "") + " " + ref.get("title", "")


def violations(text, chosen, facts, terms):
    """Foreign EC numbers and cofactors the facts never mention, as a list so they can be counted.

    Stricter than evaluate_chat.faithfulness, which allows any EC from the candidate list: naming a
    candidate the model did not choose is still a claim about an enzyme this reaction is not.
    """
    out = []
    ec3 = ".".join(chosen.split(".")[:3]) if chosen else ""
    for ec in re.findall(r"\b\d+\.\d+\.\d+(?:\.\d+)?\b", text or ""):
        if ec != chosen and ec != ec3 and not (chosen or "").startswith(ec + "."):
            out.append(("foreign_ec", ec))
    for term, pat in (terms or {}).items():
        if re.search(pat, text or "") and not re.search(pat, facts):
            out.append(("ungrounded_term", term))
    return out


def boot(x, n_boot=10000, seed=0):
    x = np.asarray([v for v in x if not pd.isna(v)], float)
    if not len(x):
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    d = rng.choice(x, (n_boot, len(x)), replace=True).mean(1)
    return x.mean(), *np.percentile(d, [2.5, 97.5])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="dir with explanations.json")
    ap.add_argument("--out", type=Path, default=Path("results/chat_eval"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    recs = json.loads((Path(args.run) / "explanations.json").read_text())
    rows, invented = [], Counter()
    for r in recs:
        chosen, terms = r.get("chosen_ec4") or "", r.get("check_terms") or {}
        computed, shown = facts_text(r)
        draft, final = r.get("draft_text") or "", r.get("final_text") or r.get("explanation") or ""
        vd = violations(draft, chosen, computed, terms)
        vf = violations(final, chosen, computed, terms)
        vf_shown = violations(final, chosen, shown, terms)
        invented.update(t for k, t in vf if k == "ungrounded_term")

        body = re.split(r"\*\*WHY EC", final)[0]      # the mechanism half, before the justification
        # does the mechanism actually discuss the molecules this reaction changes? the changes read
        # "C1 (CH of (Z)-but-2-enal) - C2 (OH of H2O): double -> single", so the species are the
        # parentheticals. Water and protons are excluded: naming them says nothing.
        species = {m.lower() for m in re.findall(r"of ([^)]+)\)", " ".join(r.get("changes") or []))
                   if len(m) > 2 and m.lower() not in ("h2o", "h+")}
        on_topic = (all(s in body.lower() for s in species) if species else np.nan)
        rows.append(dict(
            rxn_id=r.get("rxn_id"), chosen_ec4=chosen, confidence=r.get("confidence"),
            n_votes=r.get("n_votes"), n_words=len(final.split()),
            format_ok=bool(re.search(r"MECHANISM:", final) and re.search(r"WHY EC\s*\d", final)),
            foreign_ec=sum(k == "foreign_ec" for k, _ in vf),
            ungrounded_terms=sum(k == "ungrounded_term" for k, _ in vf),
            invented=";".join(t for k, t in vf if k == "ungrounded_term"),
            clean=not vf, clean_vs_shown=not vf_shown, hedged=bool(HEDGE.search(body)),
            on_topic=on_topic,
            # the self-check is sold as a repair step: did it move any of this?
            rewritten=draft.strip() != final.strip(),
            fixed=bool(vd) and not vf, introduced=bool(vf) and not vd,
        ))

    d = pd.DataFrame(rows)
    d.to_csv(args.out / "explanation_audit.csv", index=False)
    n = len(d)

    md = [f"# Explanation audit ({n} explanations)", "",
          "What the text claims, independent of whether the enzyme was right.", "",
          "| property | rate [95% CI] |", "|---|---|"]
    # every row is phrased so that more is better, and the three counted as failures are flipped
    # here rather than in the CSV, which keeps the raw columns as plain counts
    rates = []
    for label, col, flip in [("Follows the required format", "format_ok", False),
                             ("Supported by the computed facts", "clean", False),
                             ("Supported once the retrieved reference counts", "clean_vs_shown", False),
                             ("Cites only the enzyme it chose", "foreign_ec", True),
                             ("Every cofactor named is in the facts", "ungrounded_terms", True),
                             ("Mechanism discusses every species that changes", "on_topic", False),
                             ("States the mechanism directly, without analogy", "hedged", True)]:
        v = d[col].astype(float) if col == "on_topic" else d[col].astype(bool).astype(float)
        m, lo, hi = boot(1 - v if flip else v)
        md.append(f"| {label} | {m:.1%} [{lo:.1%}, {hi:.1%}] |")
        rates.append(dict(property=label, column=col, n=int(v.notna().sum()),
                          value=m, ci_lo=lo, ci_hi=hi))
    pd.DataFrame(rates).to_csv(args.out / "explanation_rates.csv", index=False)

    before = n - (d.fixed | (~d.clean)).sum()        # fully supported before the rewrite
    md += ["", "## Does the self-check repair anything?", "",
           f"- text rewritten: **{d.rewritten.sum()}/{n}**",
           f"- fully supported before: **{before}/{n}**, after: **{d.clean.sum()}/{n}**",
           f"- violations fixed: **{d.fixed.sum()}**, newly introduced: **{d.introduced.sum()}**", ""]

    if invented:
        md += ["## What gets invented", "", "| cofactor / metal | reactions |", "|---|---|"]
        md += [f"| {t} | {c} |" for t, c in invented.most_common()]

    md += ["", "## Length", "",
           f"- median {int(d.n_words.median())} words (min {d.n_words.min()}, max {d.n_words.max()})", ""]

    text = "\n".join(md)
    (args.out / "explanation_audit.md").write_text(text + "\n")
    print(text)
    print(f"\n-> {args.out}")


if __name__ == "__main__":
    main()
