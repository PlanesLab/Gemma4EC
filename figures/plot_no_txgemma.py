"""
Reproduces Figure1B.R: plotnine bar chart + cowplot-style 3-section legend.
Renders at full 600 DPI then composites with PIL for a crisp final image.
"""
import pandas as pd
import numpy as np
import tempfile, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from PIL import Image
from plotnine import (
    ggplot, aes, geom_bar, geom_text, scale_fill_manual,
    scale_y_continuous, labs, theme_minimal, theme,
    element_text, element_blank, element_rect, element_line,
    position_dodge,
)

# ── Data ──────────────────────────────────────────────────────────────────────
df = pd.read_csv("/scratch/jarcagniriv/Gemma4EC/results/summary/weighted_metrics.csv")
rename = {
    "Gemma4EC-9b":      "Gemma4EC-9B",
    "Gemma4EC-2b":      "Gemma4EC-2B",
    "Gemini-2.5-flash": "Gemini-2.5",
    "ChatGPT-5.1":      "GPT-5.1",
    "ChatGPT-5.2":      "GPT-5.2",
    "ChatGPT-4.1-mini": "GPT-4.1-mini",
}
df["Model"] = df["Model"].replace(rename)

gemma_models  = ["Gemma4EC-9B", "Gemma4EC-2B"]
domain_models = ["BEC-Pred", "Theia"]
llm_models    = ["Gemini-2.5", "GPT-5.2", "GPT-5.1", "GPT-4.1-mini"]
all_order     = gemma_models + domain_models + llm_models

pastel_colors = {
    "Gemma4EC-9B":  "#C8B8E8",
    "Gemma4EC-2B":  "#D6CFE8",
    "BEC-Pred":     "#A8DDB5",
    "Theia":        "#AED6F1",
    "Gemini-2.5":   "#E8C97A",
    "GPT-5.2":      "#BF7E92",
    "GPT-5.1":      "#D9A3AE",
    "GPT-4.1-mini": "#E8B7C2",
}

# ── Prepare long-format data ──────────────────────────────────────────────────
def prepare(data):
    present = [m for m in all_order if m in data["Model"].values]
    long = data[data["Model"].isin(present)].melt(
        id_vars="Model",
        value_vars=["Weighted_MCC", "Weighted_PPV", "Weighted_Recall"],
        var_name="Metric", value_name="Value"
    )
    long["Metric"] = long["Metric"].map({
        "Weighted_MCC":    "MCC",
        "Weighted_PPV":    "Precision",
        "Weighted_Recall": "Recall",
    })
    long["Model"]  = pd.Categorical(long["Model"],  categories=present, ordered=True)
    long["Metric"] = pd.Categorical(long["Metric"], categories=["MCC", "Precision", "Recall"], ordered=True)
    long["Label"]  = long["Value"].map(lambda v: f"{v:.2f}")
    return long

# ── Bar plot (plotnine, no legend) ────────────────────────────────────────────
def make_bar_plot(plot_df, fig_w, fig_h):
    return (
        ggplot(plot_df, aes(x="Metric", y="Value", fill="Model"))
        + geom_bar(stat="identity",
                   position=position_dodge(width=0.95),
                   width=0.90,
                   color="white",
                   size=0.3)
        + geom_text(aes(label="Label"),
                    position=position_dodge(width=0.95),
                    va="bottom",
                    size=7.2,
                    color="#555555",
                    fontweight="bold",
                    format_string="{}",
                    nudge_y=0.009)
        + scale_fill_manual(values=pastel_colors, guide=None)
        + scale_y_continuous(limits=(0, 1.0), expand=(0, 0),
                             breaks=[0.00, 0.25, 0.50, 0.75, 1.00])
        + labs(x="", y="")
        + theme_minimal(base_size=18)
        + theme(
            figure_size=(fig_w, fig_h),
            axis_text_x=element_text(size=32, face="bold", color="#555555"),
            axis_text_y=element_text(size=24, color="#888888"),
            axis_title_x=element_blank(),
            axis_title_y=element_blank(),
            legend_position="none",
            plot_background=element_rect(fill="white", color=None),
            panel_background=element_rect(fill="white", color=None),
            panel_grid_major_x=element_blank(),
            panel_grid_minor=element_blank(),
            panel_grid_major_y=element_line(color="#e5e5e5", size=0.6),
        )
    )

