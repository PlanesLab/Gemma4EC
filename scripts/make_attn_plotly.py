#!/usr/bin/env python3
"""
make_attn_plotly.py — convert existing bertviz HTML files to self-contained
plotly attention visualizations that open reliably in any browser.

Reads each rxnNN_bertviz.html (or rxnNN_bertviz_slim.html) in attn_out/,
extracts the embedded attention data, and writes rxnNN_attn.html — one file
per reaction with a head selector dropdown.  No GPU, no model needed.

Usage:
    cd /scratch/jarcagniriv/Gemma4EC
    pip install plotly         # one-time
    python make_attn_plotly.py
"""

import json
import argparse
from pathlib import Path


# ── extract attention data from an existing bertviz HTML ─────────────────────

def load_bertviz_params(html_path: Path) -> dict:
    text = html_path.read_text(encoding="utf-8")
    marker = "const params = "
    idx = text.find(marker)
    if idx == -1:
        raise ValueError(f"No bertviz params found in {html_path}")
    json_start = idx + len(marker)
    params, _ = json.JSONDecoder().raw_decode(text, json_start)
    return params


# ── build a self-contained plotly HTML ───────────────────────────────────────

def make_plotly_html(params: dict, rxn_label: str, summary_row: dict) -> str:
    entry      = params["attention"][0]
    attn       = entry["attn"]        # [layers][heads][from][to]
    tokens     = entry["left_text"]   # list[str]
    n_layers   = len(attn)
    n_heads    = len(attn[0])
    n_tok      = len(tokens)

    # Readable token labels (strip Ġ/Ċ sentencepiece artefacts)
    labels = [t.replace("▁", " ").replace("Ġ", " ").replace("Ċ", "↵") for t in tokens]

    # Build one heatmap trace per (layer, head)
    traces_json = []
    for li in range(n_layers):
        for hi in range(n_heads):
            z    = attn[li][hi]   # [from][to]
            name = f"Layer {li} · Head {hi}"
            traces_json.append({
                "type":        "heatmap",
                "z":           z,
                "x":           labels,
                "y":           labels,
                "colorscale":  "Blues",
                "reversescale": False,
                "zmin":        0,
                "zmax":        1,
                "name":        name,
                "visible":     (li == 0 and hi == 0),
                "hovertemplate": "From: %{y}<br>To: %{x}<br>Weight: %{z:.4f}<extra></extra>",
            })

    n_traces = n_layers * n_heads

    # Dropdown buttons — one per head (always shows last layer, or per head)
    buttons = []
    for li in range(n_layers):
        for hi in range(n_heads):
            vis = [False] * n_traces
            vis[li * n_heads + hi] = True
            buttons.append({
                "label":  f"Layer {li} · Head {hi}",
                "method": "update",
                "args":   [{"visible": vis},
                           {"title": f"{rxn_label} — Layer {li} · Head {hi}"}],
            })

    true_ec  = summary_row.get("true_ec",      "?")
    pred_ec  = summary_row.get("predicted_ec", "?")
    correct  = "✓" if str(summary_row.get("correct_L3", "")).lower() == "true" else "✗"

    layout = {
        "title":  f"{rxn_label} — Layer 0 · Head 0 | True: {true_ec} → Pred: {pred_ec} {correct}",
        "height": max(500, 14 * n_tok),
        "width":  max(600, 14 * n_tok),
        "xaxis":  {"tickangle": -45, "tickfont": {"size": 8}, "automargin": True},
        "yaxis":  {"tickfont":  {"size": 8}, "automargin": True, "autorange": "reversed"},
        "updatemenus": [{
            "buttons":    buttons,
            "direction":  "down",
            "showactive": True,
            "x":          1.15,
            "xanchor":    "left",
            "y":          1.0,
            "yanchor":    "top",
            "pad":        {"r": 10, "t": 10},
        }],
        "margin": {"l": 120, "r": 200, "t": 80, "b": 120},
    }

    traces_str = json.dumps(traces_json)
    layout_str = json.dumps(layout)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Attention — {rxn_label}</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
</head>
<body style="font-family:sans-serif; padding:12px;">
<h3>{rxn_label} &nbsp; True EC: <b>{true_ec}</b> → Predicted: <b>{pred_ec}</b> {correct}</h3>
<p style="font-size:0.85em;color:#555;">
  Rows = query token (FROM), Columns = key token (TO).<br>
  Showing the last model layer stored in the bertviz output.
  Use the dropdown (top-right) to switch heads.
</p>
<div id="plot"></div>
<script>
var traces = {traces_str};
var layout = {layout_str};
Plotly.newPlot('plot', traces, layout, {{responsive: true}});
</script>
</body>
</html>"""
    return html


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--attn_dir", default="./attn_out")
    args = p.parse_args()

    out_dir = Path(args.attn_dir)

    # Load summary for EC labels
    summary_path = out_dir / "summary.tsv"
    summary = {}
    if summary_path.exists():
        import csv
        with open(summary_path) as f:
            for row in csv.DictReader(f, delimiter="\t"):
                rxn_num = int(row["reaction"])
                summary[rxn_num] = row

    html_files = sorted(out_dir.glob("*_bertviz.html"))
    if not html_files:
        print(f"No *_bertviz.html files found in {out_dir}")
        return

    for html_path in html_files:
        # Extract reaction number from filename (rxn01, rxn02, …)
        stem    = html_path.stem.replace("_bertviz", "")   # e.g. "rxn01"
        rxn_num = int("".join(filter(str.isdigit, stem)))
        label   = f"Reaction {rxn_num:02d} ({stem})"

        print(f"  {stem}  ", end="", flush=True)
        try:
            params = load_bertviz_params(html_path)
        except Exception as exc:
            print(f"SKIP ({exc})")
            continue

        row_data = summary.get(rxn_num, {})
        html     = make_plotly_html(params, label, row_data)

        out_path = out_dir / f"{stem}_attn.html"
        out_path.write_text(html, encoding="utf-8")
        size_kb = len(html.encode()) / 1024
        print(f"→  {out_path.name}  ({size_kb:.0f} KB)")

    print(f"\nDone. Open any rxnNN_attn.html in a browser.")
    print("(Plotly loads ~3 MB of JS from CDN on first open; cached after that.)")


if __name__ == "__main__":
    main()
