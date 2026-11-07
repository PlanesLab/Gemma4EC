#!/usr/bin/env python3
"""Rhea500 benchmark: 10 bootstrap samples of 500 Rhea reactions, no retraining.

Top-1 EC3, MCC / precision / recall per EC3 label weighted by support; rows without a valid non-EC7 label dropped.
Writes results/seeds_rhea500/benchmark_{seed,per_class,level}_metrics.csv.
Usage: python results/seeds/rhea500_benchmark.py
"""

import glob
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import matthews_corrcoef, precision_score, recall_score

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(os.environ.get("GEMMA4EC_WORK", "work"))
CAND = WORK / "seeds_rhea500_cand"
OUT = ROOT / "results" / "seeds_rhea500"
API_NAMES = {"gpt-4_1-mini": "GPT", "gemini-3_1-flash-lite": "Gemini"}


def invalid_true(s):
    """True if the label has no complete non-EC7 3-level EC."""
    for ec in s.split(";")[0].split("|"):
        p = ec.strip().split(".")
        if len(p) >= 3 and all(x.isdigit() for x in p[:3]) and p[0] != "7":
            return False
    return True


def parse(s):
    """Set of 3-level ECs in the first ';'-group, unpadded ('2.07.08' -> '2.7.8')."""
    out = set()
    for ec in (s or "").split(";")[0].split("|"):
        p = ec.strip().split(".")
        if len(p) >= 3 and all(x.isdigit() for x in p[:3]):
            out.add(".".join(str(int(x)) for x in p[:3]))
    return out


def from_csv(path, key, val):
    f = WORK / path
    if not f.exists():
        return {}
    d = pd.read_csv(f, dtype=str, keep_default_na=False)
    return dict(zip(d[key], d[val]))


def from_chunks(d, pool, idcol, predcol):
    """SIMMER and SelenzymeRF write one file per chunk, keyed Q<row of the query pool>."""
    out = {}
    for f in sorted(glob.glob(str(d / "chunk_*.csv"))):
        c = pd.read_csv(f, dtype=str, keep_default_na=False)
        for q, p in zip(c[idcol], c[predcol]):
            if str(q).startswith("Q") and int(str(q)[1:]) < len(pool):
                out[pool.rxn_smiles.iloc[int(str(q)[1:])]] = p
    return out


