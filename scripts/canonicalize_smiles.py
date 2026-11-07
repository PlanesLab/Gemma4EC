#!/usr/bin/env python3
"""RDKit-canonical reaction SMILES. canon_rxn() is the shared helper used by the split,
API-pool, Selenzyme and BEC-Pred scripts to key reactions consistently."""

from rdkit import Chem, RDLogger

RDLogger.DisableLog("rdApp.*")


def canon_mol(smi: str) -> str:
    try:
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            return Chem.MolToSmiles(mol)
    except Exception:
        pass
    return smi


def canon_rxn(rxn_smi: str) -> str:
    if not isinstance(rxn_smi, str) or not rxn_smi.strip():
        return rxn_smi
    parts = rxn_smi.split(">")
    if len(parts) != 3:
        return rxn_smi
    return ">".join(
        ".".join(canon_mol(m) for m in part.split(".")) if part else ""
        for part in parts
    )
