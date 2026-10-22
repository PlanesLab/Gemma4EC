#!/usr/bin/env python3
"""
Two stand-alone panels for one reaction, with identical molecule drawings (same 2D coordinates, scale and framing):
  <out>_reaction_centre.{png,pdf}: atoms and bonds that change (atom mapping) highlighted
  <out>_attention.{png,pdf}:       Gemma4EC attention projected onto atoms
Products are drawn in the orientation of the matching reactant (common-substructure alignment).

Usage (gemma4ec env):
    python figures/chat_reaction_panels.py [--rxn 9] [--out figures/chat/rxn09]
"""

import argparse
import io
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from PIL import Image, ImageChops
from rdkit import Chem
from rdkit.Chem import AllChem, rdDepictor, rdFMCS
from rdkit.Chem.Draw import rdMolDraw2D

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "chat"))
import reaction_facts as rf  # noqa: E402

# Gemma4EC-9B / Gemma4EC-2B colours of the benchmark figures (figures/seed_figures.R); red for the reaction centre
PURPLE, LAVENDER, RED, INK = "#685477", "#B7A5E2", "#C23B45", "#2B2B2B"
# white -> Gemma4EC-2B -> a saturated mid purple (full Gemma4EC-9B was too dark under atom labels)
ATT_CMAP = LinearSegmentedColormap.from_list("att", ["#FFFFFF", LAVENDER, "#7D5BA6"])
ATT_MAX = 0.15        # colour scale 0-15 % attention per atom
plt.rcParams.update({"font.family": "Liberation Sans"})
RES = 3               # pixel density multiplier (about RES x 300 dpi)
TRANSPARENT = False   # set by --transparent: no background in the saved figure
FIG_W_IN = 3.1        # figure width in inches (legend fonts are in points, so this fixes their relative size)
BOND_PX = 95 * RES    # bond length in pixels: sets molecule size, identical in both panels
CANVAS = (1600, 1200)


def _reach(m, start, block):
    """Atoms reachable from start without passing through block."""
    seen, stack = set(), [start]
    while stack:
        a = stack.pop()
        if a in seen or a == block:
            continue
        seen.add(a)
        stack += [n.GetIdx() for n in m.GetAtomWithIdx(a).GetNeighbors()]
    return seen


def abbreviate(smi, min_chain=5):
    """Collapse CoA (-> SCoA) and long acyl chains (-> exact formula, e.g. C17H31) into labelled pseudo-atoms.
    Returns (mol, {new index: [original indices]})."""
    m = Chem.MolFromSmiles(smi)
    for a in m.GetAtoms():
        a.SetIntProp("orig", a.GetIdx())
    groups, used = [], set()
    for c, o, sx, _ in m.GetSubstructMatches(Chem.MolFromSmarts("[CX3](=O)[SX2][CH2]")):
        mem = _reach(m, sx, c)
        if len(mem) > 20 and not mem & used:
            groups.append((c, mem, "SCoA"))
            used |= mem
    for c, o, x, alpha in m.GetSubstructMatches(Chem.MolFromSmarts("[CX3](=O)([O,S])[CX4]")):
        mem = _reach(m, alpha, c)
        atoms = [m.GetAtomWithIdx(i) for i in mem]
        if len(mem) >= min_chain and not mem & used and all(a.GetSymbol() == "C" and not a.IsInRing() for a in atoms):
            nh = sum(a.GetTotalNumHs() for a in atoms)
            groups.append((c, mem, f"C<sub>{len(mem)}</sub>H<sub>{nh}</sub>"))
            used |= mem
    rw = Chem.RWMol(m)
    for k, (anchor, mem, label) in enumerate(groups):
        d = Chem.Atom(0)
        d.SetProp("atomLabel", label)
        d.SetIntProp("orig", -(k + 1))
        di = rw.AddAtom(d)
        rw.AddBond(anchor, di, Chem.BondType.SINGLE)
    for i in sorted(used, reverse=True):
        rw.RemoveAtom(i)
    nm = rw.GetMol()
    Chem.SanitizeMol(nm, Chem.SanitizeFlags.SANITIZE_ALL ^ Chem.SanitizeFlags.SANITIZE_PROPERTIES)
    mapping = {}
    for a in nm.GetAtoms():
        o = a.GetIntProp("orig")
        mapping[a.GetIdx()] = [o] if o >= 0 else sorted(groups[-o - 1][1])
    return nm, mapping