# ── Legend panel (matplotlib → PIL) ──────────────────────────────────────────
def make_legend_image(present, leg_w_in, leg_h_in, dpi):
    gemma_p  = [m for m in gemma_models  if m in present]
    domain_p = [m for m in domain_models if m in present]
    llm_p    = [m for m in llm_models    if m in present]
    sections = [(t, m) for t, m in [
        ("Gemma4EC",              gemma_p),
        ("Domain-Specific Models", domain_p),
        ("General-Purpose LLMs",  llm_p),
    ] if m]

    fig, ax = plt.subplots(figsize=(leg_w_in, leg_h_in), dpi=dpi)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    # Count total rows: each section has title + items + gap
    total_rows = sum(len(m) + 1 for _, m in sections) + (len(sections) - 1) * 0.6
    row_h = 1.0 / total_rows
    y = 1.0

    for title, models in sections:
        y -= row_h * 0.85
        ax.text(0.05, y, title,
                fontsize=26, fontweight="bold", color="#222222",
                va="center", ha="left", transform=ax.transAxes,
                fontfamily="sans-serif")
        for model in models:
            y -= row_h
            # colour swatch
            rect = mpatches.FancyBboxPatch(
                (0.05, y - row_h * 0.35), 0.13, row_h * 0.7,
                boxstyle="square,pad=0",
                facecolor=pastel_colors[model], edgecolor="white", linewidth=1.0,
                transform=ax.transAxes, clip_on=False
            )
            ax.add_patch(rect)
            ax.text(0.22, y, model,
                    fontsize=22, color="#555555",
                    va="center", ha="left", transform=ax.transAxes,
                    fontfamily="sans-serif")
        y -= row_h * 0.6   # gap between sections

    tmp = tempfile.mktemp(suffix=".png")
    fig.savefig(tmp, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    img = Image.open(tmp).convert("RGBA")
    os.unlink(tmp)
    return img

# ── Compose bar + legend side-by-side with PIL ────────────────────────────────
def save_figure(data, out_path, width=22, height=10, dpi=600):
    present = [m for m in all_order if m in data["Model"].values]
    plot_df = prepare(data.copy())

    bar_frac = 0.78
    bar_w    = width * bar_frac
    leg_w    = width * (1 - bar_frac)

    # 1. Render bar plot via plotnine at full DPI
    p = make_bar_plot(plot_df, bar_w, height)
    tmp_bar = tempfile.mktemp(suffix=".png")
    p.save(tmp_bar, dpi=dpi, verbose=False)
    bar_img = Image.open(tmp_bar).convert("RGBA")
    os.unlink(tmp_bar)

    # 2. Render legend at same height in pixels
    bar_px_h = bar_img.height
    bar_px_w = bar_img.width
    leg_px_w = int(bar_px_w / bar_frac * (1 - bar_frac))

    leg_img = make_legend_image(present, leg_w, height, dpi)
    leg_img = leg_img.resize((leg_px_w, bar_px_h), Image.LANCZOS)

    # 3. Composite
    total_w = bar_px_w + leg_px_w
    final = Image.new("RGBA", (total_w, bar_px_h), (255, 255, 255, 255))
    final.paste(bar_img, (0, 0))
    final.paste(leg_img, (bar_px_w, 0))
    final.convert("RGB").save(out_path, dpi=(dpi, dpi))
    print(f"Saved: {out_path}")

# ── Run ───────────────────────────────────────────────────────────────────────
df_no_tx     = df[df["Model"] != "TxGemma-9b"].copy()
df_no_tx_bec = df[~df["Model"].isin(["TxGemma-9b", "BEC-Pred"])].copy()

save_figure(df_no_tx,
            "/scratch/jarcagniriv/Gemma4EC/figures/plot_no_txgemma.png")
save_figure(df_no_tx_bec,
            "/scratch/jarcagniriv/Gemma4EC/figures/plot_no_txgemma_no_becpred.png")
