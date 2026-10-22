#!/usr/bin/env python3
"""
Flow figure for one example: input reaction -> Gemma4EC -> predicted EC; the reaction with Gemma4EC attention;
then the chat (question/answer bubbles, **bold** spans supported).

Inputs: the reaction panel from figures/chat_reaction_panels.py (default figures/chat/rxn09_transparent_combined.png)
and the dialogue in figures/chat/chat_example_rxn09_dialogue.md ("**User:** ..." / "**Gemma4EC:** ..." lines).

Usage (gemma4ec env):
    python figures/chat_flow_figure.py [--out figures/chat/rxn09_flow]
"""

import argparse
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image

PURPLE, LAVENDER, INK, GREY = "#685477", "#B7A5E2", "#1E1E1E", "#6B6B6B"
USER_BG, BOT_BG = "#EDEDED", "#F1ECF9"
plt.rcParams.update({"font.family": ["Liberation Sans", "DejaVu Sans"]})   # fallback has subscript glyphs
FS = 9            # chat font size (pt)
FIG_W = 7.0       # inches


def parse_dialogue(md):
    """[(speaker, text)] from '**Speaker:** text' paragraphs."""
    turns = []
    for para in re.split(r"\n\s*\n", Path(md).read_text().strip()):
        m = re.match(r"\*\*(User|Gemma4EC):\*\*\s*(.*)", para.strip(), re.S)
        if m:
            turns.append((m.group(1), " ".join(m.group(2).split())))
    return turns


def rich_words(text):
    """[(word, bold, mono, space_before)] from markdown-ish text with **bold** and `code` spans."""
    out = []
    for part in re.split(r"(\*\*.*?\*\*|`.*?`)", text):
        if not part:
            continue
        bold, mono = part.startswith("**"), part.startswith("`")
        core = part[2:-2] if bold else part[1:-1] if mono else part
        glue = not (bold or mono) and not part.startswith(" ")      # e.g. "," right after a bold span
        for k, w in enumerate(core.split(" ")):
            if w:
                out.append((w, bold, mono, not (k == 0 and glue)))
    return out


class Canvas:
    """Full-figure axes in points (origin bottom-left), with text measurement."""

    def __init__(self, w_in, h_in, dpi=600):
        self.fig = plt.figure(figsize=(w_in, h_in), dpi=dpi)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.W, self.H = w_in * 72, h_in * 72
        self.ax.set_xlim(0, self.W)
        self.ax.set_ylim(0, self.H)
        self.ax.axis("off")
        self.r = self.fig.canvas.get_renderer()

    def width(self, s, **kw):
        t = self.ax.text(0, 0, s, **kw)
        w = t.get_window_extent(self.r).width * 72 / self.fig.dpi
        t.remove()
        return w

    def rich(self, x, y_top, text, max_w, fs=FS, lead=1.38, color=INK):
        """Lay out rich text from (x, y_top) downwards; returns the height used (pt)."""
        words = rich_words(text)
        space = self.width("a b", fontsize=fs) - self.width("ab", fontsize=fs)
        lines, line, lw = [], [], 0
        for w, b, m, sp in words:
            kw = dict(fontsize=fs * (0.92 if m else 1), fontweight="bold" if b else "normal",
                      family="DejaVu Sans Mono" if m else None)
            ww = self.width(w, **kw)
            gap_ = space if sp else 0
            if line and lw + gap_ + ww > max_w:
                lines.append(line)
                line, lw, gap_ = [], 0, 0
            line.append((w, kw, ww, gap_ if line else 0))
            lw += (gap_ if len(line) > 1 else 0) + ww
        if line:
            lines.append(line)
        lh = fs * lead
        for k, ln in enumerate(lines):
            xx = x
            for w, kw, ww, g in ln:
                xx += g
                self.ax.text(xx, y_top - k * lh, w, va="top", ha="left", color=color, **kw)
                xx += ww
        self.last_width = max(sum(g + ww for _, _, ww, g in ln) for ln in lines) if lines else 0
        return len(lines) * lh


def box(cv, x, y, w, h, fc, ec="none", lw=1.0, r=6):
    cv.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                   fc=fc, ec=ec, lw=lw, zorder=0))


