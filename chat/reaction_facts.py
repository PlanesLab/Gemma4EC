#!/usr/bin/env python3
"""
Compute chemical facts for each reaction in attn_out/summary.tsv, so the chat model reasons over
verified facts instead of parsing SMILES itself:

  - molecule names (MetaNetX chem_prop by InChIKey), formulas and cofactor roles
  - atom mapping (RXNMapper) -> bonds broken/formed/changed, H and charge changes,
    functional groups lost/gained, which reactant each product atom comes from
  - known reactions in MetaNetX with the same participants (InChIKey connectivity), with their EC
  - Gemma4EC attention projected onto atoms: share on reaction-centre / cofactor / other atoms

Runs in the rxnmapper env (RXNMapper + RDKit); build_mechanistic_prompts.py --facts reads the output.

Usage:
    $RXNMAPPER_PY chat/reaction_facts.py [--attn_dir attn_out]
"""

import os
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem.rdMolDescriptors import CalcMolFormula

RDLogger.DisableLog('rdApp.*')

REF_DIR = os.environ.get("METANETX_DIR", "data/external/metanetx")   # reac_prop.tsv, chem_prop.tsv

# cofactor / cosubstrate recognition (checked in order; first hit wins)
COFACTORS = [
    ("acyl-CoA (thioester; acyl donor)",       "C(=O)SCC[#7]~[#6](~[#8])CC[#7]~[#6](~[#8])C(O)C(C)(C)COP(~O)(~O)OP(~O)(~O)OC"),
    ("coenzyme A",                              "[SX2H1,SX1-]CC[#7]~[#6](~[#8])CC[#7]~[#6](~[#8])C(O)C(C)(C)COP(~O)(~O)OP(~O)(~O)OC"),
    ("NADP+ (oxidized; hydride acceptor)",      "NC(=O)c1ccc[n+](c1)C1OC(COP(~O)(~O)OP(~O)(~O)OCC2OC(n3cnc4c(N)ncnc43)C(OP(~O)(~O)~O)C2O)C(O)C1O"),
    ("NAD+ (oxidized; hydride acceptor)",       "NC(=O)c1ccc[n+](c1)C1OC(COP(~O)(~O)OP(~O)(~O)OCC2OC(n3cnc4c(N)ncnc43)C(O)C2O)C(O)C1O"),
    ("NADPH (reduced; hydride donor)",          "NC(=O)C1=CN(C=CC1)C1OC(COP(~O)(~O)OP(~O)(~O)OCC2OC(n3cnc4c(N)ncnc43)C(OP(~O)(~O)~O)C2O)C(O)C1O"),
    ("NADH (reduced; hydride donor)",           "NC(=O)C1=CN(C=CC1)C1OC(COP(~O)(~O)OP(~O)(~O)OCC2OC(n3cnc4c(N)ncnc43)C(O)C2O)C(O)C1O"),
    ("FAD",                                     "Cc1cc2nc3c(=O)[nH]c(=O)nc-3n(CC(O)C(O)C(O)COP(~O)(~O)OP(~O)(~O)OC)c2cc1C"),
    ("FADH2 (reduced flavin)",                  "Cc1cc2c(cc1C)N(CC(O)C(O)C(O)COP(~O)(~O)OP(~O)(~O)OC)c1[nH]c(=O)[nH]c(=O)c1N2"),
    ("FMN (oxidized flavin)",                   "Cc1cc2nc3c(=O)[nH]c(=O)nc-3n(CC(O)C(O)C(O)COP(~O)(~O)~O)c2cc1C"),
    ("FMNH2 (reduced flavin; electron donor)",  "Cc1cc2c(cc1C)N(CC(O)C(O)C(O)COP(~O)(~O)~O)c1[nH]c(=O)[nH]c(=O)c1N2"),
    ("ATP",                                     "P(~O)(~O)(~O)OP(~O)(~O)OP(~O)(~O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1O"),
    ("ADP",                                     "P(~O)(~O)(~O)OP(~O)(~O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1O"),
    ("CDP-activated head group (CDP-X; CMP is the leaving group)", "Nc1ccn(C2OC(COP(~O)(~O)OP(~O)(~O)O)C(O)C2O)c(=O)n1"),
    ("CMP",                                     "Nc1ccn(C2OC(COP(~O)(~O)~O)C(O)C2O)c(=O)n1"),
    ("UDP-sugar / UDP",                         "O=c1ccn(C2OC(COP(~O)(~O)OP(~O)(~O)O)C(O)C2O)c(=O)[nH]1"),
    ("S-adenosyl-L-methionine (methyl donor)",  "C[S+](CCC(N)C(=O)O)CC1OC(n2cnc3c(N)ncnc32)C(O)C1O"),
    ("pyridoxal 5'-phosphate",                  "Cc1ncc(COP(~O)(~O)~O)c(C=O)c1O"),
    ("O2 (oxidant)",                            "[OX1]=[OX1]"),
    ("H2O",                                     "[OH2]"),
    ("CO2",                                     "O=C=O"),
    ("H+",                                      "[H+]"),
]
COFACTOR_PATS = [(lab, Chem.MolFromSmarts(s)) for lab, s in COFACTORS]

