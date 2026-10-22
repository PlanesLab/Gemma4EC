#!/usr/bin/env python3
"""
Mechanism references for the chat pipeline: M-CSA entries (curated, EBI) and hand-written class cards.

Selection for a reaction and its chosen EC number (best first):
  1. M-CSA entry with exactly that EC number
  2. a class card whose rules match (EC sub-subclass, cofactor roles, substrate pattern, enzyme reaction text)
  3. an M-CSA entry of the same EC sub-subclass that uses the same cofactor (labelled as an analogous enzyme)

Cards are deliberately general (textbook level) so they hold for every enzyme the rule matches.
"""

import json
import re
from pathlib import Path

CARDS = [
    {
        "id": "nadp_alcohol_dehydrogenase",
        "title": "NAD(P)+-dependent alcohol dehydrogenase (oxidation of a C-OH to C=O)",
        "ec3": ["1.1.1"], "cofactor": r"NAD", "smarts": "[CX4;!$(C=O)][OX2H]",
        "text": ("Alcohol dehydrogenases transfer a hydride from the carbon bearing the hydroxyl group (the carbinol C-H) "
                 "to C4 of the nicotinamide ring of NAD(P)+, giving the carbonyl product and NAD(P)H; the hydroxyl proton "
                 "is removed by a general base at the same time. In short-chain dehydrogenases/reductases (SDR) the base is "
                 "a Tyr (with Lys and Ser in the catalytic triad); in medium-chain (MDR) enzymes a catalytic Zn2+ binds the "
                 "alcohol oxygen and lowers its pKa. No covalent intermediate is formed and the reaction is reversible; "
                 "the cofactor usually binds first (ordered mechanism)."),
    },
    {
        "id": "gmc_flavin_oxidase",
        "title": "Flavin (FAD) alcohol oxidase, GMC family (alcohol + O2 -> aldehyde + H2O2)",
        "ec3": ["1.1.3"], "cofactor": r"O2", "smarts": "[CX4;!$(C=O)][OX2H]",
        "text": ("These oxidases (glucose-methanol-choline family, e.g. aryl-alcohol oxidase, glucose oxidase) carry a "
                 "tightly bound FAD. Reductive half-reaction: a catalytic His acts as general base on the substrate "
                 "hydroxyl while the hydride on the alpha-carbon is transferred to flavin N5, giving the aldehyde and "
                 "reduced FADH-. Oxidative half-reaction: FADH- reduces O2 (via a flavin semiquinone/superoxide pair) "
                 "to hydrogen peroxide, regenerating FAD. O2 is therefore the electron acceptor; its oxygen atoms end up "
                 "in H2O2, not in the product."),
    },
    {
        "id": "p450_monooxygenase",
        "title": "Cytochrome P450 monooxygenase (heme-thiolate; R-H + O2 + 2e- -> R-OH + H2O)",
        "ec3": ["1.14.14"], "cofactor": r"O2", "enzyme_text": r"hemoprotein|P450|unspecific monooxygenase|steroid|CYP",
        "text": ("P450s carry a heme iron ligated by a Cys thiolate. The two electrons come from NADPH via NADPH-cytochrome "
                 "P450 reductase, a FAD/FMN flavoprotein (written in some databases as '[reduced NADPH-hemoprotein "
                 "reductase]', and in some reaction records as FMNH2 or NADPH). Cycle: substrate binds, Fe3+ is reduced "
                 "to Fe2+, O2 binds, a second electron and two protons cleave the O-O bond releasing water and forming "
                 "Compound I (Fe(IV)=O porphyrin radical cation). For aliphatic C-H hydroxylation Compound I abstracts a "
                 "hydrogen atom and the carbon radical recombines with the Fe-OH ('oxygen rebound'). For aromatic "
                 "hydroxylation Compound I adds to the ring (sigma-complex/arene oxide), followed by an NIH shift and "
                 "rearomatisation to the phenol. One O atom of O2 goes into the product, the other into water."),
    },
    {
        "id": "two_component_flavin_monooxygenase",
        "title": "Two-component flavin monooxygenase (FMNH2/FADH2 + O2, C4a-hydroperoxyflavin)",
        "ec3": ["1.14.14"], "cofactor": r"FMNH2|FADH2", "enzyme_text": r"FMNH2|FADH2|reduced flavin",
        "text": ("A separate NAD(P)H:flavin reductase supplies reduced flavin (FMNH2 or FADH2), which the monooxygenase "
                 "binds and reacts with O2 to form a C4a-(hydro)peroxyflavin. The distal oxygen is transferred to the "
                 "substrate (electrophilic hydroxylation/epoxidation by the hydroperoxide, or nucleophilic attack by "
                 "the peroxide anion in Baeyer-Villiger-type reactions). The C4a-hydroxyflavin then loses water, giving "
                 "oxidised FMN/FAD. One O atom of O2 goes into the product, the other into water."),
    },
    {
        "id": "plp_amino_acid_decarboxylase",
        "title": "PLP-dependent amino-acid decarboxylase (R-CH(NH2)-COOH -> R-CH2-NH2 + CO2)",
        "ec3": ["4.1.1"], "smarts": "[NX3,NX4+][CX4][CX3](=O)[OX2H,OX1-]",
        "text": ("Pyridoxal 5'-phosphate (PLP) is bound to an active-site Lys as an internal aldimine. The substrate "
                 "alpha-amino group displaces the Lys (transaldimination) to form an external aldimine. The bond between "
                 "C-alpha and the carboxylate, held perpendicular to the pyridine ring, breaks and CO2 leaves; the "
                 "negative charge is delocalised into the protonated pyridine ring (quinonoid intermediate, PLP acts as "
                 "an electron sink). Protonation of C-alpha and a second transaldimination by the Lys release the amine "
                 "product and regenerate the internal aldimine. PLP is not written in the reaction because it is "
                 "regenerated; CO2 is often omitted from records."),
    },
    {
        "id": "acyl_coa_o_acyltransferase",
        "title": "Acyl-CoA:alcohol O-acyltransferase (acyl-CoA + R-OH -> ester + CoA)",
        "ec3": ["2.3.1"], "cofactor": r"acyl-CoA", "bond": r"FORMED single bond (O\d+ .*OH.* C\d+|C\d+ .* O\d+ .*OH)",
        "text": ("The acceptor hydroxyl group attacks the thioester carbonyl carbon of the acyl-CoA. A conserved active-site "
                 "His (e.g. in DGAT1 and other MBOAT-family acyltransferases, and in DGAT2/LPAAT-type enzymes) acts as "
                 "general base, deprotonating the hydroxyl. The tetrahedral oxyanion intermediate collapses, expelling "
                 "the CoA thiolate (protonated to CoA-SH) and forming the ester bond. The acyl group is transferred "
                 "directly from CoA to the acceptor; CoA is the leaving group and is usually omitted from records."),
    },
    {
        "id": "acyl_coa_n_acyltransferase",
        "title": "Acyl-CoA:amine N-acyltransferase (acyl-CoA + R-NH2 -> amide + CoA)",
        "ec3": ["2.3.1"], "cofactor": r"acyl-CoA", "bond": r"FORMED single bond .*N\d+",
        "text": ("In GNAT-family and glycine N-acyltransferases, acyl-CoA and the acceptor bind to form a ternary complex. "
                 "The deprotonated acceptor amine (a Glu/His or a water network acts as general base) attacks the "
                 "thioester carbonyl directly; the tetrahedral intermediate collapses to the amide and the CoA thiolate, "
                 "which is protonated by a general acid (often a Tyr). No acyl-enzyme intermediate is formed. CoA is the "
                 "leaving group."),
    },
    {
        "id": "cdp_alcohol_phosphotransferase",
        "title": "CDP-alcohol phosphotransferase (CDP-X + R-OH -> R-O-P(O2)-O-X + CMP)",
        "ec3": ["2.7.8"], "cofactor": r"CDP",
        "text": ("CDP-alcohol phosphotransferases (CDP-AP family: ethanolamine/choline phosphotransferases, "
                 "phosphatidylinositol/-serine/-glycerophosphate synthases, eukaryotic cardiolipin synthase) are "
                 "membrane enzymes with a conserved Asp-rich motif (D-G-x2-A-R-x8-G-x3-D-x3-D) that binds Mg2+ ions. A "
                 "conserved Asp acts as general base and deprotonates the acceptor hydroxyl, which attacks the phosphorus "
                 "atom that is NOT attached to the cytidine nucleoside (the distal phosphate of CDP-X) in an in-line "
                 "SN2-type substitution; the Mg2+ ions neutralise the diphosphate and stabilise the leaving group, CMP. "
                 "The product is a new phosphodiester linking the acceptor to the X group; CMP is usually omitted from records."),
    },
]


