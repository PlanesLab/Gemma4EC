#!/usr/bin/env python3
"""Build the chat evaluation set: reactions with EC4 ground truth from the ECReact release.

ECReact's rxn_smiles embeds the EC ('reactants|1.2.1.8>>products'); matching on (reaction, EC3) recovers the EC4.
Stratified over EC classes, with a quota of reactions Gemma4EC-9B gets wrong at EC3.
Writes rxn_smiles, ec, true_ec4, gemma_pred_ec3, gemma_correct_ec3, ec_class, rxn_id (1-based row = pipeline id).
Usage: python chat/eval/make_eval_set.py --n 100 --n_wrong 15 --seed 0 --out chat/eval/set/reactions.csv
"""
import argparse
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SPLIT = ROOT / "data" / "ECReact_seeds_strat_dedup" / "seed0" / "test.csv"
ECREACT = ROOT / "data" / "external" / "ecreact-1.0.csv"
PREDS = Path("/scratch/jarcagniriv/gemma4ec/seeds_strat_dedup/seed0/gemma4ec_9b/results/"
             "predictions_test.EC_NUMBER.EC_NUMBER_PROMPT_2.msid66vv.tsv")


def ec3(e):
    """'2.07.08' and '2.7.8.3' both -> '2.7.8'."""
    p = str(e).split(".")[:3]
    return ".".join(str(int(x)) if x.strip().isdigit() else x for x in p)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=100, help="total reactions")
    ap.add_argument("--n_wrong", type=int, default=15, help="how many Gemma4EC-9B got wrong at EC3")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--split", type=Path, default=SPLIT)
    ap.add_argument("--ecreact", type=Path, default=ECREACT)
    ap.add_argument("--preds", type=Path, default=PREDS)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    # ---- recover EC4 -----------------------------------------------------------
    src = pd.read_csv(args.ecreact)
    src["key"] = src["rxn_smiles"].map(lambda s: re.sub(r"\|[\d.\-]+(?=>>)", "", s))
    src["ec3"] = src["ec"].map(ec3)
    lut = src.drop_duplicates(["key", "ec3"]).set_index(["key", "ec3"])["ec"]

    df = pd.read_csv(args.split)
    df["ec3"] = df["ec"].map(ec3)
    df["true_ec4"] = lut.reindex(pd.MultiIndex.from_arrays([df["rxn_smiles"], df["ec3"]])).values
    df["ec_class"] = df["ec3"].str.split(".").str[0]
    usable = df["true_ec4"].notna() & ~df["true_ec4"].astype(str).str.split(".").str[3].eq("-")
    print(f"{args.split}: {len(df)} reactions, {usable.sum()} with a recovered 4-digit EC "
          f"({100 * usable.mean():.1f}%)")
    df = df[usable].copy()

    # ---- attach Gemma4EC-9B's own EC3 prediction -------------------------------
    pr = pd.read_csv(args.preds, sep="\t").drop_duplicates("smiles")
    pred = pr.set_index("smiles")["pred_fragment"]
    df["gemma_pred_ec3"] = df["rxn_smiles"].map(pred).map(lambda x: ec3(x) if pd.notna(x) else None)
    df = df[df["gemma_pred_ec3"].notna()].copy()
    df["gemma_correct_ec3"] = df["gemma_pred_ec3"] == df["ec3"]
    print(f"with a Gemma4EC-9B prediction: {len(df)}  "
          f"(EC3 accuracy {100 * df['gemma_correct_ec3'].mean():.1f}%)")

    # ---- stratified selection --------------------------------------------------
    # Classes are very unevenly sized (EC7 has a handful), so take an even share where the data
    # allows and let the shortfall spill to the larger classes rather than dropping a class.
    def take(pool, k, rng):
        """k rows from pool, spread as evenly as possible over EC classes."""
        if k <= 0 or pool.empty:
            return pool.iloc[0:0]
        picked, remaining = [], k
        groups = {c: g.sample(frac=1, random_state=rng) for c, g in pool.groupby("ec_class")}
        while remaining > 0 and any(len(g) for g in groups.values()):
            live = [c for c, g in groups.items() if len(g)]
            per = max(1, remaining // len(live))
            for c in sorted(live):
                if remaining <= 0:
                    break
                g = groups[c]
                t = min(per, len(g), remaining)
                picked.append(g.iloc[:t])
                groups[c] = g.iloc[t:]
                remaining -= t
        return pd.concat(picked) if picked else pool.iloc[0:0]

    wrong = take(df[~df["gemma_correct_ec3"]], args.n_wrong, args.seed)
    right = take(df[df["gemma_correct_ec3"]], args.n - len(wrong), args.seed + 1)
    sel = pd.concat([wrong, right]).sample(frac=1, random_state=args.seed).reset_index(drop=True)
    sel.insert(0, "rxn_id", range(1, len(sel) + 1))

    out = sel[["rxn_id", "rxn_smiles", "ec", "true_ec4", "ec3", "ec_class",
               "gemma_pred_ec3", "gemma_correct_ec3"]]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)

    print(f"\nselected {len(out)}: {(~out.gemma_correct_ec3).sum()} wrong at EC3, "
          f"{out.gemma_correct_ec3.sum()} correct")
    print("per EC class:")
    tab = out.groupby("ec_class").agg(n=("rxn_id", "size"), wrong=("gemma_correct_ec3", lambda s: (~s).sum()))
    print(tab.to_string())
    print(f"\n-> {args.out}")


if __name__ == "__main__":
    main()