def main():
    cand_pool = pd.read_csv(ROOT / "data/ECReact_seeds_rhea500_cand/api_pool.csv", dtype=str)
    raw_pool = pd.read_csv(ROOT / "data/ECReact_seeds_rhea500_rawpool/api_pool.csv", dtype=str)

    tools = {
        "Theia": from_csv("seeds_rhea500_cand/tools/Theia.csv", "rxn_smiles", "Theia"),
        "BEC-Pred": from_csv("seeds_rhea500_cand/tools/BEC-Pred.csv", "rxn_smiles", "BEC-Pred"),
        "SelenzymeRF": from_chunks(CAND / "tools/selenzyme", cand_pool, "Reaction", "All ECs"),
    }
    for f in glob.glob(str(CAND / "api_pool/predictions_*.tsv")):
        d = pd.read_csv(f, sep="\t", dtype=str, keep_default_na=False)
        tag = Path(f).stem.split("API.")[-1]
        tools[API_NAMES.get(tag, tag)] = dict(zip(d.smiles, d.pred_raw))

    # CLAIRE answers the pooled query file and is keyed by its row index
    pool6 = pd.read_csv(ROOT / "data/ECReact_seeds_rhea500_pool/seed6/test.csv", dtype=str)
    cl = pd.read_csv(WORK / "seeds_rhea500_pool/seed6/claire/CLAIRE.csv", dtype=str, keep_default_na=False)
    cl["i"] = pd.to_numeric(cl.reactionID, errors="coerce")
    claire = {pool6.reaction_id.iloc[int(i)]: p for i, p in zip(cl.i, cl.predictions)
              if pd.notna(i) and int(i) < len(pool6)}

    sim_raw = from_chunks(WORK / "seeds_rhea500_rawpool/tools/simmer", raw_pool,
                          "Reaction name", "SIMMER pred")

    rows, cls_rows, lvl_rows = [], [], []
    for s in range(10):
        base = pd.read_csv(ROOT / f"data/ECReact_seeds_rhea500/seed{s}/test.csv", dtype=str)
        base = base[~base.ec.apply(invalid_true)].reset_index(drop=True)
        true = base.ec.apply(parse)
        cand = pd.read_csv(ROOT / f"data/ECReact_seeds_rhea500_cand/seed{s}/test.csv", dtype=str)
        cand = cand[cand.reaction_id.str.endswith("|main")].copy()
        cand["rid"] = cand.reaction_id.str.split("|", n=1).str[0]
        form = base.reaction_id.map(dict(zip(cand.rid, cand.rxn_smiles)))
        raw = base.reaction_id.map(dict(zip(base.reaction_id, base.rxn_smiles)))

        preds = {}
        for size in ("9b", "2b"):
            f = CAND / f"seed{s}/gemma4ec_{size}_ensemble/selected.csv"
            if f.exists():
                d = pd.read_csv(f, dtype=str, keep_default_na=False)
                preds[f"Gemma4EC-{size.upper()}"] = base.reaction_id.map(
                    dict(zip(d.reaction_id, d.pred_selected)))
        for name, mp in tools.items():
            preds[name] = form.map(mp)
        preds["CLAIRE"] = base.reaction_id.map(claire)
        preds["SIMMER"] = raw.map(sim_raw)

        for m, pr in preds.items():
            pred = pr.fillna("").apply(parse)
            cov = (pred.apply(len) > 0).mean()
            labels = sorted(set().union(*true) | set().union(*pred))
            mlb = MultiLabelBinarizer(classes=labels)
            Y, P = mlb.fit_transform(true), mlb.transform(pred)
            sup = Y.sum(0)
            mcc = np.array([matthews_corrcoef(Y[:, i], P[:, i]) for i in range(len(labels))])
            rows.append({"method": m, "seed": s, "mcc": np.average(mcc, weights=sup),
                         "ppv": np.average(precision_score(Y, P, average=None, zero_division=0), weights=sup),
                         "recall": np.average(recall_score(Y, P, average=None, zero_division=0), weights=sup),
                         "n_test": len(base), "coverage": cov})
            cls = np.array([lab.split(".")[0] for lab in labels])
            for c in sorted(set(cls)):
                idx = (cls == c) & (sup > 0)
                if idx.any():
                    cls_rows.append({"method": m, "seed": s, "ec_class": c, "metric": "mcc",
                                     "value": np.average(mcc[idx], weights=sup[idx]),
                                     "support": int(sup[idx].sum())})
            for level in (1, 2, 3):
                t_l = true.apply(lambda x: {".".join(e.split(".")[:level]) for e in x})
                p_l = pred.apply(lambda x: {".".join(e.split(".")[:level]) for e in x})
                labs = sorted(set().union(*t_l) | set().union(*p_l))
                mlb = MultiLabelBinarizer(classes=labs)
                Yl, Pl = mlb.fit_transform(t_l), mlb.transform(p_l)
                w = Yl.sum(0)
                lvl_rows.append({"method": m, "seed": s, "level": level,
                                 "mcc": np.average([matthews_corrcoef(Yl[:, i], Pl[:, i])
                                                    for i in range(len(labs))], weights=w),
                                 "ppv": np.average(precision_score(Yl, Pl, average=None, zero_division=0), weights=w),
                                 "recall": np.average(recall_score(Yl, Pl, average=None, zero_division=0), weights=w)})

    OUT.mkdir(parents=True, exist_ok=True)
    sm = pd.DataFrame(rows)
    sm.to_csv(OUT / "benchmark_seed_metrics.csv", index=False)
    pd.DataFrame(cls_rows).to_csv(OUT / "benchmark_per_class_metrics.csv", index=False)
    pd.DataFrame(lvl_rows).to_csv(OUT / "benchmark_level_metrics.csv", index=False, float_format="%.4f")
    print(sm.groupby("method").mcc.agg(["mean", "std"]).round(4).sort_values("mean", ascending=False).to_string())
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