def arrow(cv, x0, y0, x1, y1):
    cv.ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>,head_length=4,head_width=2.2",
                                    lw=1.1, color="black", shrinkA=0, shrinkB=0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="figures/chat/rxn09_combined.png")
    ap.add_argument("--dialogue", default="figures/chat/chat_example_rxn09_dialogue.md")
    ap.add_argument("--smiles", default="COc1ccc(CO)cc1Cl.O=O>>COc1ccc(C=O)cc1Cl")
    ap.add_argument("--prediction", default="EC 1.1.3")
    ap.add_argument("--prediction_note", default="CH–OH donor, O₂ acceptor")
    ap.add_argument("--equation", default="3-chloroanisyl alcohol + O₂ → 3-chloro-anisaldehyde + H₂O₂",
                    help="written reaction shown under the structures (supports **bold**)")
    ap.add_argument("--out", default="figures/chat/rxn09_flow")
    args = ap.parse_args()

    panel = Image.open(args.panel)
    turns = parse_dialogue(args.dialogue)

    # first pass on a tall canvas to measure the chat, then redraw at the exact height
    for final in (False, True):
        H_in = height_in if final else 12
        cv = Canvas(FIG_W, H_in)
        W, y = cv.W, cv.H - 10
        pad, gap = 10, 12

        # ── row 1: input -> Gemma4EC -> prediction ───────────────────────────────
        xs = [pad, 0.54 * W, 0.72 * W]
        ws = [0.47 * W, 0.135 * W, 0.27 * W]
        smi_fs = 7.6 if len(args.smiles) <= 48 else 6.0
        cw = cv.width("C" * 20, fontsize=smi_fs, family="DejaVu Sans Mono") / 20
        per_line = max(10, int((ws[0] - 16) / cw))
        smi_lines = [args.smiles[i:i + per_line] for i in range(0, len(args.smiles), per_line)]
        lh = smi_fs * 1.25
        row_h = max(40, 24 + len(smi_lines) * lh)
        y0 = y - row_h
        box(cv, xs[0], y0, ws[0], row_h, "white", ec=GREY, lw=0.8)
        cv.ax.text(xs[0] + 8, y0 + row_h - 8, "Input reaction", fontsize=7.5, color=GREY, va="top")
        cv.ax.text(xs[0] + 8, y0 + row_h - 21, "\n".join(smi_lines), fontsize=smi_fs, family="DejaVu Sans Mono",
                   va="top", linespacing=1.25)
        box(cv, xs[1], y0 + (row_h - 40) / 2, ws[1], 40, PURPLE)
        cv.ax.text(xs[1] + ws[1] / 2, y0 + row_h / 2, "Gemma4EC", fontsize=10, fontweight="bold", color="white",
                   ha="center", va="center")
        py0 = y0 + (row_h - 40) / 2
        box(cv, xs[2], py0, ws[2], 40, BOT_BG, ec=LAVENDER, lw=0.8)
        cv.ax.text(xs[2] + 8, py0 + 40 - 8, "Prediction", fontsize=7.5, color=GREY, va="top")
        cv.ax.text(xs[2] + 8, py0 + 16, args.prediction, fontsize=12, fontweight="bold", color=PURPLE, va="center")
        cv.ax.text(xs[2] + 8, py0 + 5.5, args.prediction_note, fontsize=6.5, color=GREY, va="center")
        arrow(cv, xs[0] + ws[0] + 3, y0 + row_h / 2, xs[1] - 3, y0 + row_h / 2)
        arrow(cv, xs[1] + ws[1] + 3, y0 + row_h / 2, xs[2] - 3, y0 + row_h / 2)
        y = y0 - gap

        # ── row 2: reaction with attention ──────────────────────────────────────
        pw = 0.62 * W
        ph = pw * panel.size[1] / panel.size[0]
        px = (W - pw) / 2
        cv.ax.imshow(panel, extent=(px, px + pw, y - ph, y), zorder=1, interpolation="lanczos")
        y = y - ph - 6
        if args.equation:                                   # written equation, centred under the structures
            probe = Canvas(FIG_W, 3)
            probe.rich(0, 100, args.equation, W - 2 * pad, fs=8.5)
            ew = probe.last_width
            plt.close(probe.fig)
            y -= cv.rich((W - ew) / 2, y, args.equation, W - 2 * pad, fs=8.5) + gap
        else:
            y -= gap

        # ── row 3: chat ─────────────────────────────────────────────────────────
        bw = 0.74 * W
        for who, text in turns:
            user = who == "User"
            bx = W - pad - bw if user else pad
            inner = 9
            # measure, then draw bubble behind
            label_h = 11
            probe = Canvas(FIG_W, 3)                     # measure width/height without drawing on cv
            probe.rich(0, 100, text, bw - 2 * inner)
            bw_i = max(probe.last_width + 2 * inner, 110)
            plt.close(probe.fig)
            bx = W - pad - bw_i if user else pad
            h_text = cv.rich(bx + inner, y - inner - label_h, text, bw_i - 2 * inner)
            h = h_text + 2 * inner + label_h - 2
            box(cv, bx, y - h, bw_i, h, USER_BG if user else BOT_BG, ec="none" if user else LAVENDER, lw=0.8, r=8)
            cv.ax.text(bx + inner, y - inner + 1, "User" if user else "Gemma4EC chat", fontsize=7.5,
                       fontweight="bold", color=GREY if user else PURPLE, va="top")
            y = y - h - 7
        used = cv.H - y + 4
        if not final:
            height_in = used / 72
            plt.close(cv.fig)

    out = Path(args.out)
    cv.fig.savefig(out.with_suffix(".png"), dpi=600)
    cv.fig.savefig(out.with_suffix(".pdf"))
    cv.fig.savefig(Path(f"{out}_transparent").with_suffix(".png"), dpi=600, transparent=True)
    print(f"Saved {out}.png / .pdf / _transparent.png ({FIG_W:.1f} x {height_in:.2f} in)")


if __name__ == "__main__":
    main()