def _match_card(card, ec3, roles, substrate_mols, changes, enzyme_text):
    from rdkit import Chem
    if ec3 not in card["ec3"]:
        return False
    if "cofactor" in card and not any(r and re.search(card["cofactor"], r) for r in roles):
        return False
    if "smarts" in card:
        pat = Chem.MolFromSmarts(card["smarts"])
        if not any(m is not None and m.HasSubstructMatch(pat) for m in substrate_mols):
            return False
    if "bond" in card and not any(re.search(card["bond"], c) for c in changes):
        return False
    if "enzyme_text" in card and not re.search(card["enzyme_text"], enzyme_text or "", re.I):
        return False
    return True


class MechanismKB:
    def __init__(self, mcsa_index="chat/data/mcsa_index.json"):
        p = Path(mcsa_index)
        self.mcsa = json.load(open(p)) if p.exists() else []

    def mcsa_exact(self, ec4):
        return [e for e in self.mcsa if ec4 in e["ecs"]]

    def mcsa_analogs(self, ec3, cofactor_terms, enzyme_text, min_overlap=0.2):
        """M-CSA entries of the same sub-subclass that use the same cofactors and resemble the enzyme by name/reaction
        (word Jaccard >= min_overlap); best first."""
        words = lambda t: {w for w in re.split(r"[^a-z0-9]+", t.lower()) if len(w) >= 4}
        q = words(enzyme_text)
        out = []
        for e in self.mcsa:
            if not any(x.startswith(ec3 + ".") for x in e["ecs"]):
                continue
            blob = (e["reaction"] + " " + e["mechanism"]).lower()
            if not all(t.lower() in blob for t in cofactor_terms):
                continue
            w = words(e["enzyme"] + " " + e["reaction"])
            sim = len(q & w) / max(len(q | w), 1)
            if sim >= min_overlap:
                out.append((sim, e))
        return [e for _, e in sorted(out, key=lambda x: -x[0])]

    def select(self, ec4, roles, substrate_mols, changes, enzyme_text):
        """(kind, title, text, source) for the best mechanism reference, or None."""
        ec3 = '.'.join(ec4.split('.')[:3])
        exact = self.mcsa_exact(ec4)
        if exact:
            e = exact[0]
            return ("exact", f"{e['enzyme']} (EC {ec4})", _mcsa_text(e), f"M-CSA entry {e['mcsa_id']}")
        for card in CARDS:
            if _match_card(card, ec3, roles, substrate_mols, changes, enzyme_text):
                return ("class", card["title"], card["text"], f"mechanism card '{card['id']}'")
        terms = [t for r in roles if r for t in ("NAD", "FAD", "FMN", "CoA", "ATP", "pyridoxal") if t.lower() in r.lower()]
        analog = self.mcsa_analogs(ec3, terms, enzyme_text)
        if analog:
            e = analog[0]
            return ("analog", f"{e['enzyme']} (EC {', '.join(e['ecs'])}), an enzyme of the same sub-subclass",
                    _mcsa_text(e), f"M-CSA entry {e['mcsa_id']} (analogous enzyme, different substrate)")
        return None


def _mcsa_text(e, max_steps=8):
    steps = ' '.join(f"({i}) {s}" for i, s in enumerate(e["steps"][:max_steps], 1))
    return (e["mechanism"] + (f" Steps: {steps}" if steps else "")).strip()
