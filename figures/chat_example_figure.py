#!/usr/bin/env python3
"""
Figure: one worked example of the Gemma4EC chat pipeline (default: reaction 9, aryl-alcohol oxidase).

Left: (A) the reaction with the atom-mapped reaction centre highlighted; (B) Gemma4EC attention projected onto atoms.
Right: the interaction - input, Gemma4EC prediction, computed facts, TxGemma-9B-Chat explanation, confidence.
Text is taken verbatim from the pipeline outputs (chat/prompts/v2_txgemma9b.json); also written to <out>.md.

Usage (gemma4ec env):
    python figures/chat_example_figure.py [--rxn 9] [--out figures/chat/chat_example_rxn09]
"""

import argparse
import io
import json
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image
from rdkit import Chem
from rdkit.Chem.Draw import rdMolDraw2D

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "chat"))
import reaction_facts as rf  # noqa: E402

PURPLE, LAVENDER, INK, GREY, PAPER = "#654477", "#A58CE0", "#2B2B2B", "#6B6B6B", "#F6F3FA"
plt.rcParams.update({"font.family": "Liberation Sans", "font.size": 11})
ATT_CMAP = LinearSegmentedColormap.from_list("att", ["#FFFFFF", LAVENDER, PURPLE])


def draw_mol(smi, colors, radii=None, bonds=None, size=(620, 440)):
    m = Chem.MolFromSmiles(smi)
    d = rdMolDraw2D.MolDraw2DCairo(*size)
    o = d.drawOptions()
    o.bondLineWidth = 2
    o.fixedBondLength = 52
    o.minFontSize = 18
    o.annotationFontScale = 0.9
    o.clearBackground = True
    o.addAtomIndices = False
    o.highlightRadius = 0.42
    hb = bonds or {}
    d.DrawMolecule(m, highlightAtoms=list(colors), highlightAtomColors=colors,
                   highlightAtomRadii=radii or {}, highlightBonds=list(hb), highlightBondColors=hb)
    d.FinishDrawing()
    return Image.open(io.BytesIO(d.GetDrawingText()))


def reaction_row(ax, images, plus_positions, arrow_after):
    """Lay molecule images side by side with '+' and an arrow."""
    ax.axis("off")
    widths = [im.size[0] for im in images]
    gap = 60
    total = sum(widths) + gap * (len(images) - 1)
    x = 0
    for k, im in enumerate(images):
        ax.imshow(np.asarray(im), extent=(x, x + im.size[0], 0, im.size[1]))
        x += im.size[0]
        if k < len(images) - 1:
            if k == arrow_after:
                ax.add_patch(FancyArrowPatch((x + 8, im.size[1] / 2), (x + gap - 8, im.size[1] / 2),
                                             arrowstyle="-|>", mutation_scale=22, lw=2, color=INK))
            else:
                ax.text(x + gap / 2, im.size[1] / 2, "+", ha="center", va="center", fontsize=22, color=INK)
            x += gap
    ax.set_xlim(-10, total + 10)
    ax.set_ylim(0, max(im.size[1] for im in images))
    ax.set_aspect("equal")


SUBS = [("H2O2", "H$_2$O$_2$"), ("FADH2", "FADH$_2$"), ("FMNH2", "FMNH$_2$"), ("CO2", "CO$_2$"),
        ("H2O", "H$_2$O"), ("O2", "O$_2$"), ("CH2", "CH$_2$")]


def sub(t):
    for a, b in SUBS:
        t = t.replace(a, b)
    return t