def depict(mols):
    """2D coordinates: reactants on their own, each product aligned to its largest common substructure with a reactant."""
    out = {}
    reactants = []
    for lab, smi, _ in mols:
        m = Chem.Mol(smi) if isinstance(smi, Chem.Mol) else Chem.MolFromSmiles(smi)
        rdDepictor.SetPreferCoordGen(True)
        rdDepictor.Compute2DCoords(m)
        if lab.startswith("Product") and reactants:
            best = max(reactants, key=lambda r: rdFMCS.FindMCS([r, m], timeout=10).numAtoms)
            mcs = rdFMCS.FindMCS([best, m], timeout=10, ringMatchesRingOnly=True)
            if mcs.numAtoms >= 3:
                patt = Chem.MolFromSmarts(mcs.smartsString)
                ref_match, prb_match = best.GetSubstructMatch(patt), m.GetSubstructMatch(patt)
                rdDepictor.GenerateDepictionMatching2DStructure(m, best, atomMap=list(zip(ref_match, prb_match)))
        elif lab.startswith("Reactant"):
            reactants.append(m)
        out[lab] = m
    return out


def on_white(im):
    """Flatten onto white (unpainted canvas is transparent and would turn black); keep alpha if TRANSPARENT."""
    im = im.convert("RGBA")
    if TRANSPARENT:
        return im
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    return Image.alpha_composite(bg, im).convert("RGB")


def bounds(m, margin=1.4):
    xy = np.array([[p.x, p.y] for p in m.GetConformer().GetPositions()[:, None].tolist() for p in []] or
                  [[m.GetConformer().GetAtomPosition(i).x, m.GetConformer().GetAtomPosition(i).y]
                   for i in range(m.GetNumAtoms())])
    return xy[:, 0].min() - margin, xy[:, 1].min() - margin, xy[:, 0].max() + margin, xy[:, 1].max() + margin


def render(m, atom_cols, radii=None, bond_cols=None):
    """Draw into a fixed coordinate window, so two renderings of the same molecule overlay exactly."""
    from rdkit.Geometry import Point2D
    x0, y0, x1, y1 = bounds(m)
    S = BOND_PX / 1.5                       # RDKit depictions use 1.5 A bonds
    W, H = int((x1 - x0) * S * 1.6), int((y1 - y0) * S * 1.6)   # roomy canvas; cropped to content later
    d = rdMolDraw2D.MolDraw2DCairo(W, H)
    o = d.drawOptions()
    o.bondLineWidth = 3 * RES
    o.minFontSize = 50 * RES
    o.maxFontSize = 50 * RES
    o.highlightRadius = 0.45
    o.clearBackground = True
    o.padding = 0.0
    o.useBWAtomPalette()          # same label colours whether or not an atom is highlighted
    if TRANSPARENT:
        o.setBackgroundColour((1, 1, 1, 0))
    o.fixedBondLength = BOND_PX   # (SetScale would cap atom-label fonts at 40 px)
    bc = bond_cols or {}
    d.DrawMolecule(m, highlightAtoms=list(atom_cols), highlightAtomColors=atom_cols,
                   highlightAtomRadii=radii or {}, highlightBonds=list(bc), highlightBondColors=bc)
    coords = {i: (d.GetDrawCoords(i).x, d.GetDrawCoords(i).y) for i in range(m.GetNumAtoms())}
    d.FinishDrawing()
    img = on_white(Image.open(io.BytesIO(d.GetDrawingText())))
    img.info["coords"] = coords
    return img


