#!/usr/bin/env python3
"""Score the chat explanations (<run>/explanations.json) against chat/eval/set/reactions.csv.

Reports, with 95% bootstrap CIs over reactions: candidate recall (ceiling), enzyme top-1 vs similarity
top-1 and random, accuracy by how the enzyme was chosen, faithfulness (ECs outside the candidates,
cofactors absent from the facts; draft vs final), and attention on reaction-centre atoms vs chance.
Skipped records and abstentions count as wrong in "all", and are excluded from "explained".

Writes one CSV per metric plus summary.md.
Usage: python chat/evaluate_chat.py --run chat/eval/set/run --truth chat/eval/set/reactions.csv --out results/chat_eval
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

RNG = np.random.default_rng(0)
EC_NAMES = {"1": "Oxidoreductases", "2": "Transferases", "3": "Hydrolases", "4": "Lyases",
            "5": "Isomerases", "6": "Ligases", "7": "Translocases"}


def boot_ci(x, n_boot=10000, stat=np.mean):
    """Percentile bootstrap over reactions. Returns (point, lo, hi)."""
    x = np.asarray([v for v in x if v is not None and not (isinstance(v, float) and np.isnan(v))], float)
    if len(x) == 0:
        return np.nan, np.nan, np.nan
    if len(x) == 1:
        return float(stat(x)), float(stat(x)), float(stat(x))
    idx = RNG.integers(0, len(x), size=(n_boot, len(x)))
    d = stat(x[idx], axis=1)
    return float(stat(x)), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def row(name, x, **extra):
    p, lo, hi = boot_ci(x)
    return dict(metric=name, n=len(x), value=p, ci_lo=lo, ci_hi=hi, **extra)


def load(run, truth):
    recs = json.loads((Path(run) / "explanations.json").read_text())
    # explanations.json carries the attention as the sentence shown to the model; the per-atom
    # numbers stay in reaction_facts.json, so take them from there and join on rxn_id
    facts_path = Path(run) / "reaction_facts.json"
    att_by_id = {}
    if facts_path.exists():
        att_by_id = {f.get("rxn_id"): (f.get("attention_atoms") or {})
                     for f in json.loads(facts_path.read_text())}
    t = pd.read_csv(truth)
    by_smiles = t.set_index("rxn_smiles")
    out = []
    for r in recs:
        smi = r.get("rxn_smiles")
        if smi not in by_smiles.index:
            continue
        g = by_smiles.loc[smi]
        if isinstance(g, pd.DataFrame):
            g = g.iloc[0]
        cands = r.get("candidates", []) or []
        votes = r.get("votes", {}) or {}
        n_votes = sum(votes.values()) or 1
        chosen = r.get("chosen_ec4")
        out.append(dict(
            rxn_id=r.get("rxn_id"), rxn_smiles=smi,
            true_ec4=str(g["true_ec4"]), ec_class=str(g["ec_class"]),
            gemma_correct_ec3=bool(g["gemma_correct_ec3"]),
            cand_ec4=[c["ec4"] for c in cands],
            sim_top1=cands[0]["ec4"] if cands else None,
            chosen=chosen, selection=r.get("selection", "vote"),
            agree=votes.get(chosen, 0), n_votes=n_votes,
            # runs made before draft_text was added still carry the first draft in the log
            draft_text=(r.get("draft_text")
                        or next((e["text"] for e in (r.get("log") or []) if e.get("stage") == "draft0"), "")),
            final_text=r.get("final_text", r.get("explanation", "")) or "",
            facts_text=" ".join([r.get("summary", "") or "", " ".join(r.get("changes", []) or []),
                                 r.get("allowed_text", "") or ""]),
            check_terms=r.get("check_terms", {}) or {},
            attention=att_by_id.get(r.get("rxn_id")) or {},
        ))
    return pd.DataFrame(out)


def faithfulness(text, cand_ec4, facts, terms):
    """A reader-checkable violation: an EC outside the candidate list, or a term the facts never mention."""
    if not text:
        return np.nan
    allowed_ec = set(cand_ec4) | {".".join(e.split(".")[:3]) for e in cand_ec4}
    for ec in re.findall(r"\b\d+\.\d+\.\d+(?:\.\d+)?\b", text):
        if ec not in allowed_ec and not any(c.startswith(ec + ".") for c in cand_ec4):
            return 1.0
    for term, pat in terms.items():
        if re.search(pat, text) and not re.search(pat, facts):
            return 1.0
    return 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="dir with explanations.json")
    ap.add_argument("--truth", required=True, help="CSV from chat/eval/make_eval_set.py")
    ap.add_argument("--out", type=Path, default=Path("results/chat_eval"))
    ap.add_argument("--n_boot", type=int, default=10000)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    d = load(args.run, args.truth)
    if d.empty:
        raise SystemExit("no explanations matched the ground-truth CSV")
    print(f"{len(d)} explanations matched to ground truth")

    # -- 1 candidate recall ------------------------------------------------------
    d["recall"] = [float(t in c) for t, c in zip(d.true_ec4, d.cand_ec4)]

    # -- 2 top-1, chat vs similarity vs random, on the same candidate lists -------
    d["acc_chat"] = [float(ch == t) for ch, t in zip(d.chosen, d.true_ec4)]
    d["acc_sim"] = [float(s == t) for s, t in zip(d.sim_top1, d.true_ec4)]
    # random is scored as its expectation (1/len) rather than one draw: same mean, no sampling noise
    d["acc_rand"] = [(1.0 / len(c)) if c else np.nan for c in d.cand_ec4]

    acc_rows = [row("candidate_recall", d.recall, method="ceiling"),
                row("top1", d.acc_chat, method="TxGemma-Chat"),
                row("top1", d.acc_sim, method="Similarity top-1"),
                row("top1", d.acc_rand, method="Random")]
    ex = d[d.chosen.notna()]
    if len(ex) < len(d):
        acc_rows += [row("top1_explained", ex.acc_chat, method="TxGemma-Chat (explained only)"),
                     row("top1_explained", ex.acc_sim, method="Similarity top-1 (same records)")]
    pd.DataFrame(acc_rows).to_csv(args.out / "accuracy_overall.csv", index=False)

    per = []
    for cls, g in d.groupby("ec_class"):
        for nm, col in [("TxGemma-Chat", "acc_chat"), ("Similarity top-1", "acc_sim"), ("Random", "acc_rand")]:
            per.append(row("top1", g[col], method=nm, ec_class=cls, ec_name=EC_NAMES.get(cls, cls)))
        per.append(row("candidate_recall", g.recall, method="ceiling", ec_class=cls,
                       ec_name=EC_NAMES.get(cls, cls)))
    pd.DataFrame(per).to_csv(args.out / "accuracy_per_class.csv", index=False)

    # -- 3 calibration by vote agreement ----------------------------------------
    def bucket(sel, a, n):
        if sel == "similarity":
            return "ranking lead (no vote)"
        if sel in ("abstain", "skipped"):
            return None
        return "5/5" if a >= n else ("4/5" if a == n - 1 else "<=3/5")
    d["agree_bucket"] = [bucket(s_, a, n) for s_, a, n in zip(d.selection, d.agree, d.n_votes)]
    cal = [row("top1", g.acc_chat, agreement=b) for b, g in d.dropna(subset=["agree_bucket"]).groupby("agree_bucket")]
    pd.DataFrame(cal).to_csv(args.out / "calibration.csv", index=False)

    # -- 4 faithfulness, before and after the self-check -------------------------
    for stage, col in [("draft", "draft_text"), ("final", "final_text")]:
        d[f"halluc_{stage}"] = [faithfulness(t, c, f, k) if ch else np.nan for t, c, f, k, ch
                                in zip(d[col], d.cand_ec4, d.facts_text, d.check_terms, d.chosen)]
    faith = [row("hallucination_rate", d.halluc_draft, stage="before self-check"),
             row("hallucination_rate", d.halluc_final, stage="after self-check")]
    pd.DataFrame(faith).to_csv(args.out / "faithfulness.csv", index=False)

    # -- 5 attention on reaction-centre atoms vs chance --------------------------
    att = d[d.attention.map(bool)].copy()
    att["centre_share"] = [a.get("share", {}).get("reaction-centre atoms", np.nan) for a in att.attention]
    att["chance"] = [a.get("centre_atom_fraction", np.nan) for a in att.attention]
    att = att.dropna(subset=["centre_share", "chance"])
    pd.DataFrame(dict(rxn_id=att.rxn_id, ec_class=att.ec_class,
                      centre_share=att.centre_share, chance=att.chance,
                      enrichment=att.centre_share - att.chance)).to_csv(
        args.out / "attention.csv", index=False)
    if len(att) >= 2:
        stat, pval = wilcoxon(att.centre_share, att.chance)
    else:
        stat, pval = np.nan, np.nan

    # -- summary -----------------------------------------------------------------
    def fmt(r):
        return f"{r['value']:.1%} [{r['ci_lo']:.1%}, {r['ci_hi']:.1%}]"
    md = [f"# Chat evaluation ({len(d)} reactions)", "",
          "Outcomes: " + ", ".join(f"{k} {v}" for k, v in d.selection.value_counts().items()), "",
          "## Enzyme selection (EC4, exact)", "",
          "| method | top-1 accuracy [95% CI] |", "|---|---|"]
    for r in acc_rows:
        md.append(f"| {r['method'] if r['metric'] != 'candidate_recall' else 'Candidate recall (ceiling)'} | {fmt(r)} |")
    md += ["", "## Calibration by vote agreement", "", "| agreement | n | accuracy [95% CI] |", "|---|---|---|"]
    for r in sorted(cal, key=lambda x: x["agreement"]):
        md.append(f"| {r['agreement']} | {r['n']} | {fmt(r)} |")
    md += ["", "## Faithfulness", "", "| stage | hallucination rate [95% CI] |", "|---|---|"]
    for r in faith:
        md.append(f"| {r['stage']} | {fmt(r)} |")
    md += ["", "## Attention on reaction-centre atoms", "",
           f"- mean share on centre atoms: {att.centre_share.mean():.1%}" if len(att) else "- no attention data",
           f"- chance level (centre atoms / all atoms): {att.chance.mean():.1%}" if len(att) else "",
           f"- paired Wilcoxon: W = {stat:.0f}, p = {pval:.2e} (n = {len(att)})" if len(att) >= 2 else ""]
    (args.out / "summary.md").write_text("\n".join(md) + "\n")

    d.drop(columns=["check_terms", "attention", "draft_text", "final_text", "facts_text"]).to_csv(
        args.out / "per_reaction.csv", index=False)
    print("\n".join(md))
    print(f"\n-> {args.out}")


if __name__ == "__main__":
    main()
