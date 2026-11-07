#!/usr/bin/env python3
"""Score filled rating sheets: Krippendorff's alpha per item, means with bootstrap 95% CI (overall and by
whether Gemma4EC was right), and with --consensus one majority score per item (ties go to the worse score).

Usage: python chat/eval/score_ratings.py chat/eval/ratings/KEY.csv chat/eval/ratings/ratings_*.csv [--consensus]
"""

import argparse
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

RUBRIC = ["mechanism_correct", "enzyme_plausible", "contradicts_reaction", "unverifiable_detail", "useful"]


def alpha_ordinal(mat):
    """Krippendorff's alpha for ordinal data; mat is items x raters, NaN where not rated."""
    vals = mat[~np.isnan(mat)]
    if len(vals) == 0 or np.all(vals == vals[0]):
        return np.nan
    levels = np.unique(vals)
    # observed disagreement: mean squared difference between rater pairs within an item
    num = den = 0.0
    for row in mat:
        r = row[~np.isnan(row)]
        if len(r) < 2:
            continue
        for a, b in combinations(r, 2):
            num += (a - b) ** 2
            den += 1
    if den == 0:
        return np.nan
    do = num / den
    # expected disagreement: the same over all pairs of values, regardless of item
    de = np.mean([(a - b) ** 2 for a, b in combinations(vals, 2)]) if len(vals) > 1 else np.nan
    return 1 - do / de if de else np.nan


def boot_ci(x, n=10000, seed=0):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    bs = rng.choice(x, (n, len(x)), replace=True).mean(axis=1)
    return x.mean(), *np.percentile(bs, [2.5, 97.5])


# items where a higher score is worse, so a tie is broken upwards (the more critical reading)
NEGATIVE = {"unsupported_claims", "contradicts_reaction", "unverifiable_detail"}
# what counts as passing each item when the consensus is turned into a rate
PASS = {"mechanism_correct": 2, "enzyme_plausible": 2, "useful": 2,
        "unsupported_claims": 0, "contradicts_reaction": 0, "unverifiable_detail": 0}


def consensus(R, args):
    """Majority score per item, and the pass rates it implies."""
    items = [c for c in RUBRIC if c in R]
    out, stats_rows = {}, []
    for item in items:
        wide = R.pivot_table(index="item_id", columns="rater", values=item, aggfunc="first")
        picks, majority = {}, 0
        for rid, row in wide.iterrows():
            v = row.dropna().astype(int)
            if v.empty:
                continue
            counts = v.value_counts()
            top = counts.max()
            best = sorted(counts[counts == top].index)
            if len(best) == 1:
                picks[rid] = best[0]
                majority += top > len(v) / 2
            else:   # no majority: take the more critical of the tied scores
                picks[rid] = max(best) if item in NEGATIVE else min(best)
        out[item] = pd.Series(picks)
        ok = PASS[item]
        rate = (out[item] == ok).mean()
        stats_rows.append({"item": item, "n": len(out[item]), "pass_rate": rate,
                           "clear_majority": majority / max(len(out[item]), 1),
                           "mean": out[item].mean()})
    print("\n=== consensus over raters (majority; ties broken towards the worse score) ===")
    df = pd.DataFrame(stats_rows)
    df["pass_rate"] = (df.pass_rate * 100).round(0).astype(int).astype(str) + "%"
    df["clear_majority"] = (df.clear_majority * 100).round(0).astype(int).astype(str) + "%"
    print(df.round(2).to_string(index=False))
    print("  pass = top score, or 0 for the items where a higher score is worse;")
    print("  clear_majority = share of items where more than half the raters gave the chosen score.")
    if args.out:
        pd.DataFrame(out).rename_axis("item_id").to_csv(args.out)
        print(f"  per-item consensus -> {args.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("key", type=Path)
    ap.add_argument("ratings", type=Path, nargs="+", help="one filled ratings.csv per rater")
    ap.add_argument("--consensus", action="store_true", help="also report the majority score per item")
    ap.add_argument("--out", type=Path, help="write the per-item consensus to this CSV")
    args = ap.parse_args()

    key = pd.read_csv(args.key)
    raters = []
    for i, p in enumerate(args.ratings):
        d = pd.read_csv(p)
        d["rater"] = p.stem
        raters.append(d)
    R = pd.concat(raters)
    print(f"{len(args.ratings)} raters x {key.item_id.nunique()} items")

    print("\n=== inter-rater agreement (Krippendorff's alpha, ordinal) ===")
    for item in RUBRIC:
        if item not in R:
            continue
        wide = R.pivot_table(index="item_id", columns="rater", values=item, aggfunc="first")
        a = alpha_ordinal(wide.to_numpy(dtype=float))
        flag = "" if not np.isfinite(a) else ("  (good)" if a > .8 else "  (tentative)" if a > .67
                                              else "  (too noisy)")
        print(f"  {item:20s} alpha = {a:5.3f}{flag}")

    merged = R.merge(key, on="item_id", how="left")
    print("\n=== scores (mean over raters per item, bootstrap 95% CI over items) ===")
    for item in RUBRIC:
        if item not in merged:
            continue
        per_item = merged.groupby("item_id")[item].mean()
        m, lo, hi = boot_ci(per_item)
        print(f"  {item:20s} {m:4.2f}  [{lo:4.2f}, {hi:4.2f}]")

    if "gemma_correct" in merged and merged.gemma_correct.notna().any():
        print("\n=== split by whether Gemma4EC's prediction was right (raters were blind) ===")
        for item in RUBRIC:
            if item not in merged:
                continue
            per = merged.groupby(["item_id", "gemma_correct"])[item].mean().reset_index()
            line = f"  {item:20s}"
            for val in [True, False]:
                sub = per[per.gemma_correct == val][item]
                m, lo, hi = boot_ci(sub)
                line += f"   {'correct' if val else 'wrong'} {m:4.2f} [{lo:4.2f},{hi:4.2f}]"
            print(line)

    if args.consensus:
        consensus(R, args)


if __name__ == "__main__":
    main()