# lipid classes (checked in order); lets lipids without a database name match BRENDA wording
_PTD = "[#6]C(=O)OCC(OC(=O)[#6])COP(~O)(~O)O"          # phosphatidyl
LIPID_CLASSES = [
    ("cardiolipin",                      f"{_PTD}CC(O)COP(~O)(~O)OCC(OC(=O)[#6])COC(=O)[#6]"),
    ("CDP-diacylglycerol",               f"{_PTD}P(~O)(~O)OCC1OC(n2ccc(N)nc2=O)C(O)C1O"),
    ("phosphatidylglycerol",             f"{_PTD}CC([OX2H])[CH2][OX2H]"),
    ("phosphatidylcholine",              f"{_PTD}CC[N+](C)(C)C"),
    ("phosphatidylserine",               f"{_PTD}CC(N)C(=O)[O,OH]"),
    ("phosphatidylethanolamine",         f"{_PTD}C[CH2][NX3,NX4+;!$(N(C)(C)C)]"),
    ("phosphatidylinositol",             f"{_PTD}C1C(O)C(O)C(O)C(O)C1O"),
    ("phosphatidic acid",                "[#6]C(=O)OCC(OC(=O)[#6])COP(~O)([OX2H,OX1-])[OX2H,OX1-]"),
    ("triacylglycerol",                  "[#6]C(=O)OCC(OC(=O)[#6])COC(=O)[#6]"),
    ("diacylglycerol",                   "[#6]C(=O)OC[CX4](OC(=O)[#6])[CH2][OX2H]"),
    ("diacylglycerol",                   "[#6]C(=O)OC[CX4]([OX2H])[CH2]OC(=O)[#6]"),
    ("monoacylglycerol",                 "[#6]C(=O)OC[CX4]([OX2H])[CH2][OX2H]"),
]
LIPID_PATS = [(lab, Chem.MolFromSmarts(sm)) for lab, sm in LIPID_CLASSES]


def lipid_class(mol):
    if mol is None or mol.GetNumHeavyAtoms() < 20:
        return None
    for lab, pat in LIPID_PATS:
        if mol.HasSubstructMatch(pat):
            return lab
    return None


# functional groups for "lost / gained" summaries (SMARTS)
GROUPS = {
    "primary/secondary alcohol C-OH": "[CX4;!$(C=O)][OX2H]",
    "phenol / aromatic OH":         "c[OX2H]",
    "aldehyde":                     "[CX3H1](=O)[#6]",
    "ketone":                       "[#6][CX3](=O)[#6]",
    "carboxylic acid/carboxylate":  "[CX3](=O)[OX2H1,OX1-]",
    "carboxylic ester":             "[#6][CX3](=O)[OX2][#6]",
    "thioester":                    "[#6][CX3](=O)[SX2]",
    "amide":                        "[CX3](=O)[NX3]",
    "primary amine":                "[NX3H2,NX4H3+][CX4]",
    "secondary amine":              "[NX3H1,NX4H2+]([CX4])[CX4]",
    "C=C (non-aromatic)":           "[CX3]=[CX3]",
    "phosphate ester / phosphodiester": "[#6]O[PX4](=O)",
    "phosphoanhydride":             "P(=O)OP(=O)",
    "epoxide":                      "C1OC1",
}
GROUP_PATS = {k: Chem.MolFromSmarts(v) for k, v in GROUPS.items()}
TRIVIAL = {"H+", "H2O"}
ATOM_RE = re.compile(r"(\[[^\]]+\]|Br|Cl|[BCNOPSFIbcnops])")   # SMILES atom tokens, in RDKit atom order