def render_combined(m, red_atoms, red_bonds, att_cols, att_radii, red_alpha=0.45):
    """Reaction centre (translucent red, under) and attention (purple, over) drawn on one canvas, so they align."""
    from rdkit.Geometry import Point2D
    x0, y0, x1, y1 = bounds(m)
    S = BOND_PX / 1.5
    W, H = int((x1 - x0) * S * 1.6), int((y1 - y0) * S * 1.6)   # roomy canvas; cropped to content later
    d = rdMolDraw2D.MolDraw2DCairo(W, H)
    o = d.drawOptions()
    o.bondLineWidth = 3 * RES
    o.minFontSize = 50 * RES
    o.maxFontSize = 50 * RES
    o.padding = 0.0
    o.useBWAtomPalette()
    o.clearBackground = True
    if TRANSPARENT:
        o.setBackgroundColour((1, 1, 1, 0))
    o.fixedBondLength = BOND_PX   # (SetScale would cap atom-label fonts at 40 px)
    # translucent red pre-blended with white, so the oval is even and the purple drawn later sits on top
    rc = tuple(red_alpha * c + (1 - red_alpha) for c in to_rgb(RED))
    white = {i: (1, 1, 1, 0) if TRANSPARENT else (1, 1, 1) for i in att_cols}   # invisible layout pass
    o.highlightRadius = 0.45
    # pass 1: same highlight set (invisible, white) as pass 3, so both passes get the identical layout
    d.DrawMolecule(m, highlightAtoms=list(att_cols), highlightAtomColors=white, highlightAtomRadii=att_radii,
                   highlightBonds=[], highlightBondColors={})
    conf = m.GetConformer()
    pos = lambda i: np.array([conf.GetAtomPosition(i).x, conf.GetAtomPosition(i).y])
    A = np.array([pos(i) for i in red_atoms])
    # extra points where hydrogen labels are drawn (e.g. "HO": the H sits beyond the O, away from its bond)
    extra = []
    for i in red_atoms:
        at = m.GetAtomWithIdx(i)
        if at.GetSymbol() != "C" and at.GetTotalNumHs() and at.GetDegree() == 1:
            nb = pos(at.GetNeighbors()[0].GetIdx())
            w = pos(i) - nb
            extra.append(pos(i) + 0.55 * w / np.linalg.norm(w))
    P = np.vstack([A] + ([np.array(extra)] if extra else []))
    if len(A):
        if len(A) > 1:
            u = A[-1] - A[0]
            u = u / np.linalg.norm(u)
        else:
            u = np.array([1.0, 0.0])
        proj = P @ u
        c = A.mean(axis=0) + ((proj.max() + proj.min()) / 2 - A.mean(axis=0) @ u) * u   # centred on the full extent
        a = (proj.max() - proj.min()) / 2 + 0.55                                         # semi-axes in Angstrom
        v, b = np.array([-u[1], u[0]]), 0.55
        t = np.linspace(0, 2 * np.pi, 90)
        pts = [Point2D(*(c + a * np.cos(k) * u + b * np.sin(k) * v)) for k in t]
        d.SetFillPolys(True)
        d.SetColour(rc)
        d.DrawPolygon(pts)
    o.clearBackground = False
    d.DrawMolecule(m, highlightAtoms=list(att_cols), highlightAtomColors=att_cols, highlightAtomRadii=att_radii,
                   highlightBonds=[], highlightBondColors={})
    d.FinishDrawing()
    return on_white(Image.open(io.BytesIO(d.GetDrawingText())))


