#!/usr/bin/env python3
"""Put reaction SMILES into the form Gemma4EC was trained on (ECReact) before predicting.

  1. each molecule is written as ECReact writes it (charge state, stereo, spelling), else ionised at pH 7.3;
  2. participants on each side are sorted alphabetically;
  3. one main product is kept: the largest product that is not a common co-product (water, H+, CO2,
     phosphate, NAD(P)(H), ADP, CoA, ...). Use --keep_products to skip this.

Usage: python preprocess_smiles.py reactions.csv reactions_prep.csv      # needs a rxn_smiles column
The input SMILES are kept in rxn_smiles_original.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from rdkit import Chem, RDLogger

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
from preprocess_smiles_to_ecreact import ecreact_forms, map_reaction  # noqa: E402

RDLogger.DisableLog("rdApp.*")

CO_PRODUCTS = [
    "O", "[H+]", "O=C=O", "N", "[NH4+]", "O=O", "OO", "[OH-]", "[Cl-]",
    "O=P([O-])([O-])O", "OP(=O)(O)O", "O=P([O-])([O-])OP(=O)([O-])O", "OP(=O)(O)OP(=O)(O)O",
    "NC(=O)c1ccc[n+]([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)c1",
    "NC(=O)C1=CN([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)C=CC1",
    "NC(=O)c1ccc[n+]([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](OP(=O)([O-])[O-])[C@@H]3O)[C@@H](O)[C@H]2O)c1",
    "NC(=O)C1=CN([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](OP(=O)([O-])[O-])[C@@H]3O)[C@@H](O)[C@H]2O)C=CC1",
    "Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]1O",            # ADP
    "Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])[O-])[C@@H](O)[C@H]1O",                         # AMP
    "CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCS",  # CoA
    "O=c1ccn([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]2O)c(=O)[nH]1",        # UDP
    "Nc1nc2c(ncn2[C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]2O)c(=O)[nH]1",    # GDP
    "Nc1ccn([C@@H]2O[C@H](COP(=O)([O-])[O-])[C@@H](O)[C@H]2O)c(=O)n1",                        # CMP
    "Nc1ncnc2c1ncn2[C@@H]1O[C@H](CSCC[C@H]([NH3+])C(=O)[O-])[C@@H](O)[C@H]1O",                # S-adenosylhomocysteine
]


def skeleton(smi):
    m = Chem.MolFromSmiles(smi)
    try:
        return Chem.MolToInchiKey(m).split("-")[0] if m else None
    except Exception:
        return None


def heavy(smi):
    m = Chem.MolFromSmiles(smi)
    return m.GetNumHeavyAtoms() if m else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--keep_products", action="store_true", help="keep every product")
    args = ap.parse_args()

    d = pd.read_csv(args.input, dtype=str)
    if "rxn_smiles" not in d:
        raise SystemExit("input needs a rxn_smiles column")
    d["rxn_smiles_original"] = d["rxn_smiles"]
    mols = {m for r in d.rxn_smiles for side in r.split(">>") for m in side.split(".") if m}
    mapping, how, fallback = ecreact_forms(mols)
    d["rxn_smiles"] = [map_reaction(r, mapping, how, fallback) for r in d.rxn_smiles]

    if not args.keep_products:
        co = {skeleton(s) for s in CO_PRODUCTS} - {None}

        def main_product(r):
            subs, prods = r.split(">>")
            prods = prods.split(".")
            keep = [p for p in prods if skeleton(p) not in co] or prods
            return f"{subs}>>{max(keep, key=heavy)}"
        d["rxn_smiles"] = d["rxn_smiles"].map(main_product)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(args.output, index=False)
    print(f"{len(d)} reactions -> {args.output}")


if __name__ == "__main__":
    main()