def normalize_ec3(ec):
    parts = str(ec).strip().split('.')
    try:
        return '.'.join(str(int(p)) for p in parts[:3]) if len(parts) >= 3 else None
    except ValueError:
        return None


# ── molecules ─────────────────────────────────────────────────────────────────

def split_rxn(smiles):
    """[(label, smiles, char_start)] for reactants then products."""
    out, pos = [], 0
    left, _, right = smiles.partition('>>')
    for side, label in ((left, "Reactant"), (right, "Product")):
        for k, mol in enumerate(side.split('.'), 1):
            out.append((f"{label} {k}", mol, pos))
            pos += len(mol) + 1
        pos += 1
    return out


def cofactor_role(mol):
    for lab, pat in COFACTOR_PATS:
        if pat is not None and mol.HasSubstructMatch(pat):
            if lab in ("H2O", "CO2", "H+") and mol.GetNumHeavyAtoms() > 3:
                continue
            if lab == "O2 (oxidant)" and mol.GetNumHeavyAtoms() != 2:
                continue
            return lab
    return None


GENERIC_RE = re.compile(r"alpha,omega|^an? |\bR-|-R\b|\(n\)|\bgeneric\b", re.I)


def load_names(keys: set[str], ref_dir: Path):
    """(chem_prop table, {block: [(InChIKey, name)]}) for the connectivity blocks of the keys we need."""
    blocks = {k[:14] for k in keys}
    cp = pd.read_csv(ref_dir / "chem_prop.tsv", sep='\t', comment='#', header=None, dtype=str,
                     usecols=[0, 1, 7], names=["id", "name", "ikey"]).dropna(subset=["id", "name"])
    cand = defaultdict(list)
    for mid, name, ik in cp.itertuples(index=False):
        if isinstance(ik, str) and ik[:14] in blocks:
            cand[ik[:14]].append((ik, name))
    return cp, cand


def pick_name(ik: str, cand: dict):
    """Best MetaNetX name for an InChIKey: same full key > same stereo block > non-generic > shorter."""
    opts = cand.get(ik[:14], [])
    if not opts:
        return None, "none"
    if ik[:14] == "GPRLSGONYQIRFK":
        return "H+", "exact"
    k, name = min(opts, key=lambda o: (bool(GENERIC_RE.search(o[1])), o[0] != ik, o[0][15:25] != ik[15:25], len(o[1])))
    return name, ("exact" if k == ik or k[:-1] == ik[:-1] else "same stereo, different protonation" if k[15:25] == ik[15:25]
                  else "same connectivity only; stereo or protonation differs")


# ── known reactions with the same participants ────────────────────────────────

def load_reference(ref_dir: Path, cp: pd.DataFrame):
    """[(MNX id, EC string, left keys, right keys, left names, right names)] for MetaNetX reactions with an EC4."""
    has_key = cp["ikey"].notna()
    mnx2b = dict(zip(cp["id"][has_key], cp["ikey"][has_key].str[:14]))
    mnx2b["WATER"] = "XLYOFNOQVPJJNP"
    mnx2name = dict(zip(cp["id"], cp["name"]))
    prop = pd.read_csv(ref_dir / "reac_prop.tsv", sep='\t', comment='#', header=None, dtype=str, usecols=[0, 1, 3]).dropna()
    ref = []
    for rid, eq, ecs in prop.itertuples(index=False):
        if not any(e.count('.') == 3 for e in ecs.split(';')):
            continue
        sides = [re.findall(r'(MNXM\w+|WATER)', side) for side in eq.split(' = ', 1)]
        if len(sides) != 2:
            continue
        keys = [{mnx2b.get(m) for m in side} - {None} - TRIVIAL_KEYS for side in sides]
        names = [[mnx2name.get(m, m) for m in side if mnx2b.get(m) not in TRIVIAL_KEYS] for side in sides]
        ref.append((rid, ecs, keys[0], keys[1], names[0], names[1]))
    return ref


TRIVIAL_KEYS = {"GPRLSGONYQIRFK", "XLYOFNOQVPJJNP"}   # H+, H2O