def bbox(*imgs, pad=30):
    """Union bounding box of non-white content over several renderings of the same molecule."""
    boxes = [(im.getchannel("A").getbbox() if im.mode == "RGBA" else
              ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()) for im in imgs]
    boxes = [b for b in boxes if b]
    x0, y0 = min(b[0] for b in boxes) - pad, min(b[1] for b in boxes) - pad
    x1, y1 = max(b[2] for b in boxes) + pad, max(b[3] for b in boxes) + pad
    return max(x0, 0), max(y0, 0), x1, y1


def compose(images, n_react, path, colorbar=None, gap=45 * RES, red_key=False):
    """Molecules side by side on a common baseline, '+' between reactants, thin straight arrow before products."""
    H = max(im.size[1] for im in images)
    edge = 0
    # wider gap before the products: the arrow sits fully between the last reactant and the first product
    gap = max(gap, int(0.12 * max(im.size[1] for im in images)))       # scale spacing with molecule height
    gaps = [int(gap * 2.4) if k == n_react - 1 else gap for k in range(len(images) - 1)]
    W = sum(im.size[0] for im in images) + sum(gaps) + 2 * edge
    dpi = W / FIG_W_IN                 # fixed physical width: legend keeps its proportions at any resolution
    fig_h = H / dpi + (0.52 if colorbar else 0.02)
    fig = plt.figure(figsize=(W / dpi, fig_h), dpi=dpi, facecolor="none" if TRANSPARENT else "white")
    ax = fig.add_axes([0, (0.52 / fig_h) if colorbar else 0, 1, (H / dpi) / fig_h])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    x = edge
    for k, im in enumerate(images):
        y0 = (H - im.size[1]) / 2
        ax.imshow(np.asarray(im), extent=(x, x + im.size[0], y0, y0 + im.size[1]), interpolation="lanczos")
        x += im.size[0]
        if k < len(images) - 1:
            g = gaps[k]
            if k == n_react - 1:
                ax.annotate("", xy=(x + g - 12 * RES, H / 2), xytext=(x + 12 * RES, H / 2),
                            arrowprops=dict(arrowstyle="-|>,head_length=0.5,head_width=0.18", lw=1.2, color="black",
                                            shrinkA=0, shrinkB=0))
            else:
                ax.text(x + g / 2, H / 2, "+", ha="center", va="center", fontsize=16, color=INK)
            x += g
    if colorbar:
        vmax, label = colorbar
        cax = fig.add_axes([0.12 if red_key else 0.35, 0.38 / fig_h, 0.3, 0.07 / fig_h])
        cb = fig.colorbar(plt.cm.ScalarMappable(cmap=ATT_CMAP, norm=plt.Normalize(0, vmax)), cax=cax,
                          orientation="horizontal")
        cb.set_ticks([0, 5, 10, 15] if vmax >= 15 else [0, vmax / 2, vmax])
        cb.set_label(label, fontsize=7)
        cb.ax.tick_params(labelsize=7, width=0.5, length=2)    # numbers same size as the label
        cb.outline.set_linewidth(0.5)
        if red_key:
            from matplotlib.patches import Ellipse
            lax = fig.add_axes([0.58, 0.12 / fig_h, 0.4, 0.42 / fig_h])
            lax.axis("off")
            lax.set_xlim(0, 4)
            lax.set_ylim(0, 1)
            lax.add_patch(Ellipse((0.45, 0.55), 0.7, 0.42, fc=tuple(0.45 * c + 0.55 for c in to_rgb(RED)), ec="none"))
            lax.text(0.95, 0.55, "Reaction Centre", va="center", fontsize=10)
    fig.savefig(path.with_suffix(".png"), dpi=dpi, transparent=TRANSPARENT)
    fig.savefig(path.with_suffix(".pdf"), dpi=dpi, transparent=TRANSPARENT)
    plt.close(fig)
    print(f"Saved {path}.png / .pdf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rxn", type=int, default=9)
    ap.add_argument("--attn_dir", default="attn_out")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no_centre", action="store_true", help="combined figure without the reaction-centre ovals")
    ap.add_argument("--transparent", action="store_true", help="no background; files get a _transparent suffix")
    ap.add_argument("--abbreviate", action="store_true",
                    help="draw CoA as SCoA and long acyl chains as formulas (attention summed onto them)")
    args = ap.parse_args()
    global TRANSPARENT
    TRANSPARENT = args.transparent
    out = Path(args.out or f"figures/chat/rxn{args.rxn:02d}")
    if args.transparent:
        out = Path(f"{out}_transparent")
    out.parent.mkdir(parents=True, exist_ok=True)

    row = pd.read_csv(Path(args.attn_dir) / "summary.tsv", sep="\t").set_index("reaction").loc[args.rxn]
    fact = next(f for f in json.load(open(Path(args.attn_dir) / "reaction_facts.json")) if f["rxn_id"] == args.rxn)
    mols = rf.split_rxn(row["rxn_smiles"])
    centre = rf.analyse_mapping(fact["mapping"]["mapped_rxn"], mols)[4]
    d = np.load(Path(args.attn_dir) / f"rxn{args.rxn:02d}_smiles_attn.npz", allow_pickle=True)
    att, _ = rf.attention_by_atom(d["char_spans"], d["weights"].astype(float), mols)
    if args.abbreviate:
        new_mols, new_att, new_centre = [], {}, set()
        for lab, smi, st in mols:
            nm, mp = abbreviate(smi)
            new_mols.append((lab, nm, st))
            for ni, olds in mp.items():
                new_att[(lab, ni)] = sum(att.get((lab, o), 0) for o in olds)
                if len(olds) == 1 and (lab, olds[0]) in centre:
                    new_centre.add((lab, ni))
        mols, att, centre = new_mols, new_att, new_centre
    amax = max(ATT_MAX, max(att.values()))
    drawn = depict(mols)

    imgs_c, imgs_a, imgs_m = [], [], []
    for lab, _, _ in mols:
        m = drawn[lab]
        c_atoms = {i: to_rgb(RED) for (l, i) in centre if l == lab}
        c_bonds = {b.GetIdx(): to_rgb(RED) for b in m.GetBonds()
                   if b.GetBeginAtomIdx() in c_atoms and b.GetEndAtomIdx() in c_atoms}
        def att_colour(t):
            # transparent figure: fade low attention out instead of drawing near-white discs
            r, g, b = ATT_CMAP(t)[:3]
            return (r, g, b, min(1.0, 2.0 * t)) if TRANSPARENT else (r, g, b)
        a_atoms = {i: att_colour(att.get((lab, i), 0) / amax) for i in range(m.GetNumAtoms())
                   if att.get((lab, i), 0) > 0.004}
        a_rad = {i: 0.28 + 0.35 * att.get((lab, i), 0) / amax for i in a_atoms}
        ic, ia = render(m, c_atoms, bond_cols=c_bonds), render(m, a_atoms, radii=a_rad)
        im_ = render_combined(m, {} if args.no_centre else c_atoms, {} if args.no_centre else c_bonds, a_atoms, a_rad)
        imgs_c.append(ic.crop(bbox(ic, pad=12 * RES)))
        imgs_a.append(ia.crop(bbox(ia, pad=12 * RES)))
        imgs_m.append(im_.crop(bbox(im_, pad=12 * RES)))
    n_react = sum(lab.startswith("Reactant") for lab, *_ in mols)
    compose(imgs_c, n_react, Path(f"{out}_reaction_centre"))
    compose(imgs_a, n_react, Path(f"{out}_attention"), colorbar=(amax * 100, "Gemma4EC attention per atom (%)"))
    att_label = ("Gemma4EC attention (%), summed over abbreviated groups" if args.abbreviate
                 else "Gemma4EC attention per atom (%)")
    compose(imgs_m, n_react, Path(f"{out}_combined"), colorbar=(amax * 100, att_label),
            red_key=not args.no_centre)


if __name__ == "__main__":
    main()