def box(fig, x, y, w, h, title, body, edge=GREY, face="white", title_color=INK, mono=False, fs=10.5, wrap=92):
    ax = fig.add_axes([x, y, w, h])
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.005, 0.01), 0.99, 0.98, boxstyle="round,pad=0.005,rounding_size=0.025",
                                transform=ax.transAxes, fc=face, ec=edge, lw=1.6))
    ax.text(0.025, 0.93, title, transform=ax.transAxes, fontsize=11.5, fontweight="bold", color=title_color, va="top")
    lines = []
    for para in body:
        if para == "":
            lines.append("")
            continue
        lines += [sub(x) for x in textwrap.wrap(para, wrap, subsequent_indent="   " if para.startswith("• ") else "")]
    ax.text(0.025, 0.93 - 0.032 / h, "\n".join(lines), transform=ax.transAxes,
            fontsize=fs, va="top", color=INK, family="DejaVu Sans Mono" if mono else None, linespacing=1.35)
    return ax


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rxn", type=int, default=9)
    ap.add_argument("--attn_dir", default="attn_out")
    ap.add_argument("--explanations", default="chat/prompts/v2_txgemma9b.json")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = Path(args.out or f"figures/chat/chat_example_rxn{args.rxn:02d}")
    out.parent.mkdir(parents=True, exist_ok=True)

    row = pd.read_csv(Path(args.attn_dir) / "summary.tsv", sep="\t").set_index("reaction").loc[args.rxn]
    fact = next(f for f in json.load(open(Path(args.attn_dir) / "reaction_facts.json")) if f["rxn_id"] == args.rxn)
    rec = next(r for r in json.load(open(args.explanations)) if r["rxn_id"] == args.rxn)
    smiles = row["rxn_smiles"]
    mols = rf.split_rxn(smiles)
    centre = rf.analyse_mapping(fact["mapping"]["mapped_rxn"], mols)[4]
    d = np.load(Path(args.attn_dir) / f"rxn{args.rxn:02d}_smiles_attn.npz", allow_pickle=True)
    att, _ = rf.attention_by_atom(d["char_spans"], d["weights"].astype(float), mols)
    amax = max(att.values())

    # ── panel A: reaction centre; panel B: attention ─────────────────────────────
    imgs_a, imgs_b = [], []
    for lab, smi, _ in mols:
        m = Chem.MolFromSmiles(smi)
        c_atoms = {i: to_rgb(LAVENDER) for (l, i) in centre if l == lab}
        c_bonds = {b.GetIdx(): to_rgb(LAVENDER) for b in m.GetBonds()
                   if b.GetBeginAtomIdx() in c_atoms and b.GetEndAtomIdx() in c_atoms}
        imgs_a.append(draw_mol(smi, c_atoms, bonds=c_bonds))
        a_cols = {i: ATT_CMAP(att.get((lab, i), 0) / amax)[:3] for i in range(m.GetNumAtoms()) if att.get((lab, i), 0) > 0.004}
        a_rad = {i: 0.25 + 0.35 * att.get((lab, i), 0) / amax for i in a_cols}
        imgs_b.append(draw_mol(smi, a_cols, radii=a_rad))
    n_react = sum(lab.startswith("Reactant") for lab, *_ in mols)

    fig = plt.figure(figsize=(17, 9.6), facecolor="white")
    axA = fig.add_axes([0.015, 0.53, 0.45, 0.36])
    reaction_row(axA, imgs_a, None, n_react - 1)
    fig.text(0.015, 0.93, "A", fontsize=20, fontweight="bold")
    fig.text(0.04, 0.932, "Reaction centre (atom mapping)", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.04, 0.905, "atoms and bonds that change are highlighted", fontsize=10.5, color=GREY)

    axB = fig.add_axes([0.015, 0.09, 0.45, 0.36])
    reaction_row(axB, imgs_b, None, n_react - 1)
    fig.text(0.015, 0.49, "B", fontsize=20, fontweight="bold")
    fig.text(0.04, 0.492, "Gemma4EC attention on atoms", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.04, 0.465, "all layers and heads, from the tokens that generate the EC number", fontsize=10.5, color=GREY)
    cax = fig.add_axes([0.12, 0.065, 0.25, 0.014])
    cb = fig.colorbar(plt.cm.ScalarMappable(cmap=ATT_CMAP, norm=plt.Normalize(0, amax * 100)), cax=cax,
                      orientation="horizontal")
    cb.set_label("attention per atom (%)", fontsize=10)
    cb.ax.tick_params(labelsize=9)

    # ── right: the interaction ──────────────────────────────────────────────────
    fig.text(0.49, 0.93, "C", fontsize=20, fontweight="bold")
    fig.text(0.515, 0.932, "Interaction", fontsize=13, fontweight="bold", color=INK)
    topk = ', '.join(f"EC {e.split(':')[0].lstrip('0').replace('.0', '.')} ({float(e.split(':')[1]):.0%})"
                     for e in str(row["topk_ec"]).split(';')[:1])
    cand = next(c for c in rec["candidates"] if c["ec4"] == rec["chosen_ec4"])
    expl = rec["explanation"].replace("**", "")
    mech = expl.split("WHY EC", 1)[0].replace("MECHANISM:", "").strip()
    why = "WHY EC" + expl.split("WHY EC", 1)[1] if "WHY EC" in expl else ""
    why = why.replace(f"WHY EC {cand['ec4']}:", "").strip()
    n_votes = sum(rec["votes"].values())

    ax_in = box(fig, 0.49, 0.80, 0.495, 0.11, "Input  →  Gemma4EC", [], fs=10.5)
    ax_in.text(0.025, 0.55, smiles, transform=ax_in.transAxes, fontsize=10.5, family="DejaVu Sans Mono", va="center")
    ax_in.text(0.025, 0.22, f"Predicted EC sub-subclass:  {topk}", transform=ax_in.transAxes, fontsize=11, va="center",
               fontweight="bold", color=PURPLE)
    facts = [f"• {rec['summary']}"] + [f"• {c}" for c in rec["changes"]] + \
            [f"• Known reaction: EC {k['ec'][0]}  {k['equation']}" for k in fact["known_reactions"][:1]]
    box(fig, 0.49, 0.585, 0.495, 0.195, "Computed facts  (RDKit · RXNMapper · MetaNetX; written by code)", facts,
        fs=10.5, wrap=112)
    body = [f"Enzyme: EC {cand['ec4']} {cand['name']}  ({rec['votes'].get(cand['ec4'], 0)}/{n_votes} votes)", "",
            f"Mechanism: {mech}", "", f"Why EC {cand['ec4']}: {why}"]
    box(fig, 0.49, 0.25, 0.495, 0.315, "TxGemma-9B-Chat (explanation)", body, edge=PURPLE, face=PAPER, title_color=PURPLE,
        fs=11, wrap=106)
    ref = (cand.get("reference") or {}).get("source", "none")
    fig.text(0.495, 0.21, f"Confidence: {rec['confidence']}  ({'; '.join(rec['confidence_reasons'])}).",
             fontsize=10.2, color=INK, wrap=True)
    fig.text(0.495, 0.183, f"Mechanism reference given to the model: {ref}.  Caveats: "
             f"{'; '.join(rec['caveats']) if rec['caveats'] else 'none detected'}.", fontsize=10.2, color=GREY)

    fig.savefig(out.with_suffix(".png"), dpi=300)
    fig.savefig(out.with_suffix(".pdf"))

    md = [f"# Gemma4EC chat example: reaction {args.rxn}\n",
          f"**Input:** `{smiles}`\n", f"**Gemma4EC:** {topk}\n",
          "**Computed facts** (RDKit, RXNMapper, MetaNetX):\n" + "\n".join(f"- {x[2:]}" for x in facts) + "\n",
          f"**TxGemma-9B-Chat**\n", f"> **Enzyme:** EC {cand['ec4']} {cand['name']} "
          f"({rec['votes'].get(cand['ec4'], 0)}/{n_votes} votes)\n>",
          f"> **Mechanism:** {mech}\n>", f"> **Why EC {cand['ec4']}:** {why}\n",
          f"**Attention:** {rec['attention'].removeprefix('Attention: ')}\n",
          f"**Confidence: {rec['confidence']}** ({'; '.join(rec['confidence_reasons'])}).\n",
          f"*Mechanism reference given to the model: {ref}.*\n"]
    out.with_suffix(".md").write_text("\n".join(md))
    print(f"Saved {out}.png / .pdf / .md")


if __name__ == "__main__":
    main()