def known_reactions(query_sides, ref, substrate_keys, top=4):
    """MetaNetX reactions whose participant connectivity keys best match the query (either direction);
    at least one shared participant must be a substrate/product, not only cofactors."""
    qL, qR = (set(s) - TRIVIAL_KEYS for s in query_sides)
    hits = []
    for rid, ecs, L, R, nL, nR in ref:
        for a, b, flip in ((L, R, False), (R, L, True)):
            shared = (qL & a) | (qR & b)
            if not shared & substrate_keys:
                continue
            inter = len(qL & a) + len(qR & b)
            score = inter / (len(qL | a) + len(qR | b))
            if score >= 0.5:
                names = (nR, nL) if flip else (nL, nR)
                hits.append((score, rid, ecs, ' + '.join(names[0]) + ' = ' + ' + '.join(names[1])))
    hits.sort(key=lambda h: -h[0])
    seen, out = set(), []
    for score, rid, ecs, eqn in hits:
        ec4 = sorted({e for e in ecs.split(';') if e.count('.') == 3})
        key = (eqn, tuple(ec4))
        if key in seen or not ec4:
            continue
        seen.add(key)
        out.append({"mnx": rid, "match": round(score, 2), "ec": ec4, "equation": eqn})
        if len(out) >= top:
            break
    return out


# ── atom mapping and reaction centre ──────────────────────────────────────────

def atom_desc(a):
    h = a.GetTotalNumHs()
    s = a.GetSymbol() + (f"H{h}" if h > 1 else "H" if h == 1 else "")
    return s + ("+" if a.GetFormalCharge() > 0 else "-" if a.GetFormalCharge() < 0 else "")


BOND_NAME = {1.0: "single", 1.5: "aromatic", 2.0: "double", 3.0: "triple"}


def analyse_mapping(mapped_rxn, mols):
    """Bond/H/charge changes between mapped reactants and products; atoms keyed (molecule label, atom idx)."""
    left, _, right = mapped_rxn.partition('>>')
    sides = {"Reactant": [Chem.MolFromSmiles(s) for s in left.split('.')],
             "Product": [Chem.MolFromSmiles(s) for s in right.split('.')]}
    nxt = 100000
    for mm in sides["Reactant"]:        # reactant atoms that reach no product: give them private ids
        for a in mm.GetAtoms():
            if not a.GetAtomMapNum():
                a.SetAtomMapNum(nxt)
                nxt += 1
    # match each mapped molecule to an original molecule of the same side (rxnmapper may reorder)
    orig = {lab: Chem.MolFromSmiles(s) for lab, s, _ in mols}
    loc = {}          # (side, map number) -> (orig label, orig atom idx)
    used = set()
    for side, mlist in sides.items():
        for mm in mlist:
            plain = Chem.Mol(mm)
            for a in plain.GetAtoms():
                a.SetAtomMapNum(0)
            can = Chem.MolToSmiles(plain)
            for lab, om in orig.items():
                if lab.startswith(side) and lab not in used and om is not None and Chem.MolToSmiles(om) == can:
                    used.add(lab)
                    match = om.GetSubstructMatch(plain)
                    for i, a in enumerate(mm.GetAtoms()):
                        if a.GetAtomMapNum() and match:
                            loc[(side, a.GetAtomMapNum())] = (lab, match[i])
                    break

    def bonds(side):
        b = {}
        for mm in sides[side]:
            for bd in mm.GetBonds():
                i, j = bd.GetBeginAtom().GetAtomMapNum(), bd.GetEndAtom().GetAtomMapNum()
                if i and j:
                    b[frozenset((i, j))] = bd.GetBondTypeAsDouble()
        return b

    def atoms(side):
        return {a.GetAtomMapNum(): a for mm in sides[side] for a in mm.GetAtoms() if a.GetAtomMapNum()}

    rb, pb, ra, pa = bonds("Reactant"), bonds("Product"), atoms("Reactant"), atoms("Product")
    in_prod = set(pa)
    changes, centre = [], set()

    def name(m):
        lab, idx = loc.get(("Reactant", m), ("?", -1))
        return f"{ra[m].GetSymbol()}{m} ({lab}, {atom_desc(ra[m])})"

    for key in sorted(set(rb) | set(pb), key=lambda k: sorted(k)):
        i, j = sorted(key)
        if i not in in_prod or j not in in_prod:
            continue      # bond to atoms that leave with an omitted co-product: reported separately
        before, after = rb.get(key), pb.get(key)
        if before == after:
            continue
        if before is None:
            changes.append(f"FORMED {BOND_NAME.get(after, after)} bond {name(i)} – {name(j)}")
        elif after is None:
            changes.append(f"BROKEN {BOND_NAME.get(before, before)} bond {name(i)} – {name(j)}")
        elif not (before == 1.5 or after == 1.5):
            changes.append(f"CHANGED bond {name(i)} – {name(j)}: {BOND_NAME[before]} → {BOND_NAME[after]}")
        else:
            continue
        centre |= {i, j}
    # bonds from product-side atoms to atoms that do not appear in any product (leaving groups)
    for key, order in rb.items():
        i, j = sorted(key)
        if (i in in_prod) != (j in in_prod):
            keep, gone = (i, j) if i in in_prod else (j, i)
            changes.append(f"BROKEN {BOND_NAME.get(order, order)} bond {name(keep)} – {name(gone)} "
                           f"(the {ra[gone].GetSymbol()} side leaves with a co-product not listed in the record)")
            centre.add(keep)
    for m in sorted(in_prod & set(ra)):
        dh = pa[m].GetTotalNumHs() - ra[m].GetTotalNumHs()
        dq = pa[m].GetFormalCharge() - ra[m].GetFormalCharge()
        if dh or dq:
            centre.add(m)
            parts = ([f"{'gains' if dh > 0 else 'loses'} {abs(dh)} H"] if dh else []) + \
                    ([f"charge {ra[m].GetFormalCharge():+d} → {pa[m].GetFormalCharge():+d}"] if dq else [])
            changes.append(f"{name(m)} {' and '.join(parts)}")

    # provenance of product atoms, and reactant atoms that do not reach any product
    prov = defaultdict(Counter)
    for m in pa:
        prov[loc.get(("Product", m), ("?", 0))[0]][loc.get(("Reactant", m), ("unmapped", 0))[0]] += 1
    gone = Counter(loc.get(("Reactant", m), ("?", 0))[0] for m in ra if m not in in_prod)
    unmapped_prod = sum(1 for mm in sides["Product"] for a in mm.GetAtoms() if not a.GetAtomMapNum())
    centre_atoms = {loc[("Reactant", m)] for m in centre if ("Reactant", m) in loc} | \
                   {loc[("Product", m)] for m in centre if ("Product", m) in loc}
    return changes, prov, gone, unmapped_prod, centre_atoms


