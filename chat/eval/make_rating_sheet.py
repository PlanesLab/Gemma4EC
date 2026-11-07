#!/usr/bin/env python3
"""Build a blind rating sheet for the chat explanations (human raters or LLM judges, chat/eval/llm_rate.py).

Raters do not see whether Gemma4EC was right or the original order; the true EC is shown only with --with_truth.
Skipped records and abstentions have no mechanism and are not rated.

Writes <out>/sheet.md (items), ratings.csv (form), README.md (rubric) and KEY.csv (item -> reaction; keep back).
Usage: python chat/eval/make_rating_sheet.py chat/eval/set/run/explanations.json --out chat/eval/ratings \
           --with_truth --truth_csv chat/eval/set/reactions.csv
"""

import argparse
import json
import random
import re
from pathlib import Path

import pandas as pd

RUBRIC = {
    "mechanism_correct": "Is the mechanism correct for the reaction as recorded (the SMILES, left to right)? "
                         "(2 = correct; 1 = partly correct or too vague to be wrong; 0 = incorrect: wrong bond changes, "
                         "wrong direction, or a mechanism of a different kind of reaction). Anchor: a dehydrogenase text that "
                         "transfers the hydride to the wrong carbon is 0; one that names no residues but gets the hydride "
                         "transfer right is 2.",
    "enzyme_plausible": "Is the proposed enzyme right for this reaction? If the true EC is shown, judge against it. "
                        "(2 = same EC4 as the true one, or the reaction is clearly that enzyme's; 1 = right sub-subclass, "
                        "different enzyme; 0 = wrong kind of enzyme)",
    "contradicts_reaction": "Does the text contradict the reaction as recorded or basic chemistry? (0 = no; 1 = a minor slip, "
                            "e.g. a miscounted H; 2 = a substantive error: an invented participant or co-product, the wrong "
                            "atoms or bonds, the wrong direction). Details you cannot check are NOT counted here.",
    "unverifiable_detail": "Does the text add specific details found neither in the reaction nor in the mechanism reference "
                           "shown (residue numbers, metals, named intermediates)? (0 = none; 1 = one or two; 2 = many, or "
                           "details copied from a different enzyme or substrate in the reference)",
    "useful": "Would this help a biochemist understand the prediction? (2 = yes, 1 = somewhat, 0 = no)",
}


def block(r, with_truth=False):
    """Rater-facing text for one explanation."""
    txt = r.get("explanation", "")
    txt = re.sub(r"\bMECHANISM:\s*", "**Mechanism.** ", txt)
    txt = re.sub(r"\bWHY EC\s*([\d.]+)\s*:", r"**Why EC \1.**", txt)
    cand = next((c for c in r.get("candidates", []) if c["ec4"] == r.get("chosen_ec4")), {})
    ref = cand.get("reference") or {}
    parts = [f"**Reaction as recorded.** `{r['rxn_smiles']}`\n"]
    if r.get("completion"):
        parts.append(f"(The record omits some participants; the pipeline added "
                     f"{', '.join(r['completion']['added_reactants'] + r['completion']['added_products'])} "
                     f"from MetaNetX {r['completion']['mnx']}.)\n")
    parts.append("**Inputs the model was given** (computed by the pipeline; they may contain errors, judge them "
                 f"too).\n\n*Summary:* {r.get('summary', '')}\n")
    if r.get("changes"):
        parts.append("*Bond changes:*\n" + "\n".join(f"- {c}" for c in r["changes"]) + "\n")
    parts.append(f"*Mechanism reference given to the model* ({ref.get('kind', 'none')}): {ref.get('text', 'none')}\n")
    parts.append(f"**Enzyme proposed.** EC {r.get('chosen_ec4')} {cand.get('name', '')}\n")
    if with_truth:
        parts.append(f"**True EC (from the database).** {r.get('true_ec4') or r.get('true_ec')}\n")
    parts.append("**Explanation.**\n\n" + txt + "\n")
    if r.get("caveats"):
        parts.append("**Caveats.** " + " ".join(r["caveats"]) + "\n")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", help="explanations.json")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sample", type=int, default=0, help="rate a subset, stratified by EC class and enzyme correctness")
    ap.add_argument("--with_truth", action="store_true", help="show the true EC (for LLM judges)")
    ap.add_argument("--truth_csv", type=Path, help="reactions.csv with rxn_id, true_ec4")
    args = ap.parse_args()
    rng = random.Random(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)

    recs = [r for r in json.loads(Path(args.run).read_text()) if r.get("chosen_ec4")]
    if args.truth_csv:
        t4 = dict(pd.read_csv(args.truth_csv, dtype=str)[["rxn_id", "true_ec4"]].values)
        for r in recs:
            r["true_ec4"] = t4.get(str(r.get("rxn_id")))
    if args.sample:
        k = pd.DataFrame({"i": range(len(recs)),
                          "cls": [str(r.get("predicted_ec", "?")).split(".")[0] for r in recs],
                          "ok": [r.get("chosen_ec4") == r.get("true_ec4") for r in recs]})
        take = (k.groupby(["cls", "ok"], group_keys=False)
                 .apply(lambda g: g.sample(max(1, round(args.sample * len(g) / len(k))), random_state=args.seed)))
        if len(take) > args.sample:
            take = take.sample(args.sample, random_state=args.seed)
        recs = [recs[j] for j in sorted(take.i)]

    rng.shuffle(recs)
    md = ["# Rating sheet\n", "Read `README.md` first. Record your scores in `ratings.csv`.\n"]
    key, form = [], []
    for i, r in enumerate(recs, 1):
        iid = f"I{i:03d}"
        md += [f"\n---\n\n## {iid}\n", block(r, args.with_truth)]
        key.append(dict(item_id=iid, rxn_id=r.get("rxn_id"), true_ec=r.get("true_ec"),
                        proposed_ec=r.get("chosen_ec4"), gemma_pred=r.get("predicted_ec"),
                        gemma_correct=r.get("predicted_ec") == r.get("true_ec")))
        form.append(dict(item_id=iid, **{k: "" for k in RUBRIC}, notes=""))

    (args.out / "sheet.md").write_text("\n".join(md))
    pd.DataFrame(form).to_csv(args.out / "ratings.csv", index=False)
    pd.DataFrame(key).to_csv(args.out / "KEY.csv", index=False)
    readme = ["# Instructions for raters\n",
              f"There are **{len(form)} items** in `sheet.md`. Please score every one in `ratings.csv`.\n",
              ("Each item shows the true EC number from the database. Judge each item on the chemistry in front of you.\n"
               if args.with_truth else
               "You are not told the true EC number or whether the model's prediction was right. Judge each item on "
               "the chemistry in front of you.\n"), "## Scale\n"]
    readme += [f"- **{k}** — {v}\n" for k, v in RUBRIC.items()]
    readme.append("\n`notes`: anything wrong that the scores do not capture.\n")
    (args.out / "README.md").write_text("\n".join(readme))
    print(f"{len(form)} items -> {args.out}  (KEY.csv: keep back)")


if __name__ == "__main__":
    main()
