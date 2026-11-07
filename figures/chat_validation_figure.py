"""
chat_validation_figure.py - the chat evaluation as one figure.

Three blocks, each with its own n: coverage over all records, enzyme selection and text quality
over the explanations only. Candidate recall is computed on the explained records so it really
bounds the rows beneath it. One hue; rater-scored rows are a lighter step plus a dagger, since a
second hue fails CVD simulation. No caption on the plot.

Usage (gemma4ec env):  python figures/chat_validation_figure.py
"""
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / os.environ.get("RUN", "chat/eval/set/run")
TRUTH = ROOT / os.environ.get("TRUTH", "chat/eval/set/reactions.csv")
RES = ROOT / os.environ.get("RES_DIR", "results/chat_eval")
RATING = ROOT / os.environ.get("RATING_DIR", "chat/eval/ratings")
OUT = ROOT / "figures" / "chat"
OUT.mkdir(parents=True, exist_ok=True)

INK, GREY, RULE = "#1E1E1E", "#6B6B6B", "#DCDCDC"
SLATE, PLUM, MOSS = "#2B6490", "#92485F", "#6F9B4A"
CLAY, PERIWINKLE, AMBER = "#C47244", "#9DA8DE", "#D9B255"
TEAL, COCOA, NAVY, SAGE = "#4E9A97", "#5C4033", "#1F3A5F", "#AFC09A"
CHANCE = "#C9C9C9"   # the random floor reads as a reference, not a competing method
# one colour per row, no repeats, ordered so every adjacent pair stays >= 10 OKLab dE apart
# under simulated deuteranopia and protanopia
plt.rcParams.update({"font.family": ["Liberation Sans", "DejaVu Sans"]})


def boot(x, n_boot=10000, seed=0):
    x = np.asarray([v for v in x if not pd.isna(v)], float)
    rng = np.random.default_rng(seed)
    b = rng.choice(x, (n_boot, len(x)), replace=True).mean(1)
    return x.mean(), *np.percentile(b, [2.5, 97.5])


recs = json.loads((RUN / "explanations.json").read_text())
audit = pd.read_csv(RES / "explanation_audit.csv")
acc = pd.read_csv(RES / "accuracy_overall.csv")
truth = pd.read_csv(TRUTH).set_index("rxn_smiles")
ratings = {f.stem.removeprefix("ratings_"): pd.read_csv(f).set_index("item_id")
           for f in sorted(RATING.glob("ratings_*.csv"))}

n_all = len(recs)
explained = [r for r in recs if r.get("chosen_ec4")]
n_ex = len(explained)
n_ex_all = n_ex
ex = audit[audit.rxn_id.isin({r["rxn_id"] for r in explained})]
# complete cases only: the reactions for which every row below is defined, so the
# figure carries one n instead of three
ex = ex[ex.on_topic.notna()]
keep = set(ex.rxn_id)
explained = [r for r in explained if r["rxn_id"] in keep]
n_cc = len(ex)

# recall on the explained records only
rec_ex = []
for r in explained:
    g = truth.loc[r["rxn_smiles"]]
    g = g.iloc[0] if isinstance(g, pd.DataFrame) else g
    rec_ex.append(float(str(g["true_ec4"]) in [c["ec4"] for c in (r.get("candidates") or [])]))


def sel(which):
    """Selection, similarity top-1, or the chance floor, on the complete-case subset.

    "random" is scored as its expectation, 1/len(candidates), rather than one draw: same mean,
    no sampling noise."""
    out = []
    for r in explained:
        g = truth.loc[r["rxn_smiles"]]
        g = g.iloc[0] if isinstance(g, pd.DataFrame) else g
        c = [x["ec4"] for x in (r.get("candidates") or [])]
        if which == "random":
            out.append(1.0 / len(c) if c else np.nan)
        else:
            got = r["chosen_ec4"] if which == "chat" else (c[0] if c else None)
            out.append(float(got == str(g["true_ec4"])))
    return boot(np.asarray([v for v in out if not pd.isna(v)], float))


def rated(col, full=2):
    per = pd.concat([d[col].eq(full).astype(float) for d in ratings.values()], axis=1).mean(axis=1)
    key = pd.read_csv(RATING / "KEY.csv").set_index("item_id").rxn_id
    return boot(per[[i for i in per.index if key.get(i) in keep]].to_numpy())


# (label, value, lo, hi, colour, n)
ROWS = [
    ("Enzyme Candidate",                *boot(rec_ex), AMBER, None),
    ("Enzyme Selection",                *sel("chat"), NAVY, None),
    ("Similarity Baseline",             *sel("sim"), TEAL, None),
    ("Enzyme Plausibility",              *rated("enzyme_plausible"), SLATE, None),
    ("Supported by Reaction",           *boot(ex.clean), MOSS, None),
    ("Supported by Reaction or Reference", *boot(ex.clean_vs_shown), PERIWINKLE, None),
    ("Cofactors",                       *boot(ex.ungrounded_terms.eq(0)), CLAY, None),
    ("Enzyme Mechanism",                *boot(ex.foreign_ec.eq(0)), PLUM, None),
    ("Reaction Mechanism",              *boot(ex.on_topic), SAGE, None),
    ("Output Format",                   *boot(ex.format_ok.astype(bool)), COCOA, None),
]

fig, ax = plt.subplots(figsize=(8.6, 0.42 * len(ROWS) + 1.0), dpi=300)

yticks, ylabels = [], []
for y, (label, val, lo, hi, colour, nn) in enumerate(reversed(ROWS)):
    ax.barh(y, val, height=0.60, color=colour, zorder=3)
    if not np.isnan(lo):
        ax.plot([lo, hi], [y, y], color=INK, lw=1.0, zorder=4)
        for e in (lo, hi):
            ax.plot([e, e], [y - .11, y + .11], color=INK, lw=1.0, zorder=4)
    ax.text(1.035, y, f"{val:.0%}", va="center", ha="left", fontsize=9.8,
            fontweight="bold", color=INK, clip_on=False)
    yticks.append(y); ylabels.append(label)
y = len(ROWS)

ax.set_yticks(yticks); ax.set_yticklabels(ylabels, fontsize=9.4, color=INK)
ax.tick_params(axis="y", length=0, pad=6)
ax.set_ylim(-0.62, y - 0.55)
ax.set_xlim(0, 1.02)   # a 100% bar would otherwise sit flush against the frame and read as clipped
ax.set_xticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"], fontsize=8.8, color=GREY)
ax.set_xlabel(f"Share of reactions  (n = {n_cc})", fontsize=9.2, color=INK)
ax.xaxis.grid(True, color=RULE, lw=0.6, zorder=0)
ax.set_axisbelow(True)
for sp in ("top", "right", "left"):
    ax.spines[sp].set_visible(False)
ax.spines["bottom"].set_color(RULE)

fig.savefig(OUT / "fig_chat_validation.png", bbox_inches="tight", facecolor="white")
print(f"complete cases: {n_cc} of {n_ex_all} explained, {n_all} submitted")
print(f"Saved: {OUT / 'fig_chat_validation.png'}")