def mcs_map(smiles, roles, order=-1, exact_bonds=False, timeout=20):
    """Greedy MCS atom mapping: for each product (largest first), take the largest common substructure with
    each reactant in turn (largest first), masking atoms already used on both sides. Leftover product O atoms
    are assigned to O2/H2O oxygens. Robust where RXNMapper scrambles long repetitive chains (lipids).
    Redox cofactors (NAD(P), FAD, FMN) transfer hydride/electrons, not heavy atoms, so they are not matched.
    order=-1: largest reactant first; +1: smallest first."""
    from rdkit.Chem import rdFMCS
    left, _, right = smiles.replace('->>', '>>').partition('>>')
    R = [Chem.MolFromSmiles(x) for x in left.split('.')]
    P = [Chem.MolFromSmiles(x) for x in right.split('.')]
    used_r = [set() for _ in R]
    used_p = [set() for _ in P]
    nmap = 1

    def masked(m, used):
        rw = Chem.RWMol(m)
        for i in used:
            rw.GetAtomWithIdx(i).SetAtomicNum(0)
        return rw.GetMol()

    for pi in sorted(range(len(P)), key=lambda i: -P[i].GetNumAtoms()):
        for ri in sorted(range(len(R)), key=lambda i: order * R[i].GetNumAtoms()):
            if roles[ri] and re.search(r"NAD|FAD|FMN", roles[ri]):
                continue
            while True:
                rm, pm = masked(R[ri], used_r[ri]), masked(P[pi], used_p[pi])
                res = rdFMCS.FindMCS([rm, pm], atomCompare=rdFMCS.AtomCompare.CompareElements,
                                     bondCompare=rdFMCS.BondCompare.CompareOrder if exact_bonds else rdFMCS.BondCompare.CompareAny,
                                     ringMatchesRingOnly=True,
                                     timeout=timeout)
                if res.numAtoms < 2:
                    break
                q = Chem.MolFromSmarts(res.smartsString)
                mr = next((m for m in rm.GetSubstructMatches(q, uniquify=False, maxMatches=200)
                           if not used_r[ri] & set(m)), None)
                mp = next((m for m in pm.GetSubstructMatches(q, uniquify=False, maxMatches=200)
                           if not used_p[pi] & set(m)), None)
                if mr is None or mp is None:
                    break
                for a, b in zip(mr, mp):
                    R[ri].GetAtomWithIdx(a).SetAtomMapNum(nmap)
                    P[pi].GetAtomWithIdx(b).SetAtomMapNum(nmap)
                    nmap += 1
                used_r[ri] |= set(mr)
                used_p[pi] |= set(mp)
                if res.numAtoms < 4:      # avoid scattering tiny fragments
                    break
        # leftover product oxygens: from O2 / H2O if present
        for b in range(P[pi].GetNumAtoms()):
            if b in used_p[pi] or P[pi].GetAtomWithIdx(b).GetSymbol() != 'O':
                continue
            for ri, r in enumerate(R):
                if r.GetNumHeavyAtoms() <= 2 and all(a.GetSymbol() == 'O' for a in r.GetAtoms()):
                    free = [a for a in range(r.GetNumAtoms()) if a not in used_r[ri]]
                    if free:
                        r.GetAtomWithIdx(free[0]).SetAtomMapNum(nmap)
                        P[pi].GetAtomWithIdx(b).SetAtomMapNum(nmap)
                        nmap += 1
                        used_r[ri].add(free[0])
                        used_p[pi].add(b)
                        break
    return '.'.join(Chem.MolToSmiles(m, canonical=False) for m in R) + '>>' + \
           '.'.join(Chem.MolToSmiles(m, canonical=False) for m in P)


def oxygen_from_o2(mapped_rxn, roles):
    """Oxygenases: a product O mapped from a flavin/nicotinamide cofactor is reassigned to O2 when O2 is a reactant
    (RXNMapper sometimes takes the hydroxyl O from FMNH2/NADPH)."""
    left, _, right = mapped_rxn.partition('>>')
    R = [Chem.MolFromSmiles(x) for x in left.split('.')]
    P = [Chem.MolFromSmiles(x) for x in right.split('.')]
    o2 = [i for i, r in enumerate(roles) if r and r.startswith("O2")]
    if not o2 or len(R) != len(roles):
        return mapped_rxn
    pmaps = {a.GetAtomMapNum() for m in P for a in m.GetAtoms() if a.GetAtomMapNum()}
    free = [a for i in o2 for a in R[i].GetAtoms() if a.GetAtomMapNum() not in pmaps]
    for i, r in enumerate(roles):
        if r and re.search(r"FMN|FAD|NAD", r):
            for a in R[i].GetAtoms():
                if a.GetSymbol() == 'O' and a.GetAtomMapNum() in pmaps and free:
                    f = free.pop(0)
                    f.SetAtomMapNum(a.GetAtomMapNum())
                    a.SetAtomMapNum(0)
    # leftover product heteroatoms (e.g. the NH2 transferred by an aminotransferase, whose co-product is omitted
    # from the record): take an unused atom of the same element from a reactant that is not a redox cofactor
    for pi, pm in enumerate(P):
        for b in range(pm.GetNumAtoms()):
            sym = pm.GetAtomWithIdx(b).GetSymbol()
            if b in used_p[pi] or sym not in ("N", "O", "S"):
                continue
            for ri, r in enumerate(R):
                if roles[ri] and re.search(r"NAD|FAD|FMN", roles[ri]):
                    continue
                free = [a for a in range(r.GetNumAtoms()) if a not in used_r[ri] and r.GetAtomWithIdx(a).GetSymbol() == sym]
                if free:
                    r.GetAtomWithIdx(free[0]).SetAtomMapNum(nmap)
                    pm.GetAtomWithIdx(b).SetAtomMapNum(nmap)
                    nmap += 1
                    used_r[ri].add(free[0])
                    used_p[pi].add(b)
                    break
    return '.'.join(Chem.MolToSmiles(m, canonical=False) for m in R) + '>>' + \
           '.'.join(Chem.MolToSmiles(m, canonical=False) for m in P)


def n_edits(changes):
    return sum(c.startswith(("FORMED", "BROKEN", "CHANGED")) for c in changes)


def refine_mapping(mapped_rxn, mols, max_rounds=3):
    """Local search: swap the source of a mapped heteroatom with a same-element reactant atom that reaches no
    product (e.g. which O of a phosphoanhydride vs the attacking OH ends up in the product) when that lowers
    the number of bond edits."""
    def cost(m):
        return n_edits(analyse_mapping(m, mols)[0])

    best, best_cost = mapped_rxn, cost(mapped_rxn)
    for _ in range(max_rounds):
        left, _, right = best.partition('>>')
        R = [Chem.MolFromSmiles(x) for x in left.split('.')]
        pmaps = {a.GetAtomMapNum() for x in right.split('.') for a in Chem.MolFromSmiles(x).GetAtoms()}
        mapped = [(ri, a.GetIdx()) for ri, r in enumerate(R) for a in r.GetAtoms()
                  if a.GetAtomMapNum() in pmaps and a.GetAtomMapNum() and a.GetSymbol() in "ONSP"]
        free = [(ri, a.GetIdx()) for ri, r in enumerate(R) for a in r.GetAtoms()
                if a.GetAtomMapNum() not in pmaps and a.GetSymbol() in "ONSP"]
        improved = False
        for (ra_, ia) in mapped:
            for (rb, ib) in free:
                A, B = R[ra_].GetAtomWithIdx(ia), R[rb].GetAtomWithIdx(ib)
                if A.GetSymbol() != B.GetSymbol():
                    continue
                ma, mb = A.GetAtomMapNum(), B.GetAtomMapNum()
                A.SetAtomMapNum(mb); B.SetAtomMapNum(ma)
                cand = '.'.join(Chem.MolToSmiles(r, canonical=False) for r in R) + '>>' + right
                c = cost(cand)
                if c < best_cost:
                    best, best_cost, improved = cand, c, True
                    break
                A.SetAtomMapNum(ma); B.SetAtomMapNum(mb)
            if improved:
                break
        if not improved:
            break
    return best


def groups_of(mol):
    return Counter({k: len(mol.GetSubstructMatches(p)) for k, p in GROUP_PATS.items() if mol.HasSubstructMatch(p)})


# ── attention on atoms ────────────────────────────────────────────────────────

def atom_char_spans(mols):
    """{(label, atom idx): (char start, char end)} in the full reaction SMILES."""
    spans = {}
    for lab, smi, start in mols:
        for k, m in enumerate(ATOM_RE.finditer(smi)):
            spans[(lab, k)] = (start + m.start(), start + m.end())
    return spans


def attention_by_atom(tokens_spans, weights, mols):
    aspan = atom_char_spans(mols)
    att = defaultdict(float)
    other = 0.0
    for (s, e), w in zip(tokens_spans, weights):
        hit = [k for k, (a, b) in aspan.items() if a < e and b > s]
        if hit:
            for k in hit:
                att[k] += w / len(hit)
        else:
            other += w          # separators, bonds, ring digits, branches
    return att, other


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--attn_dir", default="attn_out")
    ap.add_argument("--ref_dir", default=REF_DIR)
    ap.add_argument("--out_file", default=None, help="default: <attn_dir>/reaction_facts.json")
    args = ap.parse_args()
    attn_dir, ref_dir = Path(args.attn_dir), Path(args.ref_dir)
    out_file = Path(args.out_file or attn_dir / "reaction_facts.json")

    df = pd.read_csv(attn_dir / "summary.tsv", sep='\t')
    all_mols = {lab_smi[1] for s in df['rxn_smiles'] for lab_smi in split_rxn(s)}
    keys = {Chem.MolToInchiKey(m) for m in map(Chem.MolFromSmiles, all_mols) if m is not None}
    print("Loading MetaNetX names …", flush=True)
    cp, cand = load_names(keys, ref_dir)
    ref = load_reference(ref_dir, cp)
    print(f"  {len(ref)} MetaNetX reactions with an EC4", flush=True)

    from rxnmapper import RXNMapper
    mapper = RXNMapper()

    facts = []
    for _, row in df.iterrows():
        rxn_id, smiles = int(row['reaction']), row['rxn_smiles']
        mols = split_rxn(smiles)
        mol_info, sides, substrate_keys = [], ([], []), set()
        for lab, smi, _ in mols:
            m = Chem.MolFromSmiles(smi)
            ik = Chem.MolToInchiKey(m) if m is not None else ""
            name, name_match = pick_name(ik, cand)
            lclass = lipid_class(m)
            role = cofactor_role(m) if m is not None else None
            mol_info.append({"label": lab, "smiles": smi, "name": name or (f"a {lclass}" if lclass else "unknown (not in MetaNetX)"),
                             "name_match": name_match, "class": lclass,
                             "formula": CalcMolFormula(m) if m is not None else "?",
                             "heavy_atoms": m.GetNumHeavyAtoms() if m is not None else 0, "role": role,
                             "groups": dict(groups_of(m)) if m is not None else {}})
            sides[lab.startswith("Product")].append(ik[:14])
            if not role and m is not None and m.GetNumHeavyAtoms() >= 6:   # not phosphate, PPi, NH3, CO2 …
                substrate_keys.add(ik[:14])

        # two mappings (RXNMapper, greedy MCS); keep the one with fewer bond edits (minimal chemical distance)
        cands = []
        try:
            mapped = mapper.get_attention_guided_atom_maps([smiles.replace('->>', '>>')], canonicalize_rxns=False)[0]
            cands.append(("RXNMapper", round(float(mapped["confidence"]), 3),
                          oxygen_from_o2(mapped["mapped_rxn"], [mi["role"] for mi in mol_info if mi["label"].startswith("Reactant")])))
        except Exception as ex:      # e.g. reaction too long for RXNMapper (512 tokens)
            print(f"  RXNMapper failed: {str(ex)[:120]}")
        r_roles = [mi["role"] for mi in mol_info if mi["label"].startswith("Reactant")]
        for order, exact in ((-1, False), (1, False), (-1, True), (1, True)):
            try:
                cands.append(("MCS", None, mcs_map(smiles, r_roles, order, exact)))
            except Exception as ex:
                print(f"  MCS mapping failed: {str(ex)[:120]}")
        results = []
        for method, conf, mrxn in cands:
            try:
                mrxn = refine_mapping(mrxn, mols)
                results.append((method, conf, mrxn, analyse_mapping(mrxn, mols)))
            except Exception as ex:
                print(f"  {method} analysis failed: {str(ex)[:120]}")
        if results:
            # fewest bond edits, but every product atom must come from somewhere: unmapped atoms cost 3 edits each
            results.sort(key=lambda r: (n_edits(r[3][0]) + 3 * r[3][3], r[0] != "RXNMapper"))
            method, conf, mrxn, (changes, prov, gone, unmapped_prod, centre_atoms) = results[0]
            mapping = {"method": method, "confidence": conf, "changes": changes,
                       "bond_edits": {r[0]: min(n_edits(x[3][0]) for x in results if x[0] == r[0]) for r in results},
                       "product_atom_sources": {p: dict(c) for p, c in prov.items()},
                       "reactant_atoms_not_in_products": dict(gone), "unmapped_product_atoms": unmapped_prod,
                       "mapped_rxn": mrxn}
        else:
            mapping, centre_atoms = {"error": "no atom mapping"}, set()

        # attention projected on atoms
        npz = attn_dir / f"rxn{rxn_id:02d}_smiles_attn.npz"
        attn = {}
        if npz.exists():
            d = np.load(npz, allow_pickle=True)
            att, other = attention_by_atom(d["char_spans"], d["weights"].astype(float), mols)
            role_of = {mi["label"]: mi["role"] for mi in mol_info}
            buckets = Counter()
            for k, w in att.items():
                if k in centre_atoms:
                    buckets["reaction-centre atoms"] += w
                elif role_of[k[0]] and role_of[k[0]] not in TRIVIAL:
                    buckets["cofactor/cosubstrate atoms (outside the centre)"] += w
                else:
                    buckets["other substrate/product atoms"] += w
            buckets["separators, bonds, ring/branch symbols"] = other
            n_atoms = sum(mi["heavy_atoms"] for mi in mol_info)
            top = sorted(att.items(), key=lambda kv: -kv[1])[:8]
            orig = {lab: Chem.MolFromSmiles(s) for lab, s, _ in mols}
            attn = {
                "share": {k: round(v, 3) for k, v in buckets.items()},
                "centre_atom_fraction": round(len(centre_atoms) / max(n_atoms, 1), 3),
                "top_atoms": [{"atom": f"{orig[lab].GetAtomWithIdx(i).GetSymbol()} #{i + 1} of {lab}",
                               "env": atom_desc(orig[lab].GetAtomWithIdx(i)),
                               "in_centre": (lab, i) in centre_atoms, "weight": round(w, 3)} for (lab, i), w in top],
            }

        facts.append({"rxn_id": rxn_id, "rxn_smiles": smiles, "molecules": mol_info, "mapping": mapping,
                      "known_reactions": known_reactions(sides, ref, substrate_keys), "attention_atoms": attn})
        print(f"rxn{rxn_id:02d}: {mapping.get('method')} {mapping.get('bond_edits')} edits, "
              f"{len(facts[-1]['known_reactions'])} known reactions, "
              f"names: {[mi['name'][:30] for mi in mol_info]}", flush=True)

    out_file.write_text(json.dumps(facts, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Saved → {out_file}")


if __name__ == "__main__":
    main()
