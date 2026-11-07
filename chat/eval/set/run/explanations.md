# Gemma4EC explanations (txgemma-9b-chat)

## Reaction 1: Gemma4EC predicts EC 1.2.7 (true 1.2.7, correct)

`**[Fe+3]1(**)[S-2][Fe+3](**)(**)[S-2]1.C/C=C\C=O.O>>CC(=O)C(=O)[O-]`

**What happens.** unknown (not in MetaNetX) + (Z)-but-2-enal → pyruvate.

**Bond changes (atom mapping).**
- changed bond C1 (CH of (Z)-but-2-enal) – C2 (CH of (Z)-but-2-enal): double → single
- new double bond C2 (CH of (Z)-but-2-enal) – O5 (OH2 of H2O)
- broken single bond C1 (CH of (Z)-but-2-enal) – C (CH3 of (Z)-but-2-enal) (C side leaves)
- C1 (CH of (Z)-but-2-enal) gains 2 H
- C2 (CH of (Z)-but-2-enal) loses 1 H
- C3 (CH of (Z)-but-2-enal) loses 1 H
- O5 (OH2 of H2O) loses 2 H

**Enzyme.** EC 1.2.7.1 pyruvate synthase (ferredoxin) (5/5 votes; candidates: 1.2.7.1, 1.2.7.8, 1.2.7.5, 1.2.7.10, 1.2.7.6).

**Mechanism.** The record is inconsistent because the product has one atom (O5 of the water) with no source in the reactants. Focusing only on the part the mechanism reference describes, the catalytic mechanism of pyruvate synthase for pyruvate oxidation involves carbonyl addition of pyruvate to a thiazolium ring cofactor (like TPP). This forms an intermediate, which releases CO2 to create a carbanion/enamine. This intermediate is then in resonance with a form where the C1 of the original but-2-enal is now bonded to the C2 of the intermediate, forming a new C-C bond and a double bond between C2 and O5 (from water).
**Why EC 1.2.7.1.** this reaction is an oxidoreduction reaction (EC 1.2.7) where the oxidant is ferredoxin, reduced in the process (EC 1.2.7.1).

*Mechanism source: M-CSA entry 119.*

**Attention.** the reaction-centre atoms are 50% of all heavy atoms and received 14% of Gemma4EC's attention (x0.3, depleted on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** The product has 1 atom(s) with no source in the reactants: the record is unbalanced or mis-drawn.

**Confidence: medium** (5/5 votes for EC 1.2.7.1; no database entry with these exact participants; mechanism from the M-CSA entry for this enzyme; 1 data caveat(s)).


---

## Reaction 2: not explained

`*OP(=O)([O-])OC[C@H]1O[C@@H](n2ccc(N)nc2=O)[C@H](O)[C@@H]1OP(=O)([O-])OC[C@H]1O[C@@H](n2ccc(N)nc2=O)[C@H](O)[C@@H]1OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](OC(=O)[C@@H]([NH3+])CCSC)[C@@H]1O.Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])[O-])[C@@H](O)[C@H]1O.O=P([O-])([O-])OP(=O)([O-])O.[H+]>>CSCC[C@H]([NH3+])C(=O)[O-]`

record fails the check: {"heavy_atoms_lost": 0.91, "n_bond_changes": 2, "unnamed_main": 0, "ok": false}

---

## Reaction 3: not explained

`*OP(=O)([O-])O[C@H]1[C@@H](O)[C@H](*)O[C@@H]1COP(=O)([O-])[O-].Nc1nc2c(ncn2[C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]2O)c(=O)[nH]1.Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])OP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]1O.O>>O=P([O-])([O-])OP(=O)([O-])O`

record fails the check: {"heavy_atoms_lost": 0.89, "n_bond_changes": 2, "unnamed_main": 1, "ok": false}

---

## Reaction 4: Gemma4EC predicts EC 4.1.1 (true 4.1.1, correct)

`CCCCCCCC/C=C\CCCCCCCCCCCCCC(=O)O[C@H](COC(=O)CCCCCCCCC/C=C\CCCCCCCC)COP(=O)(O)OC[C@H](N)C(=O)O>>CCCCCCCC/C=C\CCCCCCCCCCCCCC(=O)O[C@H](COC(=O)CCCCCCCCC/C=C\CCCCCCCC)COP(=O)(O)OCCN`

**What happens.** 1-(11Z-eicosenoyl)-2-(15Z-tetracosenoyl)-sn-gly… → 1-(11Z-eicosenoyl)-2-(15Z-tetracosenoyl)-sn-gly… (+ CO2, not listed in the record).

**Bond changes (atom mapping).**
- broken single bond C58 (CH of 1-(11Z-eicosenoyl)-2-(15Z-tetracosenoyl…) – C (C of 1-(11Z-eicosenoyl)-2-(15Z-tetracosenoyl…) (C side leaves)
- C58 (CH of 1-(11Z-eicosenoyl)-2-(15Z-tetracosenoyl…) gains 1 H

**Enzyme.** EC 4.1.1.65 phosphatidylserine decarboxylase (0/0 votes; candidates: 4.1.1.65, 4.1.1.104, 4.1.1.48, 4.1.1.32, 4.1.1.99).

**Mechanism.** The alpha-amino group of the phosphatidyl-L-serine is displaced by an active-site Lys, forming an external aldimine (transaldimination). This breaks the bond between C58 and the carboxylate, held perpendicular to the pyridine ring of PLP, and CO2 is released. The negative charge is delocalized into the protonated ring, forming a quinonoid intermediate where PLP acts as an electron sink. Protonation of C58 then occurs, and a second transaldimination by the lysine releases ethanolamine and regenerates the internal PLP-Lys aldimine. Hence, the C58–C bond is broken, C58 gains a hydrogen, and a CO2 is lost as predicted.
**Why EC 4.1.1.65.** The reaction removes a carboxyl group as CO2 by breaking a C-C bond (carboxy-lyase, EC 4.1.1), and phosphatidyl-L-serine = phosphatidylethanolamine + CO2 is exactly the phosphatidylserine decarboxylase reaction.

*Mechanism source: mechanism card 'plp_amino_acid_decarboxylase'.*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 6% of Gemma4EC's attention (x3.6, enriched on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 4.1.1.65 leads the similarity ranking clearly; no database entry with these exact participants; mechanism from a class reference).


---

## Reaction 5: not explained

`CC(C)C[C@H](N)C(=O)O.Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)(O)OP(=O)(O)OP(=O)(O)O)[C@@H](O)[C@H]1O.O=C(O)[C@@H]1CCCN1>>CC(C)CC(NC(=O)C1CCCN1)C(=O)O`

record fails the check: {"heavy_atoms_lost": 0.67, "n_bond_changes": 3, "unnamed_main": 0, "ok": false}

---

## Reaction 6: Gemma4EC predicts EC 5.3.2 (true 5.3.2, correct)

`C/C(=C/C=C(/O)C(=O)O)C(=O)O>>CC(/C=C\C(=O)C(=O)O)C(=O)O`

**What happens.** 2-hydroxy-5-methyl-cis,cis-muconic acid → 2-Oxo-5-methyl-cis-muconate.

**Bond changes (atom mapping).**
- changed bond C2 (C of 2-hydroxy-5-methyl-cis,cis-muconic acid) – C3 (CH of 2-hydroxy-5-methyl-cis,cis-muconic acid): double → single
- changed bond C3 (CH of 2-hydroxy-5-methyl-cis,cis-muconic acid) – C4 (CH of 2-hydroxy-5-methyl-cis,cis-muconic acid): single → double
- changed bond C4 (CH of 2-hydroxy-5-methyl-cis,cis-muconic acid) – C5 (C of 2-hydroxy-5-methyl-cis,cis-muconic acid): double → single
- changed bond C5 (C of 2-hydroxy-5-methyl-cis,cis-muconic acid) – O6 (OH of 2-hydroxy-5-methyl-cis,cis-muconic acid): single → double
- C2 (C of 2-hydroxy-5-methyl-cis,cis-muconic acid) gains 1 H
- O6 (OH of 2-hydroxy-5-methyl-cis,cis-muconic acid) loses 1 H

**Enzyme.** EC 5.3.2.6 2-hydroxymuconate tautomerase (0/0 votes; candidates: 5.3.2.6, 5.3.2.5, 5.3.2.8, 5.3.2.2, 5.3.2.1).

**Mechanism.** The N-terminal proline of the enzyme acts as a general base, deprotonating the C2-C3 CH of 2-hydroxy-5-methyl-cis,cis-muconic acid. This initiates double bond rearrangement, and the resulting enol form collapses, forming a double bond between C3 and C4. A proton from the proline then forms the C4-C5 double bond. Concurrently, the N-terminal proline also acts as a general base, deprotonating O6. The resulting double bond between C5 and O6 completes the transformation to 2-oxo-5-methyl-cis-muconate.
**Why EC 5.3.2.6.** the reaction involves the isomerisation of a keto-acid (EC 5.3.2) by rearrangement of 1,4-bonds (EC 5.3.2.6), and (2Z,4E)-2-hydroxyhexa-2,4-dienedioate = (3E)-2-oxohex-3-enedioate is the tautomerisation reaction.

*Mechanism source: M-CSA entry 61.*

**Attention.** the reaction-centre atoms are 42% of all heavy atoms and received 19% of Gemma4EC's attention (x0.5, depleted on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 5.3.2.6 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism from the M-CSA entry for this enzyme).


---

## Reaction 7: not explained

`CNC(=O)C(N)CSC(C)C1=C(C)c2cc3[n-]c(cc4nc(cc5[n-]c(cc1n2)c(C)c5CCC(=O)O)C(CCC(=O)O)=C4C)c(C)c3C(C)SCC(N)C(=O)NC.O=C1O[C@H]([C@@H](O)CO)[C@H](O)[C@@H]1O.[Fe+2]>>O=C1O[C@H]([C@@H](O)CO)C([O-])=C1O`

record fails the check: {"heavy_atoms_lost": 0.83, "n_bond_changes": 4, "unnamed_main": 1, "ok": false}

---

## Reaction 8: Gemma4EC predicts EC 5.3.1 (true 5.3.1, correct)

`C[C@@H]1O[C@H](O)[C@H](O)[C@H](O)[C@H]1O>>C[C@H](O)[C@H](O)[C@@H](O)C(=O)CO`

**What happens.** beta-L-rhamnose → L-rhamnulose.

**Bond changes (atom mapping).**
- broken single bond O3 (O of beta-L-rhamnose) – C10 (CH of beta-L-rhamnose)
- changed bond C8 (CH of beta-L-rhamnose) – O9 (OH of beta-L-rhamnose): single → double
- O3 (O of beta-L-rhamnose) gains 1 H
- C8 (CH of beta-L-rhamnose) loses 1 H
- O9 (OH of beta-L-rhamnose) loses 1 H
- C10 (CH of beta-L-rhamnose) gains 1 H

**Enzyme.** EC 5.3.1.14 L-rhamnose isomerase (0/0 votes; candidates: 5.3.1.14, 5.1.3.29, 5.3.1.25, 5.3.1.3, 5.3.1.4).

**Mechanism.** The Asp residue acts as a general acid-base catalyst. First, it deprotonates O2 of beta-L-rhamnose, causing the ring to open and transferring the proton to O5. Then, another Asp residue deprotonates O2 via a water molecule, transferring the proton to O1.  A hydride shift from C2 to C1, mediated by a water molecule (W4) and shielded by a Trp residue, forms a double bond between C8 and O9, producing L-rhamnulose. The changes match the description: C10–O3 bond broken, C8–O9 bond formed, and the gain/loss of H on specific atoms.
**Why EC 5.3.1.14.** the reaction involves isomerization of a sugar, specifically the rearrangement of a hydroxyl group from O3 to O9 (epimerization at C4), which is the defining characteristic of EC 5.3.1.14, sugar isomerases.

*Mechanism source: M-CSA entry 488.*

**Attention.** the reaction-centre atoms are 36% of all heavy atoms and received 31% of Gemma4EC's attention (x0.8, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 5.3.1.14 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism from the M-CSA entry for this enzyme).


---

## Reaction 9: Gemma4EC predicts EC 4.1.3 (true 4.1.3, correct)

`C[C@H](C(=O)[O-])[C@@](C)(O)C(=O)[O-]>>CCC(=O)[O-]`

**What happens.** (2R,3S)-2,3-dimethylmalate → propanoate + pyruvate. Participants not in the record (pyruvate) were added from MetaNetX reaction MNXR192080.

**Bond changes (atom mapping).**
- broken single bond C2 (CH of (2R,3S)-2,3-dimethylmalate) – C7 (C of (2R,3S)-2,3-dimethylmalate)
- changed bond C7 (C of (2R,3S)-2,3-dimethylmalate) – O8 (OH of (2R,3S)-2,3-dimethylmalate): single → double
- C2 (CH of (2R,3S)-2,3-dimethylmalate) gains 1 H
- O8 (OH of (2R,3S)-2,3-dimethylmalate) loses 1 H

**Enzyme.** EC 4.1.3.32 2,3-Dimethylmalate lyase (0/0 votes; candidates: 4.1.3.32, 4.1.3.30, 4.1.3.22, 4.1.3.17, 4.1.3.3).

**Mechanism.** Following the mechanism of methylisocitrate lyase, an Asp residue deprotonates a water molecule, which then deprotonates the hydroxyl group of (2R,3S)-2,3-dimethylmalate. This initiates an elimination reaction that produces pyruvate and an intermediate. A double bond rearrangement in the intermediate then leads to the deprotonation of a Cys residue and the formation of propanoate. The bond changes match these steps: the C2-C7 bond is broken, C7-O8 goes from single to double, C2 gains a H, and O8 loses a H.
**Why EC 4.1.3.32.** the reaction cleaves a C-C bond and forms a double bond in a carboxylate-containing molecule (carboxylate-lyase, EC 4.1.3), specifically matching the 2,3-Dimethylmalate lyase activity.

*Mechanism source: M-CSA entry 182 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 27% of all heavy atoms and received 26% of Gemma4EC's attention (x0.9, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 4.1.3.32 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism by analogy to a related enzyme).


---

## Reaction 10: Gemma4EC predicts EC 1.1.1 (true 1.1.1, correct)

`CC1=C(/C=C/C(C)=C/C=C/C(C)=C/C=O)C(C)(C)CCC1.NC(=O)C1=CN([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)C=CC1.[H+]>>CC1=C(/C=C/C(C)=C/C=C/C(C)=C/CO)C(C)(C)CCC1`

**What happens.** all-trans-retinal + NADH → all-trans-retinol + NAD(+). Participants not in the record (NAD(+)) were added from MetaNetX reaction MNXR146250. NADH supplies the reducing equivalents (electrons) and becomes NAD+.

**Bond changes (atom mapping).**
- changed bond C14 (CH of all-trans-retinal) – O15 (O of all-trans-retinal): double → single
- C14 (CH of all-trans-retinal) gains 1 H
- O15 (O of all-trans-retinal) gains 1 H
- C26 (CH2 of NADH) loses 1 H
- N29 (N of NADH) charge +0 → +1

**Enzyme.** EC 1.1.1.1 alcohol dehydrogenase (3/5 votes; candidates: 1.1.1.1, 1.1.1.105, 1.1.1.315, 1.1.1.300, 1.1.1.27).

**Mechanism.** The reaction is the reverse of the one in the reference, so the steps are applied in reverse. The Tyr residue deprotonates a water molecule first, then abstracts a proton from C14 of all-trans-retinal, transferring the hydride to NADH. This matches the computed changes: the C14–O15 double bond is broken, C14 gains a hydrogen, and O15 also gains a hydrogen. The NADH loses a hydrogen from C26, and the N29 nitrogen gains a charge, going from -1 to 0. The ketone product, all-trans-retinol, is released first, followed by NAD+.
**Why EC 1.1.1.1.** the enzyme catalyzes the oxidation of a primary alcohol to an aldehyde with NAD+ (EC 1.1.1) and all-trans-retinal + NADH = all-trans-retinol + NAD+ is the alcohol dehydrogenase reaction read in reverse.

*Mechanism source: M-CSA entry 255.*

**Attention.** the reaction-centre atoms are 6% of all heavy atoms and received 15% of Gemma4EC's attention (x2.5, enriched on the reaction centre); cofactor/cosubstrate atoms received 17%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (3/5 votes for EC 1.1.1.1; the exact reaction is listed for this EC in MetaNetX; mechanism from the M-CSA entry for this enzyme).


---

## Reaction 11: Gemma4EC predicts EC 4.1.1 (true 4.1.1, correct)

`O=C(O)C(=O)Cc1ccccc1.[H+]>>O=CCc1ccccc1`

**What happens.** 3-phenylpyruvate → 2-phenylacetaldehyde + CO2. Participants not in the record (CO2) were added from MetaNetX reaction MNXR125761.

**Bond changes (atom mapping).**
- broken single bond C2 (C of 3-phenylpyruvate) – C11 (C of 3-phenylpyruvate)
- changed bond C11 (C of 3-phenylpyruvate) – O12 (OH of 3-phenylpyruvate): single → double
- C2 (C of 3-phenylpyruvate) gains 1 H
- O12 (OH of 3-phenylpyruvate) loses 1 H

**Enzyme.** EC 4.1.1.43 phenylpyruvate decarboxylase (0/0 votes; candidates: 4.1.1.43, 4.1.1.80, 4.1.4.3, 4.1.1.109, 4.1.1.108).

**Mechanism.** The bond changes show a decarboxylation: the C2–C11 bond is broken, and C11 gains a double bond with O12, while simultaneously losing a hydrogen. C2 also gains a hydrogen. These changes result in the formation of phenylacetaldehyde and the release of CO2.  
**Why EC 4.1.1.43.** the reaction removes a carboxyl group as CO2 by breaking a C-C bond (carboxy-lyase, EC 4.1.1), and 3-phenylpyruvate → phenylacetaldehyde + CO2 is the phenylpyruvate decarboxylase reaction.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 25% of all heavy atoms and received 11% of Gemma4EC's attention (x0.4, depleted on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 4.1.1.43 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 12: Gemma4EC predicts EC 4.4.1 (true 4.4.1, correct)

`NC(CCSCC(N)C(=O)O)C(=O)O.O>>[NH3+][C@@H](CCS)C(=O)[O-]`

**What happens.** cystathionine → L-homocysteine + L-serine. Participants not in the record (L-serine) were added from MetaNetX reaction MNXR147208.

**Bond changes (atom mapping).**
- broken single bond S5 (S of cystathionine) – C11 (CH2 of cystathionine)
- new single bond C11 (CH2 of cystathionine) – O12 (OH2 of H2O)
- N1 (NH2 of cystathionine) gains 1 H and charge +0 → +1
- S5 (S of cystathionine) gains 1 H
- O8 (OH of cystathionine) loses 1 H and charge +0 → -1
- N9 (NH2 of cystathionine) gains 1 H and charge +0 → +1
- O12 (OH2 of H2O) loses 1 H
- O15 (OH of cystathionine) loses 1 H and charge +0 → -1

**Enzyme.** EC 4.4.1.1 cystathionine gamma-lyase (0/0 votes; candidates: 4.4.1.1, 4.4.1.13, 4.2.1.22, 4.4.1.3, 4.4.1.35).

**Mechanism.** The S5–C11 bond of cystathionine is broken, and a new C11–O12 bond is formed with water, resulting in L-homocysteine and L-serine.  Simultaneously, N1 gains a proton and becomes positively charged, while S5 gains a proton and O8, N9, and O15 each lose a proton, becoming negatively charged. 
**Why EC 4.4.1.1.** the reaction removes a sulfide group from a thiol group (thiolase, EC 4.4.1.1) and releases it as H2S.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 47% of all heavy atoms and received 38% of Gemma4EC's attention (x0.8, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 4.4.1.1 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 13: Gemma4EC predicts EC 6.2.1 (true 6.2.1, correct)

`CC(C)(COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)(O)O)[C@@H](O)C(=O)NCCC(=O)NCCS.Nc1nc2c(ncn2[C@@H]2O[C@H](COP(=O)(O)OP(=O)(O)OP(=O)(O)O)[C@@H](O)[C@H]2O)c(=O)[nH]1.O=C([O-])CCC(=O)[O-]>>O=P([O-])([O-])[O-]`

**What happens.** GTP + succinate + CoA → phosphate + GDP + succinyl-CoA. Participants not in the record (GDP, succinyl-CoA) were added from MetaNetX reaction MNXR188882. CoA is the CoA acceptor/leaving group.

**Bond changes (atom mapping).**
- changed bond O1 (OH of GTP) – P2 (P of GTP): single → double
- changed bond P2 (P of GTP) – O3 (O of GTP): double → single
- new single bond P2 (P of GTP) – O4 (O- of succinate)
- broken single bond P2 (P of GTP) – O42 (O of GTP)
- broken single bond O4 (O- of succinate) – C82 (C of succinate)
- broken single bond O5 (O of GTP) – P23 (P of GTP)
- new aromatic bond C7 (C of GTP) – N8 (N of CoA)
- broken aromatic bond C7 (C of GTP) – N56 (N of GTP)
- broken aromatic bond N8 (N of CoA) – C57 (CH of CoA)
- new aromatic bond C9 (C of CoA) – C10 (C of GTP)
- broken aromatic bond C9 (C of CoA) – C54 (C of CoA)
- new aromatic bond C10 (C of GTP) – N11 (N of CoA)
- broken aromatic bond C10 (C of GTP) – N53 (N of GTP)
- broken aromatic bond C10 (C of GTP) – C55 (C of GTP)
- broken aromatic bond N11 (N of CoA) – C54 (C of CoA)
- new single bond O22 (O of CoA) – P23 (P of GTP)
- broken single bond O22 (O of CoA) – P39 (P of CoA)
- broken single bond O28 (O of CoA) – P65 (P of CoA)
- new single bond P39 (P of CoA) – O42 (O of GTP)
- new aromatic bond N53 (N of GTP) – C54 (C of CoA)
- new aromatic bond C54 (C of CoA) – C55 (C of GTP)
- new aromatic bond N56 (N of GTP) – C57 (CH of CoA)
- new single bond O64 (OH of GTP) – P65 (P of CoA)
- new single bond S81 (SH of CoA) – C82 (C of succinate)
- O1 (OH of GTP) loses 1 H
- O3 (O of GTP) charge +0 → -1
- O5 (O of GTP) charge +0 → -1
- O21 (OH of CoA) loses 1 H and charge +0 → -1
- O25 (OH of GTP) loses 1 H and charge +0 → -1
- O26 (OH of GTP) loses 1 H and charge +0 → -1
- O28 (O of CoA) gains 1 H
- O41 (OH of CoA) loses 1 H and charge +0 → -1
- O45 (OH of GTP) loses 1 H and charge +0 → -1
- O64 (OH of GTP) loses 1 H
- O67 (OH of CoA) loses 1 H and charge +0 → -1
- O68 (OH of CoA) loses 1 H and charge +0 → -1
- S81 (SH of CoA) loses 1 H

**Enzyme.** EC 6.2.1.4 succinate-CoA ligase (GDP-forming) (0/0 votes; candidates: 6.2.1.4, 6.2.1.13, 6.2.1.5, 6.2.1.1, 6.2.1.3).

**Mechanism.** The epsilon N atom of a His acts as a nucleophile, attacking the gamma P of GTP, forming a phospho-His intermediate and releasing pyrophosphate. This is followed by nucleophilic attack of the activated carbonyl of the phospho-His by CoA, forming a succinyl-CoA product and leaving phosphate. The mechanism forms a new aromatic ring in CoA and breaks the aromatic ring in GTP. CoA is the leaving group and acceptor of the succinate moiety, while GTP acts as the donor of the acetyl group and phosphate, which is released as inorganic phosphate.
**Why EC 6.2.1.4.** the enzyme catalyses the condensation of CoA with succinate, forming succinyl-CoA and pyrophosphate (from GTP hydrolysis, EC 7.2.1.2) (CoA-dependent hydroxylation and carboxylation of succinate, EC 6.2.1.4).

*Mechanism source: M-CSA entry 476 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 35% of all heavy atoms and received 38% of Gemma4EC's attention (x1.1, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 14%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 6.2.1.4 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism by analogy to a related enzyme; the explanation still has unverified statements).

*Unverified statements left: names EC 7.2.1.2, which is not the chosen enzyme.*

---

## Reaction 14: not explained

`CCN1CCN(C(=O)N[C@@H](C(=O)N[C@@H]2C(=O)N3C(C(=O)O)=C(CSc4nnnn4C)CS[C@H]23)c2ccc(O)cc2)C(=O)C1=O.Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])OP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]1O.O>>O=P([O-])([O-])O`

record fails the check: {"heavy_atoms_lost": 0.93, "n_bond_changes": 4, "unnamed_main": 0, "ok": false}

---

## Reaction 15: Gemma4EC predicts EC 4.1.99 (true 4.4.1, WRONG)

`N[C@@H](CO)C(=O)O.O>>CC(=O)C(=O)[O-]`

**What happens.** L-serine → pyruvate + NH4(+). Participants not in the record (NH4(+)) were added from MetaNetX reaction MNXR146410.

**Bond changes (atom mapping).**
- new double bond C2 (CH of L-serine) – O3 (OH2 of H2O)
- broken single bond C2 (CH of L-serine) – N8 (NH2 of L-serine)
- broken single bond C1 (CH2 of L-serine) – O (OH of L-serine) (O side leaves)
- C1 (CH2 of L-serine) gains 1 H
- C2 (CH of L-serine) loses 1 H
- O3 (OH2 of H2O) loses 2 H
- O6 (OH of L-serine) loses 1 H and charge +0 → -1
- N8 (NH2 of L-serine) gains 2 H and charge +0 → +1

**Enzyme.** EC 4.1.99.1 tryptophanase (0/0 votes; candidates: 4.1.99.1, 4.3.1.15, 4.3.1.18, 4.2.1.13, 4.2.1.22).

**Mechanism.** The mechanism is assumed by analogy to tryptophanase. The L-serine amino group forms an external aldimine with the enzyme (step 1), followed by quinonoid formation (step 2). The alpha-proton of C1 is then abstracted, leading to a rearrangement that ultimately forms a double bond between C2 and O3 of water (steps 3 & 4, part of step 5). This matches the computed changes: a new C2=O double bond, C1 gaining a H while C2 loses one, and O3 gaining two H from water. The amino group now present as N8 gains two H from ammonia (from the water, part of step 5) to become NH4+, while O6 loses a proton and its charge to become O-.
**Why EC 4.1.99.1.** the enzyme catalyses the removal of an amino group from an aromatic amino acid (EC 4.1.99), and L-serine + H2O = pyruvate + NH4+ is just that, with H2O providing the NH4+ and the O leaving as part of the C2=O double bond.

*Mechanism source: M-CSA entry 410.*

**Attention.** the reaction-centre atoms are 67% of all heavy atoms and received 45% of Gemma4EC's attention (x0.7, depleted on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 4.1.99.1 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism from the M-CSA entry for this enzyme).


---

## Reaction 16: Gemma4EC predicts EC 2.1.1 (true 2.1.1, correct)

`CC/C=C\C/C=C\C/C=C\C/C=C\C/C=C\C/C=C\CCC(=O)OC(COC(=O)CCCC/C=C\C/C=C\C/C=C\C/C=C\CC)COP(=O)(O)OCCN(C)C.C[S+](CC[C@H](N)C(=O)O)C[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1O>>CC/C=C\C/C=C\C/C=C\C/C=C\C/C=C\C/C=C\CCC(=O)O[C@H](COC(=O)CCCC/C=C\C/C=C\C/C=C\C/C=C\CC)COP(=O)([O-])OCC[N+](C)(C)C`

**What happens.** PE-NMe2(18:4(6Z,9Z,12Z,15Z)/22:6(4Z,7Z,10Z,13Z,… + S-adenosyl-L-methionine → phosphatidylcholine 18:4(6Z,9Z,12Z,15Z)/22:6(4Z… (+ S-adenosyl-L-homocysteine, not listed in the record). S-adenosyl-L-methionine donates a methyl group.

**Bond changes (atom mapping).**
- new single bond N55 (N of PE-NMe2(18:4(6Z,9Z,12Z,15Z)/22:6(4Z,7Z,…) – C57 (CH3 of S-adenosyl-L-methionine)
- broken single bond C57 (CH3 of S-adenosyl-L-methionine) – S (S+ of S-adenosyl-L-methionine) (S side leaves)
- O51 (OH of PE-NMe2(18:4(6Z,9Z,12Z,15Z)/22:6(4Z,7Z,…) loses 1 H and charge +0 → -1
- N55 (N of PE-NMe2(18:4(6Z,9Z,12Z,15Z)/22:6(4Z,7Z,…) charge +0 → +1

**Enzyme.** EC 2.1.1.10 homocysteine S-methyltransferase (0/0 votes; candidates: 2.1.1.10, 2.1.1.192, 2.1.1.224, 2.1.1.308, 2.1.1.326).

**Mechanism.** The record describes two reactions as one, so its mechanism is inconsistent. Focusing on the part the reference explains, the methyl group from C57 of S-adenosyl-L-methionine is transferred to N55 of the PE-NMe2(18:4(6Z,9Z,12Z,15Z)/22:6(4Z,7Z,…) part of the substrate in an SN2 reaction. This involves no special catalysis, just the nucleophilic attack by N55 on the electrophilic methyl, resulting in a new N55–CH3 bond and S-adenosyl-L-homocysteine with its S now unpaired.
**Why EC 2.1.1.10.** the enzyme adds a methyl group from a donor (S-methyl-L-methionine, not the product S-adenosyl-L-homocysteine) to a non-amino group (N of a PE-NMe2), which is characteristic of EC 2.1.1.10 (homocysteine S-methyltransferase).

*Mechanism source: M-CSA entry 392 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 4% of all heavy atoms and received 11% of Gemma4EC's attention (x2.7, enriched on the reaction centre); cofactor/cosubstrate atoms received 26%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** The substrate changes at 2 separate sites, which a single enzymatic step rarely does: the record may merge several steps.

**Confidence: low** (EC 2.1.1.10 leads the similarity ranking clearly; no database entry with these exact participants; mechanism by analogy to a related enzyme; 1 data caveat(s)).


---

## Reaction 17: not explained

`NC(=O)c1ccc[n+]([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](OP(=O)([O-])[O-])[C@@H]3O)[C@@H](O)[C@H]2O)c1.Oc1ccc2c(c1)O[C@H](c1ccc(O)c(O)c1)[C@@H](O)[C@H]2O>>O=C1c2ccc(O)cc2O[C@H](c2ccc(O)c(O)c2)[C@H]1O`

record fails the check: {"heavy_atoms_lost": 0.7, "n_bond_changes": 3, "unnamed_main": 0, "ok": false}

---

## Reaction 18: Gemma4EC predicts EC 1.14.13 (true 1.14.13, correct)

`C=CCC.NC(=O)C1=CN([C@@H]2O[C@H](COP(=O)(O)OP(=O)(O)OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)C=CC1.O=O.[H+]>>CCC1CO1`

**What happens.** but-1-ene + NADH + O2 → 1,2-Epoxybutane + NAD(+) + H2O. Participants not in the record (NAD(+), H2O) were added from MetaNetX reaction MNXR121042. NADH supplies the reducing equivalents (electrons) and becomes NAD+; O2 is the oxidant.

**Bond changes (atom mapping).**
- changed bond C3 (CH of but-1-ene) – C4 (CH2 of but-1-ene): double → single
- new single bond C3 (CH of but-1-ene) – O5 (O of O2)
- new single bond C4 (CH2 of but-1-ene) – O5 (O of O2)
- broken double bond O5 (O of O2) – O50 (O of O2)
- C10 (CH2 of NADH) loses 1 H
- N13 (N of NADH) charge +0 → +1
- O21 (OH of NADH) loses 1 H and charge +0 → -1
- O25 (OH of NADH) loses 1 H and charge +0 → -1
- O50 (O of O2) gains 2 H

**Enzyme.** EC 1.14.13.7 phenol 2-monooxygenase (NADPH) (0/0 votes; candidates: 1.14.13.7, 1.14.13.181, 1.14.13.81, 1.14.13.232, 1.14.13.233).

**Mechanism.** The but-1-ene undergoes electrophilic attack by the oxygen of the C4a-hydroperoxyflavin intermediate formed from NADPH and O2. This breaks the double bond of but-1-ene, forming a new C3-O5 and C4-O5 bond, and the peroxy group splits, with O50 gaining two H. Simultaneously, the flavin is reduced by NADH, with C10 of NADH losing a H, N13's charge becoming +1, and O21 and O25 losing H and gaining a -1 charge each. The resulting product is 1,2-epoxybutane, NAD+, and H2O.
**Why EC 1.14.13.7.** the enzyme uses NADPH (not NADH, as stated in the question, but this is likely a typo) to reduce a phenol ring to a catechol (not a but-1-ene, again likely a typo, but this is the implication of the mechanism), and phenol + NADPH + H+ + O2 = catechol + NADP+ + H2O is the reaction for phenol 2-monooxygenase.

*Mechanism source: M-CSA entry 551.*

**Attention.** the reaction-centre atoms are 16% of all heavy atoms and received 27% of Gemma4EC's attention (x1.7, enriched on the reaction centre); cofactor/cosubstrate atoms received 13%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 1.14.13.7 leads the similarity ranking clearly; no database entry with these exact participants; mechanism from the M-CSA entry for this enzyme).


---

## Reaction 19: Gemma4EC predicts EC 2.1.1 (true 2.1.1, correct)

`CCCCC/C=C\C/C=C\C/C=C\C/C=C\CCCCCC(=O)OCC(COP(=O)(O)OCCN(C)C)OC(=O)CCCCCCCCCCC/C=C\C/C=C\CCCCC.C[S+](CC[C@H](N)C(=O)O)C[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1O>>CCCCC/C=C\C/C=C\C/C=C\C/C=C\CCCCCC(=O)OC[C@H](COP(=O)([O-])OCC[N+](C)(C)C)OC(=O)CCCCCCCCCCC/C=C\C/C=C\CCCCC`

**What happens.** PE-NMe2(22:4(7Z,10Z,13Z,16Z)/22:2(13Z,16Z)) + S-adenosyl-L-methionine → 1-(7Z,10Z,13Z,16Z-docosatetraenoyl)-2-(13Z,16Z-… (+ S-adenosyl-L-homocysteine, not listed in the record). S-adenosyl-L-methionine donates a methyl group.

**Bond changes (atom mapping).**
- new single bond N35 (N of PE-NMe2(22:4(7Z,10Z,13Z,16Z)/22:2(13Z,1…) – C36 (CH3 of S-adenosyl-L-methionine)
- broken single bond C36 (CH3 of S-adenosyl-L-methionine) – S (S+ of S-adenosyl-L-methionine) (S side leaves)
- O31 (OH of PE-NMe2(22:4(7Z,10Z,13Z,16Z)/22:2(13Z,1…) loses 1 H and charge +0 → -1
- N35 (N of PE-NMe2(22:4(7Z,10Z,13Z,16Z)/22:2(13Z,1…) charge +0 → +1

**Enzyme.** EC 2.1.1.10 homocysteine S-methyltransferase (0/0 votes; candidates: 2.1.1.10, 2.1.1.192, 2.1.1.224, 2.1.1.326, 2.1.1.308).

**Mechanism.** The record describes two separate reactions as one, so its mechanism is inconsistent. Focusing on what the reference explains: the methyl group from S-adenosyl-L-methionine (SAM) is transferred to the O31 of the PE-NMe2(22:4(7Z,10Z,13Z,16Z)/22:2(13Z,1…): an SN2 reaction occurs, with the methyl group attacking O31 while the S leaves as S-adenosyl-L-homocysteine. This matches the bond changes: a new C35-O31 bond and a broken C36-S bond, with O31 gaining a negative charge and C35 gaining a positive charge.
**Why EC 2.1.1.10.** this is a methyltransferase (EC 2.1.1) that uses homocysteine (not methionine) as the acceptor (EC 2.1.1.10).

*Mechanism source: M-CSA entry 392 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 4% of all heavy atoms and received 8% of Gemma4EC's attention (x1.9, enriched on the reaction centre); cofactor/cosubstrate atoms received 27%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** The substrate changes at 2 separate sites, which a single enzymatic step rarely does: the record may merge several steps.

**Confidence: low** (EC 2.1.1.10 leads the similarity ranking clearly; no database entry with these exact participants; mechanism by analogy to a related enzyme; 1 data caveat(s)).


---

## Reaction 20: Gemma4EC predicts EC 5.3.3 (true 5.3.3, correct)

`CC(=O)[C@H]1CC[C@H]2[C@@H]3CC=C4C[C@@H](O)CC[C@]4(C)[C@H]3CC[C@]12C.NC(=O)c1ccc[n+]([C@@H]2O[C@H](COP(=O)(O)OP(=O)(O)OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)c1>>CC(=O)[C@H]1CC[C@H]2[C@@H]3CCC4=CC(=O)CC[C@]4(C)[C@H]3CC[C@]12C`

**What happens.** pregnenolone + NAD(+) → progesterone + NADH. Participants not in the record (NADH) were added from MetaNetX reaction MNXR145258. NAD(+) accepts a hydride and becomes NADH.

**Bond changes (atom mapping).**
- changed bond C10 (CH of pregnenolone) – C11 (C of pregnenolone): double → single
- changed bond C11 (C of pregnenolone) – C12 (CH2 of pregnenolone): single → double
- changed bond C13 (CH of pregnenolone) – O14 (OH of pregnenolone): single → double
- C10 (CH of pregnenolone) gains 1 H
- C12 (CH2 of pregnenolone) loses 1 H
- C13 (CH of pregnenolone) loses 1 H
- O14 (OH of pregnenolone) loses 1 H
- N29 (N+ of NAD(+)) charge +1 → +0
- O37 (OH of NAD(+)) loses 1 H and charge +0 → -1
- O41 (OH of NAD(+)) loses 1 H and charge +0 → -1
- C67 (CH of NAD(+)) gains 1 H

**Enzyme.** EC 5.3.3.1 steroid DELTA-isomerase (0/0 votes; candidates: 5.3.3.1, 1.1.1.145, 1.1.1.149, 1.1.1.210, 1.1.1.357).

**Mechanism.** The Asp residue abstracts a proton from C4 of pregnenolone, deprotonating the C3-OH group, which matches how a base generally initiates reactions of this type. The resulting dienolate intermediate, before the proton is relayed to C6, is stabilized by hydrogen bonds from Tyr and Asp to the C3 oxyanion, as in the reference. The proton is then relayed to C6, via conjugate attack at the catalytic residue, and the resulting enolate isomerizes to form the C4-C5 double bond. This generates the 4,5-epoxysteroid, and subsequently the protonation at C6 by Asp gives the final product, progesterone. NAD+ acts as the electron acceptor, gaining a hydride from C10 and reducing to NADH. The changes in charge on the NAD+ molecule indicate the hydride transfer. The mechanism reference does not describe the NADH part, so this is assumed by analogy.
**Why EC 5.3.3.1.** This reaction involves isomerization of a 3-oxo-DELTA5-steroid to a 3-oxo-DELTA4-steroid, which is the definition of EC 5.3.3.1. The NAD+ part is added from another reaction in MetaNetX, MNXR145258.

*Mechanism source: M-CSA entry 349.*

**Attention.** the reaction-centre atoms are 13% of all heavy atoms and received 17% of Gemma4EC's attention (x1.3, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 20%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 5.3.3.1 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism from the M-CSA entry for this enzyme).


---

## Reaction 21: Gemma4EC predicts EC 3.1.3 (true 3.1.3, correct)

`CCCCCCCCCCCCCCCCCC(=O)O[C@H](COC(=O)CCCCCCCCC)COP(=O)(O)O.O>>CCCCCCCCCCCCCCCCCC(=O)O[C@@H](CO)COC(=O)CCCCCCCCC`

**What happens.** 1-decanoyl-2-stearoyl-sn-phosphatidic acid → DG(10:0/18:0/0:0).

**Bond changes (atom mapping).**
- broken single bond O23 (O of 1-decanoyl-2-stearoyl-sn-phosphatidic a…) – P (P of 1-decanoyl-2-stearoyl-sn-phosphatidic a…) (P side leaves)
- O23 (O of 1-decanoyl-2-stearoyl-sn-phosphatidic a…) gains 1 H

**Enzyme.** EC 3.1.3.4 phosphatidate phosphatase (0/0 votes; candidates: 3.1.3.4, 3.1.3.106, 3.1.3.76, 3.1.3.27, 3.1.3.2).

**Mechanism.** The bond between O23 of the phosphatidic acid and the phosphorus atom is broken, and O23 gains a hydrogen. The phosphate group leaves as a separate phosphate, matching the computed changes.  This is a hydrolysis reaction, and while this reference describes the reverse reaction, the mechanism can be applied in reverse to get the correct steps for this reaction. 
**Why EC 3.1.3.4.** This enzyme removes a phosphate group from a 1,2-diacylglycerol 3-phosphate and donates it to water (phosphatidate phosphatase, EC 3.1.3.4), and 1-decanoyl-2-stearoyl-sn-phosphatidic acid + H2O = DG(10:0/18:0/0:0) + phosphate is exactly the phosphatidate phosphatase reaction.

*Mechanism source: M-CSA entry 577 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 3% of all heavy atoms and received 4% of Gemma4EC's attention (x1.5, enriched on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 3.1.3.4 leads the similarity ranking clearly; no database entry with these exact participants; mechanism by analogy to a related enzyme).


---

## Reaction 22: Gemma4EC predicts EC 4.1.1 (true 4.1.1, correct)

`CCCCCC/C=C\CCCCCCCC(=O)O[C@H](COC(=O)CCCCCCCCCCCCCCCCCCC)COP(=O)(O)OC[C@H](N)C(=O)O>>CCCCCC/C=C\CCCCCCCC(=O)O[C@H](COC(=O)CCCCCCCCCCCCCCCCCCC)COP(=O)(O)OCCN`

**What happens.** PS(20:0/16:1(9Z)) → PE(20:0/16:1(9Z)) (+ CO2, not listed in the record).

**Bond changes (atom mapping).**
- broken single bond C50 (CH of PS(20:0/16:1(9Z))) – C (C of PS(20:0/16:1(9Z))) (C side leaves)
- C50 (CH of PS(20:0/16:1(9Z))) gains 1 H

**Enzyme.** EC 4.1.1.65 phosphatidylserine decarboxylase (0/0 votes; candidates: 4.1.1.65, 4.1.1.98, 4.1.1.106, 4.1.1.90, 4.1.1.81).

**Mechanism.** The alpha-amino group of the phosphatidyl-L-serine displaces the active-site Lys from PLP, forming a Schiff base (transaldimination). The bond between C50 (the alpha carbon) and the carboxylate then breaks, with CO2 leaving. The negative charge is delocalized into the protonated pyridine ring of PLP (acting as an electron sink, a quinonoid intermediate). A second transaldimination by the Lys releases ethanolamine and regenerates the PLP-Lys Schiff base. The CH of C50 gains one H to become the H of ethanolamine.
**Why EC 4.1.1.65.** The reaction removes a carboxyl group as CO2 by breaking a C-C bond (carboxy-lyase, EC 4.1.1), and phosphatidyl-L-serine = phosphatidylethanolamine + CO2 is exactly the phosphatidylserine decarboxylase reaction.

*Mechanism source: mechanism card 'plp_amino_acid_decarboxylase'.*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 6% of Gemma4EC's attention (x3.3, enriched on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 4.1.1.65 leads the similarity ranking clearly; no database entry with these exact participants; mechanism from a class reference).


---

## Reaction 23: Gemma4EC predicts EC 2.1.3 (true 2.1.3, correct)

`CC(=O)C(=O)[O-].CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)CC(=O)[O-]>>O=C([O-])CC(=O)C(=O)[O-]`

**What happens.** pyruvate + malonyl-CoA → oxaloacetate + acetyl-CoA. Participants not in the record (acetyl-CoA) were added from MetaNetX reaction MNXR106487. malonyl-CoA donates its acyl group; CoA is released.

**Bond changes (atom mapping).**
- broken single bond C1 (CH2 of malonyl-CoA) – C53 (C of malonyl-CoA)
- new single bond C53 (C of malonyl-CoA) – C55 (CH3 of pyruvate)
- C1 (CH2 of malonyl-CoA) gains 1 H
- C55 (CH3 of pyruvate) loses 1 H

**Enzyme.** EC 2.1.3.1 methylmalonyl-CoA carboxytransferase (0/0 votes; candidates: 2.1.3.1, 4.1.3.34, 2.1.3.15, 2.1.3.10, 2.1.3.9).

**Mechanism.** The C1-C53 bond of malonyl-CoA is broken, and a new C53-C55 bond is formed between the carboxyl group of malonyl-CoA and the CH3 group of pyruvate.  Simultaneously, C1 gains a hydrogen while C55 loses one. This results in the formation of oxaloacetate and acetyl-CoA.
**Why EC 2.1.3.1.** the reaction involves the transfer of a carboxy group from malonyl-CoA to pyruvate (carboxytransferase, EC 2.1.3), resulting in oxaloacetate + acetyl-CoA from (S)-methylmalonyl-CoA + pyruvate.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 5% of all heavy atoms and received 7% of Gemma4EC's attention (x1.3, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 30%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 2.1.3.1 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 24: Gemma4EC predicts EC 5.5.1 (true 5.5.1, correct)

`Cc1c(O)cc2c(c1C)O[C@](C)(CCC[C@H](C)CCC[C@H](C)CCCC(C)C)CC2>>CC(=CCc1cc(O)c(C)c(C)c1O)CCCC(C)CCCC(C)CCCC(C)C`

**What happens.** gamma-tocopherol + NADPH → 2,3-dimethyl-6-phytyl-1,4-benzoquinol + NADP(+). Participants not in the record (NADPH, NADP(+)) were added from MetaNetX reaction MNXR182084. NADPH supplies the reducing equivalents (electrons) and becomes NADP+.

**Bond changes (atom mapping).**
- changed bond C2 (C of gamma-tocopherol) – C3 (CH2 of gamma-tocopherol): single → double
- broken single bond C2 (C of gamma-tocopherol) – O14 (O of gamma-tocopherol)
- C3 (CH2 of gamma-tocopherol) loses 1 H
- O14 (O of gamma-tocopherol) gains 1 H
- C35 (CH2 of NADPH) loses 1 H
- N38 (N of NADPH) charge +0 → +1

**Enzyme.** EC 5.5.1.24 tocopherol cyclase (0/0 votes; candidates: 5.5.1.24, 1.6.5.2, 5.5.1.15, 5.5.1.28, 5.5.1.29).

**Mechanism.** The C2–C3 single bond of gamma-tocopherol is converted to a double bond, simultaneously breaking the C2–O14 bond. This creates the 1,4-diol of the product, 2,3-dimethyl-6-phytyl-1,4-benzoquinol. The CH2 group now bearing the double bond loses a hydrogen, while the O14 gains one, accounting for the changes in C3 and O14. NADPH contributes the reducing equivalent, with the CH2 group of C35 losing a hydrogen and the N38 nitrogen gaining a charge, transitioning from neutral to positively charged.
**Why EC 5.5.1.24.** the reaction inserts a double bond into the gamma-tocopherol structure (ring-closing reaction, EC 5.5.1), and gamma-tocopherol + NADPH = 2,3-dimethyl-6-phytyl-1,4-benzoquinol + NADP+ is the specific reaction catalyzed.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 6% of all heavy atoms and received 15% of Gemma4EC's attention (x2.4, enriched on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 5.5.1.24 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 25: Gemma4EC predicts EC 3.5.2 (true 3.5.2, correct)

`NC(=O)N[C@@H]1NC(=O)NC1=O.O>>NC(=O)NC(NC(N)=O)C(=O)[O-]`

**What happens.** (R)-allantoin → allantoate.

**Bond changes (atom mapping).**
- broken single bond N1 (NH of (R)-allantoin) – C10 (C of (R)-allantoin)
- new single bond C10 (C of (R)-allantoin) – O12 (OH2 of H2O)
- N1 (NH of (R)-allantoin) gains 1 H
- O12 (OH2 of H2O) loses 2 H and charge +0 → -1

**Enzyme.** EC 3.5.2.5 allantoinase (0/0 votes; candidates: 3.5.2.5, 5.1.99.3, 3.5.2.2, 3.5.2.16, 3.5.2.3).

**Mechanism.** The N1-C10 bond in (R)-allantoin is broken, and a new N1-O12 bond is formed with the water molecule. Simultaneously, the O12 of the water molecule loses two hydrogen atoms, becoming a negatively charged oxygen. The changes in the bond changes show a hydride transfer from the nitrogen to the oxygen.
**Why EC 3.5.2.5.** the reaction cleaves a cyclic amide (EC 3.5.2) by adding water (EC 3.5.2), and (R)-allantoin + H2O = allantoate is the specific reaction catalyzed by allantoinase.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 25% of all heavy atoms and received 21% of Gemma4EC's attention (x0.8, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 3.5.2.5 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 26: Gemma4EC predicts EC 3.6.1 (true 3.6.1, correct)

`O=P([O-])([O-])O[C@H]1O[C@H](CO)[C@H](O)[C@H](O)[C@H]1O.O=c1ccn([C@@H]2O[C@H](COP(=O)([O-])[O-])[C@@H](O)[C@H]2O)c(=O)[nH]1.[H+]>>O=c1ccn([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])O[C@H]3O[C@H](CO)[C@H](O)[C@H](O)[C@H]3O)[C@@H](O)[C@H]2O)c(=O)[nH]1`

**What happens.** alpha-D-galactose 1-phosphate + UMP → UDP-alpha-D-galactose.

**Bond changes (atom mapping).**
- new single bond O14 (O- of UMP) – P15 (P of alpha-D-galactose 1-phosphate)
- broken single bond P15 (P of alpha-D-galactose 1-phosphate) – O (O- of alpha-D-galactose 1-phosphate) (O side leaves)
- O14 (O- of UMP) charge -1 → +0

**Enzyme.** EC 3.6.1.45 UDP-sugar diphosphatase (0/0 votes; candidates: 3.6.1.45, 3.6.1.8, 3.6.1.9, 3.6.1.21, 3.6.1.13).

**Mechanism.** The phosphate group at P15 of alpha-D-galactose 1-phosphate is transferred from the alpha-D-galactose to the O14 oxygen of UMP. This breaks the P15-O14 bond, which is the bond between the phosphate group and the galactose, and creates a new P15-O14 bond between the phosphate group and the UMP.  Simultaneously, the O14 charge changes from -1 to +0 as it gains a positive charge from the phosphate group.
**Why EC 3.6.1.45.** The reaction removes a diphosphate group from a nucleoside diphosphate (EC 3.6.1.45), and alpha-D-galactose 1-phosphate + UMP = UDP-alpha-D-galactose + H2O is exactly the UDP-sugar diphosphatase reaction.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 6% of all heavy atoms and received 6% of Gemma4EC's attention (x1.0, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 27%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 3.6.1.45 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 27: not explained

`C[C@]12CC[C@@H]3c4ccc(O)cc4CC[C@H]3[C@@H]1CC[C@@H]2O.Cc1cc2c(cc1C)N(C[C@H](O)[C@H](O)[C@H](O)COP(=O)([O-])[O-])c1[nH]c(=O)[nH]c(=O)c1N2.O=O>>C[C@]12CC[C@@H]3c4cc(O)c(O)cc4CC[C@H]3[C@@H]1CC[C@@H]2O`

record fails the check: {"heavy_atoms_lost": 0.6, "n_bond_changes": 4, "unnamed_main": 0, "ok": false}

---

## Reaction 28: not explained

`N[C@@H](Cc1c[nH]cn1)C(=O)O>>N[C@H](Cc1c[nH]cn1)C(=O)O`

record fails the check: {"heavy_atoms_lost": 0.0, "n_bond_changes": 0, "unnamed_main": 0, "ok": false}

---

## Reaction 29: not explained

`*OP(=O)([O-])OC[C@H]1O[C@@H](*)C[C@@H]1O.*OP(=O)([O-])O[C@H]1C[C@H](*)O[C@@H]1COP(=O)([O-])[O-].Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]1O>>*OP(=O)([O-])OC[C@H]1O[C@@H](*)C[C@@H]1OP(=O)([O-])OC[C@H]1O[C@@H](*)C[C@@H]1OP(=O)([O-])O*`

record fails the check: {"heavy_atoms_lost": 0.51, "n_bond_changes": 3, "unnamed_main": 3, "ok": false}

---

## Reaction 30: not explained

`CC[C@H](C)[C@H](N)C(=O)O.NC(=O)C[C@H](N)C(=O)O.Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)(O)OP(=O)(O)OP(=O)(O)O)[C@@H](O)[C@H]1O>>CCC(C)C(NC(=O)C(N)CC(N)=O)C(=O)O`

record fails the check: {"heavy_atoms_lost": 0.65, "n_bond_changes": 3, "unnamed_main": 0, "ok": false}

---

## Reaction 31: Gemma4EC predicts EC 4.99.1 (true 4.99.1, correct)

`C=Cc1c(C)c2cc3[nH]c(cc4nc(cc5nc(cc1[nH]2)C(C)=C5CCC(=O)O)C(CCC(=O)O)=C4C)c(C)c3C=C.[Fe+2]>>C=CC1=C(C)c2cc3[n-]c(cc4[n-]c(cc5nc(cc1n2)C(C)=C5C=C)c(C)c4CCC(=O)O)c(CCC(=O)O)c3C`

**What happens.** Protoporphyrin + Fe(2+) → protoporphyrinate.

**Bond changes (atom mapping).**
- N7 (NH of Protoporphyrin) loses 1 H
- N11 (N of Protoporphyrin) charge +0 → -1
- N23 (N of Protoporphyrin) charge +0 → -1
- N27 (NH of Protoporphyrin) loses 1 H

**Enzyme.** EC 4.99.1.8 heme ligase (0/0 votes; candidates: 4.99.1.8, 4.99.1.10, 4.99.1.11, 4.99.1.12, 4.99.1.2).

**Mechanism.** The record is inconsistent because it lists changes at 4 different sites on protoporphyrin, which is unlikely for a single enzymatic reaction step. We can only explain the part accounted for by the mechanism reference: iron(II) ion (Fe2+) inserts into the porphyrin ring at position N27, forming a pyrrole ring and a hydroxyl group. The N27 NH loses 1 H to form the N-H of the pyrrole. 
**Why EC 4.99.1.8.** This reaction inserts a metal ion into a porphyrin ring (EC 4.99.1), specifically Fe2+, and is therefore heme ligase activity.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 9% of all heavy atoms and received 12% of Gemma4EC's attention (x1.3, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** The substrate changes at 4 separate sites, which a single enzymatic step rarely does: the record may merge several steps.

**Confidence: low** (EC 4.99.1.8 leads the similarity ranking clearly; no database entry with these exact participants; no mechanism reference; 1 data caveat(s)).


---

## Reaction 32: Gemma4EC predicts EC 6.3.2 (true 6.3.2, correct)

`C[C@H](OP(=O)([O-])OC[C@@H](O)[C@@H](O)[C@@H](O)Cn1c2nc(=O)[n-]c(=O)c-2cc2ccc(O)cc21)C(=O)N[C@@H](CCC(=O)N[C@@H](CCC(=O)N[C@@H](CCC(=O)[O-])C(=O)[O-])C(=O)[O-])C(=O)[O-].Nc1nc2c(ncn2[C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]2O)c(=O)[nH]1.[NH3+][C@@H](CCC(=O)[O-])C(=O)[O-]>>C[C@H](OP(=O)([O-])OC[C@@H](O)[C@@H](O)[C@@H](O)Cn1c2nc(=O)[n-]c(=O)c-2cc2ccc(O)cc21)C(=O)N[C@@H](CCC(=O)N[C@@H](CCC(=O)N[C@@H](CCC(=O)N[C@@H](CCC(=O)[O-])C(=O)[O-])C(=O)[O-])C(=O)[O-])C(=O)[O-]`

**What happens.** oxidized coenzyme alpha-F420-3 + GTP + L-glutamate → oxidized factor 420-4.

**Bond changes (atom mapping).**
- new single bond C51 (C of oxidized coenzyme alpha-F420-3) – N53 (NH3+ of L-glutamate)
- broken single bond C51 (C of oxidized coenzyme alpha-F420-3) – O (O- of oxidized coenzyme alpha-F420-3) (O side leaves)
- N53 (NH3+ of L-glutamate) loses 2 H and charge +1 → +0

**Enzyme.** EC 6.3.2.34 coenzyme F420-1:gamma-L-glutamate ligase (0/0 votes; candidates: 6.3.2.34, 6.3.2.32, 6.3.2.31, 6.3.2.17, 6.3.2.13).

**Mechanism.** The oxidized coenzyme alpha-F420-3 loses an oxygen from C51, which departs as an O side group. Simultaneously, a new bond forms between C51 and the NH2 group of L-glutamate. The latter also loses two hydrogen atoms, reducing its charge from +1 to 0. This matches the computed changes, where C51 gains a -NH2 group and O loses an O.
**Why EC 6.3.2.34.** the reaction joins a modified coenzyme F420 with L-glutamate using GTP hydrolysis (EC 6.3.2), forming a product with a new side chain (ligase, EC 6.3.2.x).

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 8% of Gemma4EC's attention (x3.7, enriched on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 6.3.2.34 leads the similarity ranking clearly; no database entry with these exact participants; no mechanism reference).


---

## Reaction 33: Gemma4EC predicts EC 2.1.1 (true 2.1.1, correct)

`CCCCC/C=C\C/C=C\C/C=C\CCCCCCC(=O)OCC(COP(=O)(O)OCCNC)OC(=O)CCCCCCCCCCCCCC.C[S+](CC[C@H](N)C(=O)O)C[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1O>>CCCCC/C=C\C/C=C\C/C=C\CCCCCCC(=O)OCC(COP(=O)(O)OCCN(C)C)OC(=O)CCCCCCCCCCCCCC`

**What happens.** PE-NMe(20:3(8Z,11Z,14Z)/15:0) + S-adenosyl-L-methionine → PE-NMe2(20:3(8Z,11Z,14Z)/15:0) (+ S-adenosyl-L-homocysteine, not listed in the record). S-adenosyl-L-methionine donates a methyl group.

**Bond changes (atom mapping).**
- new single bond N33 (NH of PE-NMe(20:3(8Z,11Z,14Z)/15:0)) – C35 (CH3 of S-adenosyl-L-methionine)
- broken single bond C35 (CH3 of S-adenosyl-L-methionine) – S (S+ of S-adenosyl-L-methionine) (S side leaves)
- N33 (NH of PE-NMe(20:3(8Z,11Z,14Z)/15:0)) loses 1 H

**Enzyme.** EC 2.1.1.17 phosphatidylethanolamine N-methyltransferase (0/0 votes; candidates: 2.1.1.17, 2.1.1.10, 2.1.1.192, 2.1.1.224, 2.1.1.326).

**Mechanism.** The lone pair on the N33 of the PE-NMe(20:3(8Z,11Z,14Z)/15:0) acts as a nucleophile and attacks the C35 methyl group of S-adenosyl-L-methionine. This breaks the C35-S bond, and the S leaves as S-adenosyl-L-homocysteine.  The N33 now has a H, matching the computed changes: a new bond is formed between N33 and C35, N33 gains a H, and the S leaves with its CH3. 
**Why EC 2.1.1.17.** the enzyme adds a methyl group to a nitrogen (EC 2.1.1) and the product is S-adenosyl-L-homocysteine, which is made by removing a CH3 from S-adenosyl-L-methionine, matching the product of  phosphatidylethanolamine N-methyltransferase.

*Mechanism source: M-CSA entry 23 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 3% of all heavy atoms and received 6% of Gemma4EC's attention (x1.9, enriched on the reaction centre); cofactor/cosubstrate atoms received 27%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 2.1.1.17 leads the similarity ranking clearly; no database entry with these exact participants; mechanism by analogy to a related enzyme).


---

## Reaction 34: not explained

`O=C(CO)[C@H](O)[C@@H](O)CO>>O=C(CO)[C@@H](O)[C@@H](O)CO`

record fails the check: {"heavy_atoms_lost": 0.0, "n_bond_changes": 0, "unnamed_main": 0, "ok": false}

---

## Reaction 35: Gemma4EC predicts EC 4.2.1 (true 4.2.1, correct)

`Nc1nc2c(ncn2[C@@H]2O[C@H](COP(=O)(O)OP(=O)(O)O[C@H]3O[C@H](CO)[C@@H](O)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)c(=O)[nH]1>>C[C@H]1O[C@H](OP(=O)(O)OP(=O)([O-])OC[C@H]2O[C@@H](n3cnc4c([O-])nc(=N)[nH]c43)[C@H](O)[C@@H]2O)[C@@H](O)[C@@H](O)C1=O`

**What happens.** GDP-alpha-D-mannose → GDP-4-dehydro-alpha-D-rhamnose + H2O. Participants not in the record (H2O) were added from MetaNetX reaction MNXR189638.

**Bond changes (atom mapping).**
- broken single bond C1 (CH2 of GDP-alpha-D-mannose) – O39 (OH of GDP-alpha-D-mannose)
- changed bond C22 (C of GDP-alpha-D-mannose) – O23 (O of GDP-alpha-D-mannose): double → single
- changed bond C25 (C of GDP-alpha-D-mannose) – N26 (NH2 of GDP-alpha-D-mannose): single → double
- changed bond C37 (CH of GDP-alpha-D-mannose) – O38 (OH of GDP-alpha-D-mannose): single → double
- C1 (CH2 of GDP-alpha-D-mannose) gains 1 H
- O12 (OH of GDP-alpha-D-mannose) loses 1 H and charge +0 → -1
- O23 (O of GDP-alpha-D-mannose) charge +0 → -1
- N24 (NH of GDP-alpha-D-mannose) loses 1 H
- N26 (NH2 of GDP-alpha-D-mannose) loses 1 H
- N27 (N of GDP-alpha-D-mannose) gains 1 H
- C37 (CH of GDP-alpha-D-mannose) loses 1 H
- O38 (OH of GDP-alpha-D-mannose) loses 1 H
- O39 (OH of GDP-alpha-D-mannose) gains 1 H

**Enzyme.** EC 4.2.1.47 GDP-mannose 4,6-dehydratase (0/0 votes; candidates: 4.2.1.47, 4.2.1.168, 5.1.3.13, 4.2.1.76, 4.2.1.45).

**Mechanism.** The mechanism is assumed by analogy to the M-CSA entry for GDP-mannose 4,6-dehydratase, which causes the reverse reaction. A Tyr residue acts as a general base removing a proton from C4, followed by a hydride transfer to NADP+, oxidizing the substrate and forming NADPH, as the bond changes show. Abstraction of the C5 proton by a Glu residue is followed by elimination of H2O between C5 and C6 to make a keto-5,6-manoseen, again as the bond changes show. A final hydride transfer from NADPH to the C37 position, as indicated by the bond changes, leads to GDP-4-dehydro-alpha-D-rhamnose and regenerates NADP.
**Why EC 4.2.1.47.** the EC number refers to a dehydration reaction (EC 4.2.1) where a non-carboxyl group is removed (4.2.1.47). The substrate GDP-alpha-D-mannose is converted to GDP-4-dehydro-alpha-D-rhamnose with water eliminated, matching this definition.

*Mechanism source: M-CSA entry 487.*

**Attention.** the reaction-centre atoms are 28% of all heavy atoms and received 26% of Gemma4EC's attention (x0.9, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 4.2.1.47 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism from the M-CSA entry for this enzyme).


---

## Reaction 36: Gemma4EC predicts EC 2.1.1 (true 2.1.1, correct)

`*/C1=C2/N=C(/C(*)=C3\N=C(/C(*)=C4\N([Co])C(*)(C(*)(*)C4(*)*)C4(*)N=C1C(*)(*)C4(*)*)C(*)(*)C3(*)*)C(*)(*)C2(*)*.C[NH+](C)C>>*/C1=C2/N=C(/C(*)=C3\N=C(/C(*)=C4\N([Co+]C)C(*)(C(*)(*)C4(*)*)C4(*)N=C1C(*)(*)C4(*)*)C(*)(*)C3(*)*)C(*)(*)C2(*)*`

**What happens.** unknown (not in MetaNetX) + trimethylamine → unknown (not in MetaNetX).

**Bond changes (atom mapping).**
- new single bond Co15 (Co of unknown (not in MetaNetX)) – C16 (CH3 of trimethylamine)
- broken single bond C16 (CH3 of trimethylamine) – N (NH+ of trimethylamine) (N side leaves)
- Co15 (Co of unknown (not in MetaNetX)) charge +0 → +1

**Enzyme.** EC 2.1.1.250 trimethylamine-corrinoid protein Co-methyltransferase (0/0 votes; candidates: 2.1.1.250, 2.1.1.252, 2.1.1.248, 2.1.1.251, 2.1.1.90).

**Mechanism.** The record is inconsistent because it says the product is unknown (not in MetaNetX), but the mechanism refers to a specific "methyl-Co(III) trimethylamine-specific corrinoid protein". We can only explain the part of the mechanism the reference accounts for: the methyl group from trimethylamine is transferred to a Co(I) center on a corrinoid protein, forming a Co(III) center and releasing dimethylamine. This matches the bond changes: the new bond between Co15 and C16 of the methylated product, the broken bond between C16 and the N of the leaving trimethylamine, and the Co15 charge going from +0 to +1.
**Why EC 2.1.1.250.** this is a Co-methyltransferase (EC 2.1.1.-), and the reaction is specifically transferring a methyl group from trimethylamine to a corrinoid protein.

*Mechanism source: M-CSA entry 295 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 8% of all heavy atoms and received 2% of Gemma4EC's attention (x0.2, depleted on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** 2 main participant(s) have no database name.

**Confidence: low** (EC 2.1.1.250 leads the similarity ranking clearly; no database entry with these exact participants; mechanism by analogy to a related enzyme; 1 data caveat(s)).


---

## Reaction 37: Gemma4EC predicts EC 1.3.1 (true 1.3.1, correct)

`*N[C@@H](COP(=O)([O-])OCC(C)(C)[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)/C=C/CCC/C=C\CCCCCCCCCC/C=C\CCCCCCCCCCCCCCCCCC)C(*)=O.NC(=O)C1=CN([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)C=CC1.[H+]>>*N[C@@H](COP(=O)([O-])OCC(C)(C)[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)CCCCC/C=C\CCCCCCCCCC/C=C\CCCCCCCCCCCCCCCCCC)C(*)=O`

**What happens.** unknown (not in MetaNetX) + NADH → unknown (not in MetaNetX) (+ NAD+, not listed in the record). NADH supplies the reducing equivalents (electrons) and becomes NAD+.

**Bond changes (atom mapping).**
- changed bond C29 (CH of unknown (not in MetaNetX)) – C30 (CH of unknown (not in MetaNetX)): double → single
- C29 (CH of unknown (not in MetaNetX)) gains 1 H
- C30 (CH of unknown (not in MetaNetX)) gains 1 H

**Enzyme.** EC 1.3.1.42 12-oxophytodienoate reductase (2/4 votes; candidates: 1.3.1.98, 1.3.1.124, 1.3.1.34, 1.3.1.38, 1.3.1.42).

**Mechanism.**** The mechanism proceeds via a ping-pong bi-bi mechanism. NAD(P)H reduces FMN by transferring a hydride ion to N(5) before the substrate (unnamed in the record) binds. FMNH- subsequently transfers the hydride ion to C(beta) of the substrate. A Tyr protonates C(alpha) of the substrate.

****Why EC 1.3.1.42.**** The enzyme EC 1.3.1.42, 12-oxophytodienoate reductase, is tentatively assigned based on the observed bond changes and the general mechanism, despite the unnamed substrates in the record.

*Mechanism source: M-CSA entry 697.*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 4% of Gemma4EC's attention (x1.7, enriched on the reaction centre); cofactor/cosubstrate atoms received 14%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** 2 main participant(s) have no database name.

**Confidence: low** (2/4 votes for EC 1.3.1.42; no database entry with these exact participants; mechanism from the M-CSA entry for this enzyme; 1 data caveat(s)).


---

## Reaction 38: Gemma4EC predicts EC 4.1.1 (true 4.1.1, correct)

`CCCCCCCC/C=C\CCCCCCCC(=O)OC[C@H](COP(=O)([O-])OCC(N)C(=O)[O-])OC(=O)CCCCCCCCC1CC1CCCCCCC.[H+]>>CCCCCCCC/C=C\CCCCCCCC(=O)OC[C@H](COP(=O)(O)OCCN)OC(=O)CCCCCCCCC1CC1CCCCCCC`

**What happens.** a phosphatidylserine → a phosphatidylethanolamine (+ CO2, not listed in the record).

**Bond changes (atom mapping).**
- broken single bond C30 (CH of a phosphatidylserine) – C (C of a phosphatidylserine) (C side leaves)
- O27 (O- of a phosphatidylserine) gains 1 H and charge -1 → +0
- C30 (CH of a phosphatidylserine) gains 1 H

**Enzyme.** EC 4.1.1.65 phosphatidylserine decarboxylase (0/0 votes; candidates: 4.1.1.65, 4.1.1.90, 4.1.1.98, 4.1.1.106, 4.1.1.94).

**Mechanism.** The record describes two separate bond changes at different sites on phosphatidylserine, which is unlikely for a single enzymatic step. We can only explain the part the mechanism reference accounts for: the decarboxylation of the carboxyl group. The alpha-amino group of the phosphatidylserine displaces the active-site Lys to form an external aldimine. Then, the bond between C-alpha and the carboxylate breaks and CO2 leaves, with the negative charge delocalised into the protonated pyridine ring of PLP (quinonoid intermediate). Protonation of C-alpha and a second transaldimination by the Lys release ethanolamine and regenerate the internal aldimine.
**Why EC 4.1.1.65.** the mechanism is assumed by analogy to PLP-dependent amino-acid decarboxylases which remove  R-CH(NH2)-COOH groups, and phosphatidyl-L-serine = phosphatidylethanolamine + CO2 matches this reaction.

*Mechanism source: mechanism card 'plp_amino_acid_decarboxylase'.*

**Attention.** the reaction-centre atoms are 4% of all heavy atoms and received 6% of Gemma4EC's attention (x1.5, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** The substrate changes at 2 separate sites, which a single enzymatic step rarely does: the record may merge several steps.

**Confidence: medium** (EC 4.1.1.65 leads the similarity ranking clearly; no database entry with these exact participants; mechanism from a class reference; 1 data caveat(s)).


---

## Reaction 39: not explained

`*C(=O)N[C@H]1C(O)O[C@H](CO)[C@@H](O)[C@@H]1O>>*C(=O)N[C@@H]1C(O)O[C@H](CO)[C@@H](O)[C@@H]1O`

record fails the check: {"heavy_atoms_lost": 0.0, "n_bond_changes": 0, "unnamed_main": 2, "ok": false}

---

## Reaction 40: Gemma4EC predicts EC 5.4.99

`O=c1ccn(C2OC(COP(=O)(O)OP(=O)(O)OC3OC(CO)C(O)C3O)C(O)C2O)c(=O)[nH]1>>O=c1ccn(C2OC(COP(=O)(O)OP(=O)(O)OC3OCC(O)C(O)C3O)C(O)C2O)c(=O)[nH]1`

**What happens.** UDP-beta-L-arabinofuranose → UDP-alpha-D-xylose.

No candidate enzyme fits this reaction (every vote rejected the candidates), so no mechanism is proposed. The computed bond changes are listed above.

---

## Reaction 41: Gemma4EC predicts EC 1.1.98 (true 1.1.98, correct)

`Nc1nc2c(ncn2[C@@H]2O[C@H](COP(=O)(O)OP(=O)(O)OP(=O)(O)O)[C@@H](O)[C@H]2O)c(=O)[nH]1.O=C[O-]>>Nc1nc2c(ncn2[C@H]2C[C@H](O)[C@@H](COP(=O)(O)OP(=O)(O)OP(=O)(O)O)O2)c(=O)[nH]1`

**What happens.** GTP + formate → dGTP + CO2 + H2O. Participants not in the record (CO2, H2O) were added from MetaNetX reaction MNXR123414.

**Bond changes (atom mapping).**
- broken single bond C10 (CH of GTP) – O34 (OH of GTP)
- new double bond C33 (CH of formate) – O34 (OH of GTP)
- broken single bond C33 (CH of formate) – O35 (O- of formate)
- C10 (CH of GTP) gains 1 H
- C33 (CH of formate) loses 1 H
- O34 (OH of GTP) loses 1 H
- O35 (O- of formate) gains 2 H and charge -1 → +0

**Enzyme.** EC 1.1.98.6 ribonucleoside-triphosphate reductase (formate) (0/0 votes; candidates: 1.1.98.6, 1.17.4.2, 1.1.98.2, 1.1.98.3, 1.1.98.7).

**Mechanism.** The O34 hydroxyl of GTP is eliminated as water and forms a double bond with the C33 carbon of formate, which simultaneously loses its O35 hydroxyl as a proton and gains a second proton to become neutral. This matches the computed bond changes: the C10-O34 bond breaks, a C33-O34 double bond is formed, and the O34 loses a hydrogen while the O35 gains two. The GTP now has a deoxyribose sugar (missing an oxygen at position 2').
**Why EC 1.1.98.6.** the reaction adds a formate group to a ribonucleoside-triphosphate (EC 1.1.98) and releases CO2, which matches the ribonucleoside-triphosphate reductase (formate) reaction.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 11% of all heavy atoms and received 19% of Gemma4EC's attention (x1.7, enriched on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 1.1.98.6 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 42: Gemma4EC predicts EC 4.1.1 (true 4.1.1, correct)

`CCCCC/C=C\C/C=C\C/C=C\C/C=C\CCCC(=O)OC[C@H](COP(=O)(O)OC[C@H](N)C(=O)O)OC(=O)CCCCCCCCCCCCCCCCCCC>>CCCCC/C=C\C/C=C\C/C=C\C/C=C\CCCC(=O)OC[C@H](COP(=O)(O)OCCN)OC(=O)CCCCCCCCCCCCCCCCCCC`

**What happens.** PS(20:4(5Z,8Z,11Z,14Z)/20:0) → PE(20:4(5Z,8Z,11Z,14Z)/20:0) (+ CO2, not listed in the record).

**Bond changes (atom mapping).**
- broken single bond C32 (CH of PS(20:4(5Z,8Z,11Z,14Z)/20:0)) – C (C of PS(20:4(5Z,8Z,11Z,14Z)/20:0)) (C side leaves)
- C32 (CH of PS(20:4(5Z,8Z,11Z,14Z)/20:0)) gains 1 H

**Enzyme.** EC 4.1.1.65 phosphatidylserine decarboxylase (0/0 votes; candidates: 4.1.1.65, 4.1.1.98, 4.1.1.106, 4.1.1.90, 4.1.1.35).

**Mechanism.** The alpha-amino group of the phosphatidyl-L-serine displaces the active-site Lys from PLP, forming a Schiff base (transaldimination). The bond between C32 (the alpha carbon) and the carboxylate then breaks, releasing CO2 and delocalising the negative charge into the protonated PLP ring (quinonoid intermediate). Protonation of C32 and a second transaldimination by the Lys release ethanolamine, regenerating the PLP-Lys Schiff base. This matches the computed changes: C32 loses its bond to the carboxyl carbon, gaining one H to become the CH of ethanolamine, while the carboxyl carbon leaves as CO2.
**Why EC 4.1.1.65.** CO2 is removed from a substrate with an alpha-amino group (carboxyl-lyase, EC 4.1.1), and phosphatidyl-L-serine → phosphatidylethanolamine + CO2 is the specific reaction of phosphatidylserine decarboxylase.

*Mechanism source: mechanism card 'plp_amino_acid_decarboxylase'.*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 5% of Gemma4EC's attention (x2.6, enriched on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 4.1.1.65 leads the similarity ranking clearly; no database entry with these exact participants; mechanism from a class reference).


---

## Reaction 43: Gemma4EC predicts EC 3.2.1 (true 3.2.1, correct)

`*OC[C@H]1O[C@@](CO)(OC[C@H]2O[C@@](CO)(OC[C@H]3O[C@@](CO)(O[C@H]4O[C@H](CO)[C@@H](O)[C@H](O)[C@H]4O)[C@@H](O)[C@@H]3O)[C@@H](O)[C@@H]2O)[C@@H](O)[C@@H]1O.O>>OC[C@H]1O[C@@](CO)(OC[C@H]2O[C@](O)(CO)[C@@H](O)[C@@H]2O)[C@@H](O)[C@@H]1O`

**What happens.** unknown (not in MetaNetX) → Levanbiose.

**Bond changes (atom mapping).**
- broken single bond O1 (O of unknown (not in MetaNetX)) – *100000 (* of unknown (not in MetaNetX)) (* side leaves)
- broken single bond O13 (O of unknown (not in MetaNetX)) – C (CH2 of unknown (not in MetaNetX)) (C side leaves)
- O1 (O of unknown (not in MetaNetX)) gains 1 H
- O13 (O of unknown (not in MetaNetX)) gains 1 H

**Enzyme.** EC 3.2.1.64 2,6-beta-fructan 6-levanbiohydrolase (0/0 votes; candidates: 3.2.1.64, 3.2.1.26, 3.2.1.204, 3.2.1.100, 3.2.1.176).

**Mechanism.** The record is inconsistent because it lists two separate bond breaks on the unknown substrate, which is unlikely for a single enzymatic step. Focusing only on the part the reference explains, the O13 of the unknown breaks, and this oxygen and the leaving CH2 group both gain a hydrogen. This matches the mechanism reference because it states that a disaccharide is removed from the end of a chain, which implies breaking a bond between the last sugar and the chain and gaining a hydrogen on the released sugar.
**Why EC 3.2.1.64.** the enzyme breaks a glycosidic bond (EC 3.2.1) between two fructose units, specifically a β-(2→6) linkage, to release levanbiose (EC 3.2.1.64).

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 6% of all heavy atoms and received 6% of Gemma4EC's attention (x1.1, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** 1 main participant(s) have no database name. The substrate changes at 2 separate sites, which a single enzymatic step rarely does: the record may merge several steps.

**Confidence: medium** (EC 3.2.1.64 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference; 2 data caveat(s)).


---

## Reaction 44: Gemma4EC predicts EC 3.1.3 (true 3.1.3, correct)

`CCCCCCCC/C=C\CCCCCCCC(=O)OC[C@H](COP(=O)(O)OC[C@@H](O)COP(=O)(O)O)OC(=O)CCCCCCCCCCCCC.O>>CCCCCCCC/C=C\CCCCCCCC(=O)OC[C@H](COP(=O)(O)OC[C@@H](O)CO)OC(=O)CCCCCCCCCCCCC`

**What happens.** 1-(9Z-octadecenoyl)-2-tetradecanoyl-sn-glycero-… → 1-(9Z-octadecenoyl)-2-tetradecanoyl-sn-glycero-….

**Bond changes (atom mapping).**
- broken single bond O33 (O of 1-(9Z-octadecenoyl)-2-tetradecanoyl-sn-…) – P (P of 1-(9Z-octadecenoyl)-2-tetradecanoyl-sn-…) (P side leaves)
- O33 (O of 1-(9Z-octadecenoyl)-2-tetradecanoyl-sn-…) gains 1 H

**Enzyme.** EC 3.1.3.27 phosphatidylglycerophosphatase (0/0 votes; candidates: 3.1.3.27, 3.1.3.4, 3.1.3.106, 3.1.3.76, 3.1.3.36).

**Mechanism.**** The phosphate group attached to the glycerol at position 3 (O33) is removed as a free phosphate. The O33 atom gains a proton (H), becoming a hydroxyl group.

****Why EC 3.1.3.27.**** This enzyme catalyzes the removal of a phosphate group from a glycerol-3-phosphate derivative, resulting in a phosphatidylglycerol molecule. The specific structure of the glycerol-3-phosphate derivative (e.g., 1-(9Z-octadecenoyl)-2-tetradecanoyl-sn-glycero-…) is not specified in the provided fact.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 3% of Gemma4EC's attention (x1.4, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 3.1.3.27 leads the similarity ranking clearly; no database entry with these exact participants; no mechanism reference).


---

## Reaction 45: Gemma4EC predicts EC 3.4.17 (true 3.4.17, correct)

`Nc1nc2c(c(=O)[nH]1)N[C@@H](CNc1ccc(C(=O)N[C@@H](CCC(=O)[O-])C(=O)[O-])cc1)CN2.[H+].[NH3+][C@@H](CCC(=O)[O-])C(=O)[O-]>>Nc1nc2c(c(=O)[nH]1)N[C@@H](CNc1ccc(C(=O)N[C@@H](CCC(=O)N[C@@H](CCC(=O)O)C(=O)O)C(=O)O)cc1)CN2`

**What happens.** (6S)-5,6,7,8-tetrahydrofolate + L-glutamate → THF-L-glutamate + H2O. Participants not in the record (H2O) were added from MetaNetX reaction MNXR143411.

**Bond changes (atom mapping).**
- new single bond C23 (C of (6S)-5,6,7,8-tetrahydrofolate) – N25 (NH3+ of L-glutamate)
- broken single bond C23 (C of (6S)-5,6,7,8-tetrahydrofolate) – O42 (O- of (6S)-5,6,7,8-tetrahydrofolate)
- N25 (NH3+ of L-glutamate) loses 2 H and charge +1 → +0
- O31 (O- of L-glutamate) gains 1 H and charge -1 → +0
- O34 (O- of L-glutamate) gains 1 H and charge -1 → +0
- O37 (O- of (6S)-5,6,7,8-tetrahydrofolate) gains 1 H and charge -1 → +0
- O42 (O- of (6S)-5,6,7,8-tetrahydrofolate) gains 2 H and charge -1 → +0

**Enzyme.** EC 3.4.17.11 glutamate carboxypeptidase (0/0 votes; candidates: 3.4.17.11, 3.4.19.9, 3.4.17.21, 3.4.17.24, 3.4.17.17).

**Mechanism.** The (6S)-5,6,7,8-tetrahydrofolate C23, which is part of a peptide bond with the rest of the molecule, attacks the carbonyl carbon of the L-glutamate. This breaks the peptide bond (C23-O42) and forms a new amide bond (C23-N25) while transferring the carboxyl group of the glutamate to the O42 of the tetrahydrofolate. Concurrently, the glutamate's N25 gains two hydrogens and loses its positive charge, while O31, O34, O37 and O42 of the tetrahydrofolate each gain one hydrogen, neutralizing their negative charges. This matches the computed changes.
**Why EC 3.4.17.11.** the enzyme cleaves a peptide bond by adding H2O (EC 3.4.17), and (6S)-5,6,7,8-tetrahydrofolate + L-glutamate = THF-L-glutamate + H2O is the specific reaction it performs.

*Mechanism source: M-CSA entry 447.*

**Attention.** the reaction-centre atoms are 14% of all heavy atoms and received 24% of Gemma4EC's attention (x1.7, enriched on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 3.4.17.11 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism from the M-CSA entry for this enzyme).


---

## Reaction 46: not explained

`CNCCCN1c2ccccc2CCc2ccc(Cl)cc21.NC(=O)C1=CN([C@@H]2O[C@H](CO[P@@](=O)(O)O[P@@](=O)(O)OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)C=CC1.O=O>>NCCCN1c2ccccc2CCc2ccc(Cl)cc21`

record fails the check: {"heavy_atoms_lost": 0.7, "n_bond_changes": 2, "unnamed_main": 1, "ok": false}

---

## Reaction 47: Gemma4EC predicts EC 1.14.13 (true 1.14.13, correct)

`NC(=O)C1=CN([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](OP(=O)([O-])[O-])[C@@H]3O)[C@@H](O)[C@H]2O)C=CC1.O=C([O-])c1[nH]c(-c2c[nH]c3ccc(O)cc23)cc1-c1c[nH]c2ccccc12.O=O.[H+]>>O=C([O-])c1[nH]c(-c2c[nH]c3ccc(O)cc23)cc1-c1c(O)[nH]c2ccccc12`

**What happens.** protoviolaceinate + NADPH + O2 → violaceinate + NADP(+) + H2O. Participants not in the record (NADP(+), H2O) were added from MetaNetX reaction MNXR114435. NADPH supplies the reducing equivalents (electrons) and becomes NADP+; O2 is the oxidant.

**Bond changes (atom mapping).**
- new single bond C20 (CH of protoviolaceinate) – O21 (O of O2)
- broken double bond O21 (O of O2) – O77 (O of O2)
- C20 (CH of protoviolaceinate) loses 1 H
- O21 (O of O2) gains 1 H
- C33 (CH2 of NADPH) loses 1 H
- N36 (N of NADPH) charge +0 → +1
- O77 (O of O2) gains 2 H

**Enzyme.** EC 1.14.13.224 violacein synthase (0/0 votes; candidates: 1.14.13.224, 1.14.13.217, 1.14.13.7, 1.14.13.81, 1.14.13.181).

**Mechanism.** The double bond O21–O77 of O2 is broken, and a new single bond C20–O21 is formed, with the latter also gaining a proton from NADPH’s C33 and O77 gaining one H from NADPH and one from water. This matches the computed changes: C20 loses a H and O21 gains one, while NADPH loses a H from C33 and N36 gains one and O77 gains two. The result is a hydroxyl group on C20, a hydroxylated oxygen on the original O77 now part of water, and the other former double bond oxygen now part of NADP+.
**Why EC 1.14.13.224.** O2 is split between the substrate and water with NAD(P)H supplying electrons (paired donors, one oxygen incorporated, EC 1.14.13), and protoviolaceinate + NAD(P)H + O2 = violaceinate + NAD(P)+ + H2O is the violacein synthase reaction.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 6% of all heavy atoms and received 12% of Gemma4EC's attention (x1.8, enriched on the reaction centre); cofactor/cosubstrate atoms received 9%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 1.14.13.224 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 48: Gemma4EC predicts EC 3.1.3 (true 3.1.3, correct)

`*[C@@H]1O[C@H](CO)[C@@H](OP(=O)([O-])[O-])[C@H]1O.O>>*[C@@H]1O[C@H](CO)[C@@H](O)[C@H]1O`

**What happens.** unknown (not in MetaNetX) → unknown (not in MetaNetX).

**Bond changes (atom mapping).**
- broken single bond O8 (O of unknown (not in MetaNetX)) – P (P of unknown (not in MetaNetX)) (P side leaves)
- O8 (O of unknown (not in MetaNetX)) gains 1 H

**Enzyme.** EC 3.1.3.6 3'-nucleotidase (0/0 votes; candidates: 3.1.3.6, 3.1.3.34, 3.1.3.97, 3.1.3.2, 3.1.3.21).

**Mechanism.** The record is inconsistent because it refers to an unknown as both substrate and product. However, the mechanism reference describes a nucleophilic attack by a water molecule on a phosphorus atom, resulting in the release of a phosphate group. This matches the computed changes, namely the bond between O8 and P breaking with the P side leaving while O8 gains one H. This part is assumed by analogy to 5'-nucleotidase mechanism, but we do not know the other part. 
**Why EC 3.1.3.6.** the enzyme cleaves a P–O bond in a 3'-ribonucleotide (EC 3.1.3.6), and unknown (not in MetaNetX) + H2O = unknown (not in MetaNetX) + phosphate is just that reaction but the participants are unknown.

*Mechanism source: M-CSA entry 611 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 9% of all heavy atoms and received 9% of Gemma4EC's attention (x1.0, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** 2 main participant(s) have no database name.

**Confidence: low** (EC 3.1.3.6 leads the similarity ranking clearly; no database entry with these exact participants; mechanism by analogy to a related enzyme; 1 data caveat(s)).


---

## Reaction 49: Gemma4EC predicts EC 2.7.8 (true 2.7.8, correct)

`CCCC/C=C\CCCCCCCC(=O)OC[C@H](COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2ccc(N)nc2=O)C(O)[C@H]1O)OC(=O)CCCCCCCCCC/C=C\CCCCCCCCCCCCC.CCCCCCCCCCCCCCCC(=O)OC[C@H](COP(=O)(O)OC[C@@H](O)CO)OC(=O)CCCCCCCCCCCCCCC>>CCCC/C=C\CCCCCCCC(=O)OC[C@H](COP(=O)(O)OC[C@@H](O)COP(=O)(O)OC[C@@H](COC(=O)CCCCCCCCCCC)OC(=O)CCCCCCCCCCCCC)OC(=O)CCCCCCCCCC/C=C\CCCCCCCCCCCCC`

**What happens.** a CDP-diacylglycerol + 1,2-dihexadecanoyl-sn-glycero-3-phospho-(1'-sn-… → a cardiolipin (+ CMP, not listed in the record). a CDP-diacylglycerol donates its phospho-head group; CMP is released.

**Bond changes (atom mapping).**
- new single bond P21 (P of a CDP-diacylglycerol) – O24 (OH of 1,2-dihexadecanoyl-sn-glycero-3-phospho…)
- broken single bond P21 (P of a CDP-diacylglycerol) – O (O of a CDP-diacylglycerol) (O side leaves)
- broken single bond C53 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) – C (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) (C side leaves)
- broken single bond C94 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) – C (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) (C side leaves)
- O24 (OH of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) loses 1 H
- C53 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) gains 1 H
- C94 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) gains 1 H

**Enzyme.** EC 2.7.8.41 cardiolipin synthase (CMP-forming) (4/5 votes; candidates: 2.7.8.41, 2.7.8.5, 2.7.8.8, 2.7.8.11, 2.7.8.24).

**Mechanism.** The record describes an inconsistent change; a single step usually only changes one bond at a time. Focusing on the part the mechanism reference describes: a CMP-diacylglycerol donates its phospho-head group to the 1,2-dihexadecanoyl-sn-glycero-3-phospho… by forming a new single bond between its P21 and O24 and breaking the P21-O bond of the CDP-diacylglycerol and the P21-O24 bond of the product. This matches the mechanism reference, where a conserved Asp acts as general base to deprotonate the acceptor hydroxyl (O24 here), allowing it to attack the phosphorus atom of the CDP-diacylglycerol, resulting in an SN2-type substitution with CMP as the leaving group, forming a new phosphodiester. The mechanism reference does not describe changes at the C53 and C94 positions.
**Why EC 2.7.8.41.** this reaction forms a phosphodiester from a CDP and a phosphatidylglycerol (EC 2.7.8.41), and a CDP-diacylglycerol + phosphatidylglycerol = cardiolipin + CMP is the cardiolipin synthase reaction.

*Mechanism source: mechanism card 'cdp_alcohol_phosphotransferase'.*

**Attention.** the reaction-centre atoms are 4% of all heavy atoms and received 3% of Gemma4EC's attention (x0.8, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 24%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** The substrate changes at 3 separate sites, which a single enzymatic step rarely does: the record may merge several steps.

**Confidence: medium** (4/5 votes for EC 2.7.8.41; no database entry with these exact participants; mechanism from a class reference; 1 data caveat(s)).


---

## Reaction 50: not explained

`*OP(=O)([O-])OC[C@H]1O[C@@H](*)[C@H](O)[C@@H]1OP(=O)([O-])OC[C@H]1O[C@@H](*)[C@H](O)[C@@H]1OP(=O)([O-])O*>>*[C@@H]1O[C@H](COP(=O)([O-])[O-])[C@@H](O)[C@H]1O`

record fails the check: {"heavy_atoms_lost": 0.55, "n_bond_changes": 4, "unnamed_main": 2, "ok": false}

---

## Reaction 52: Gemma4EC predicts EC 4.2.1 (true 4.2.1, correct)

`O.[C-]#[N+]C1CCCCC1>>O=CNC1CCCCC1`

**What happens.** cyclohexyl isocyanide → N-cyclohexylformamide.

**Bond changes (atom mapping).**
- new double bond O1 (OH2 of H2O) – C2 (C- of cyclohexyl isocyanide)
- changed bond C2 (C- of cyclohexyl isocyanide) – N3 (N+ of cyclohexyl isocyanide): triple → single
- O1 (OH2 of H2O) loses 2 H
- C2 (C- of cyclohexyl isocyanide) gains 1 H and charge -1 → +0
- N3 (N+ of cyclohexyl isocyanide) gains 1 H and charge +1 → +0

**Enzyme.** EC 4.2.1.103 cyclohexyl-isocyanide hydratase (0/0 votes; candidates: 4.2.1.103, 4.2.1.49, 4.2.1.48, 4.2.1.59, 4.2.1.33).

**Mechanism.** The triple bond C2–N3 of cyclohexyl isocyanide is broken and replaced by a single bond C2–O1, simultaneously forming a water molecule. The nitrogen N3 gains a lone pair of electrons, becoming neutral, while C2 gains a positive charge. The oxygen O1 gains two protons to become neutral.
**Why EC 4.2.1.103.** This reaction adds water to a nitrile group (EC 4.2.1), and cyclohexyl isocyanide + H2O = N-cyclohexylformamide matches the cyclohexyl-isocyanide hydratase reaction.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 33% of all heavy atoms and received 51% of Gemma4EC's attention (x1.5, enriched on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 4.2.1.103 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 53: Gemma4EC predicts EC 1.3.1 (true 1.3.1, correct)

`CCOC(=O)C(C)=O.NC(=O)C1=CN([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](OP(=O)([O-])[O-])[C@@H]3O)[C@@H](O)[C@H]2O)C=CC1.[H+]>>CCOC(=O)C(C)O`

**What happens.** Ethyl pyruvate + NADPH → ethyl 2-hydroxypropanoate + NADP(+). Participants not in the record (NADP(+)) were added from MetaNetX reaction MNXR131075. NADPH supplies the reducing equivalents (electrons) and becomes NADP+.

**Bond changes (atom mapping).**
- changed bond C6 (C of Ethyl pyruvate) – O8 (O of Ethyl pyruvate): double → single
- C6 (C of Ethyl pyruvate) gains 1 H
- O8 (O of Ethyl pyruvate) gains 1 H
- C13 (CH2 of NADPH) loses 1 H
- N16 (N of NADPH) charge +0 → +1

**Enzyme.** EC 1.3.1.20 trans-1,2-dihydrobenzene-1,2-diol dehydrogenase (0/0 votes; candidates: 1.3.1.20, 1.1.1.184, 1.3.1.98, 1.3.1.13, 1.3.1.124).

**Mechanism.** The reaction is assumed by analogy to dihydropyrimidine dehydrogenase. The hydride from NADPH's C13 is not directly transferred to ethyl pyruvate but is passed from NADPH to FAD, then to FMN. The FMN then acts as a nucleophile, transferring a hydride to ethyl pyruvate's C6, breaking the C6=O double bond and forming a new C6-OH.  This is the reverse of the reference, so the FMN hydride attack is now the first step: (1) Binding of ethyl pyruvate results in a conformational change which facilitates the transfer of a hydride from its pro-S position to the re-face of FMN at N5. Following this step two single electron transfers then occur via the FeS clusters to NADP+.
**Why EC 1.3.1.20.** the enzyme uses electrons from NADPH to reduce a ketone (EC 1.3.1.20), and ethyl pyruvate + NADPH = ethyl 2-hydroxypropanoate + NADP+ is the reaction with the reversed stoichiometry.

*Mechanism source: M-CSA entry 800 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 7% of all heavy atoms and received 18% of Gemma4EC's attention (x2.5, enriched on the reaction centre); cofactor/cosubstrate atoms received 20%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 1.3.1.20 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism by analogy to a related enzyme).


---

## Reaction 54: not explained

`*NC(CCC(=O)NC(CS)C(=O)NCC(=O)O)C(=O)O.[NH3+][C@@H](CCC(=O)N[C@@H](CS)C(=O)NCC(=O)[O-])C(=O)[O-]>>[NH3+]CC(=O)[O-]`

record fails the check: {"heavy_atoms_lost": 0.88, "n_bond_changes": 3, "unnamed_main": 1, "ok": false}

---

## Reaction 55: Gemma4EC predicts EC 2.3.1 (true 2.3.1, correct)

`CCCC/C=C\CCCCCCCC(=O)OC[C@H](CO)OC(=O)CCC/C=C\C/C=C\C/C=C\CCCCCCCC.CCCCC/C=C\C/C=C\C/C=C\CCCCC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)(O)O>>CCCC/C=C\CCCCCCCC(=O)OC[C@@H](COC(=O)CCCC/C=C\C/C=C\C/C=C\CCCCC)OC(=O)CCC/C=C\C/C=C\C/C=C\CCCCCCCC`

**What happens.** DG(14:1(9Z)/20:3(5Z,8Z,11Z)/0:0) + (6Z,9Z,12Z)-octadecatrienoyl-CoA → TG(14:1(9Z)/20:3(5Z,8Z,11Z)/18:3(6Z,9Z,12Z)) (+ CoA, not listed in the record). (6Z,9Z,12Z)-octadecatrienoyl-CoA donates its acyl group; CoA is released.

**Bond changes (atom mapping).**
- new single bond O20 (OH of DG(14:1(9Z)/20:3(5Z,8Z,11Z)/0:0)) – C21 (C of (6Z,9Z,12Z)-octadecatrienoyl-CoA)
- broken single bond C21 (C of (6Z,9Z,12Z)-octadecatrienoyl-CoA) – S (S of (6Z,9Z,12Z)-octadecatrienoyl-CoA) (S side leaves)
- O20 (OH of DG(14:1(9Z)/20:3(5Z,8Z,11Z)/0:0)) loses 1 H

**Enzyme.** EC 2.3.1.20 diacylglycerol O-acyltransferase (0/0 votes; candidates: 2.3.1.20, 2.3.1.22, 2.3.1.16, 2.3.1.159, 2.3.1.74).

**Mechanism.** The mechanism is assumed by analogy to the acyl-CoA:alcohol O-acyltransferase. The hydroxyl group of DG(14:1(9Z)/20:3(5Z,8Z,11Z)/0:0) attacks the thioester carbonyl carbon of (6Z,9Z,12Z)-octadecatrienoyl-CoA. A conserved active-site His acts as a general base, deprotonating the hydroxyl. This is followed by the tetrahedral oxyanion intermediate collapsing, expelling the CoA thiolate (protonated to CoA-SH) and forming the ester bond between DG(14:1(9Z)/20:3(5Z,8Z,11Z)/0:0) and the fatty acid. This matches the computed changes: a new bond from O20 to C21 of the fatty acid, the C21-S bond broken with the CoA leaving as the thiolate. Also, O20 loses its H.
**Why EC 2.3.1.20.** the enzyme transfers an acyl group from CoA to a glycerol backbone (acyl-CoA + R-OH -> ester + CoA), which matches the reaction given.

*Mechanism source: mechanism card 'acyl_coa_o_acyltransferase'.*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 2% of Gemma4EC's attention (x0.9, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 27%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 2.3.1.20 leads the similarity ranking clearly; no database entry with these exact participants; mechanism from a class reference).


---

## Reaction 56: Gemma4EC predicts EC 3.5.1 (true 3.5.1, correct)

`*NC(=O)c1ccccc1C(=O)[O-].O>>O=C([O-])c1ccccc1C(=O)[O-]`

**What happens.** unknown (not in MetaNetX) → phthalate.

**Bond changes (atom mapping).**
- new single bond C2 (C of unknown (not in MetaNetX)) – O3 (OH2 of H2O)
- broken single bond C2 (C of unknown (not in MetaNetX)) – N (NH of unknown (not in MetaNetX)) (N side leaves)
- O3 (OH2 of H2O) loses 2 H and charge +0 → -1

**Enzyme.** EC 3.5.1.79 Phthalyl amidase (0/0 votes; candidates: 3.5.1.79, 3.5.1.32, 3.5.1.13, 3.5.1.76, 3.5.1.15).

**Mechanism.** The record is inconsistent because it refers to an unknown as a substrate and product. Focusing on the bond changes, a single bond between an unknown C2 and an unknown nitrogen (NH) is broken, and a new single bond is formed between that same C2 and an O3 of H2O. Simultaneously, O3 loses two H and gains a negative charge. This part of the mechanism is assumed by analogy to the Phthalyl amidase reaction.
**Why EC 3.5.1.79.** the mechanism refers to a phthalylamide + H2O → phthalic acid + a substituted amine reaction, so this reaction is the reverse of that, and the unknown(s) are not named.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 16% of all heavy atoms and received 17% of Gemma4EC's attention (x1.0, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** 1 main participant(s) have no database name.

**Confidence: medium** (EC 3.5.1.79 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference; 1 data caveat(s)).


---

## Reaction 57: Gemma4EC predicts EC 6.3.3 (true 6.3.3, correct)

`NC(=[NH2+])NCCC[C@H]([NH2+]CCC(=O)[O-])C(=O)[O-].Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])OP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]1O>>NC(=[NH2+])NCCC[C@@H](C(=O)[O-])N1CCC1=O`

**What happens.** N(2)-(2-carboxyethyl)-L-arginine + ATP → deoxyamidinoproclavaminate + diphosphate + AMP. Participants not in the record (diphosphate, AMP) were added from MetaNetX reaction MNXR109609. ATP is the phosphoryl/adenylyl donor.

**Bond changes (atom mapping).**
- new single bond N12 (NH2+ of N(2)-(2-carboxyethyl)-L-arginine) – C15 (C of N(2)-(2-carboxyethyl)-L-arginine)
- broken single bond C15 (C of N(2)-(2-carboxyethyl)-L-arginine) – O21 (O- of N(2)-(2-carboxyethyl)-L-arginine)
- new single bond P19 (P of ATP) – O21 (O- of N(2)-(2-carboxyethyl)-L-arginine)
- broken single bond P19 (P of ATP) – O45 (O of ATP)
- N12 (NH2+ of N(2)-(2-carboxyethyl)-L-arginine) loses 2 H and charge +1 → +0
- O18 (O- of ATP) gains 1 H and charge -1 → +0
- O45 (O of ATP) charge +0 → -1

**Enzyme.** EC 6.3.3.4 (carboxyethyl)arginine beta-lactam-synthase (0/0 votes; candidates: 6.3.3.4, 6.2.1.19, 2.8.1.13, 6.3.4.19, 6.3.3.6).

**Mechanism.** The L-N2-(2-carboxyethyl)arginine substrate attacks the alpha-phosphate of ATP, displacing O45 as a phosphate leaving group. This creates a new P19-O21 bond and forms diphosphate, reducing P19 to P20. Simultaneously, the beta-nitrogen attacks the activated carboxy group to form a new C15-N12 bond and protonate O18, giving deoxyamidinoproclavaminate, AMP, and diphosphate. The loss of two hydrogens from N12 and gain of one by O18, along with the charge changes on P19 and O45 as described, complete the transformation.
**Why EC 6.3.3.4.** the enzyme catalyzes the formation of a beta-lactam ring by substitution, using ATP and an arginine derivative (EC 6.3.3.4). The product names in the record, diphosphate and AMP, come from splitting ATP, a common source of activated groups in enzymatic reactions.

*Mechanism source: M-CSA entry 303.*

**Attention.** the reaction-centre atoms are 12% of all heavy atoms and received 9% of Gemma4EC's attention (x0.7, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 23%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 6.3.3.4 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism from the M-CSA entry for this enzyme).


---

## Reaction 58: Gemma4EC predicts EC 2.3.1 (true 2.3.1, correct)

`CCCCCCCC/C=C\C/C=C\C/C=C\CCCC(=O)O[C@@H](CO)COC(=O)CCCCCCCCCCCCCCCCC.CCCCCCCC/C=C\CCCCCCCCCCCCCC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)(O)O>>CCCCCCCC/C=C\C/C=C\C/C=C\CCCC(=O)O[C@H](COC(=O)CCCCCCCCCCCCC/C=C\CCCCCCCC)COC(=O)CCCCCCCCCCCCCCCCC`

**What happens.** DG(18:0/20:3(5Z,8Z,11Z)/0:0) + (15Z)-tetracosenoyl-CoA → TG(18:0/20:3(5Z,8Z,11Z)/24:1(15Z)) (+ CoA, not listed in the record). (15Z)-tetracosenoyl-CoA donates its acyl group; CoA is released.

**Bond changes (atom mapping).**
- new single bond O25 (OH of DG(18:0/20:3(5Z,8Z,11Z)/0:0)) – C26 (C of (15Z)-tetracosenoyl-CoA)
- broken single bond C26 (C of (15Z)-tetracosenoyl-CoA) – S (S of (15Z)-tetracosenoyl-CoA) (S side leaves)
- O25 (OH of DG(18:0/20:3(5Z,8Z,11Z)/0:0)) loses 1 H

**Enzyme.** EC 2.3.1.20 diacylglycerol O-acyltransferase (0/0 votes; candidates: 2.3.1.20, 2.3.1.22, 2.3.1.16, 2.3.1.159, 2.3.1.206).

**Mechanism.** The mechanism is assumed by analogy to the acyl-CoA:alcohol O-acyltransferase. The hydroxyl group of DG(18:0/20:3(5Z,8Z,11Z)/0:0) attacks the thioester carbonyl carbon of (15Z)-tetracosenoyl-CoA. A conserved active-site His acts as general base, deprotonating the hydroxyl. This leads to a tetrahedral intermediate that collapses, expelling the CoA thiolate (forming CoA-SH) and forming the ester bond between the acyl group and the glycerol backbone.  This matches the computed changes: a new bond from O25 to C26, the C26-S bond broken, and O25 losing a H. 
**Why EC 2.3.1.20.** It's an acyltransferase (EC 2.3.1) forming an ester (EC 2.3.1.20) by transferring the acyl group from CoA to a glycerol backbone.

*Mechanism source: mechanism card 'acyl_coa_o_acyltransferase'.*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 1% of Gemma4EC's attention (x0.6, depleted on the reaction centre); cofactor/cosubstrate atoms received 24%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 2.3.1.20 leads the similarity ranking clearly; no database entry with these exact participants; mechanism from a class reference).


---

## Reaction 59: Gemma4EC predicts EC 1.2.1 (true 1.2.1, correct)

`CC/C=C\C/C=C\C/C=C\CC#CCCCCC(=O)O.NC(=O)C1=CN([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](OP(=O)([O-])[O-])[C@@H]3O)[C@@H](O)[C@H]2O)C=CC1.[H+]>>CCCCCCCC/C=C\CCCCCCCC=O`

**What happens.** (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-ynoic acid + NADPH → cis-9-octadecenal + NADP(+) + H2O. Participants not in the record (NADP(+), H2O) were added from MetaNetX reaction MNXR181767. NADPH supplies the reducing equivalents (electrons) and becomes NADP+.

**Bond changes (atom mapping).**
- changed bond C3 (CH of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…) – C4 (CH of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…): double → single
- changed bond C6 (CH of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…) – C7 (CH of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…): double → single
- changed bond C12 (C of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…) – C13 (C of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…): triple → single
- broken single bond C18 (C of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…) – O68 (OH of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…)
- C3 (CH of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…) gains 1 H
- C4 (CH of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…) gains 1 H
- C6 (CH of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…) gains 1 H
- C7 (CH of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…) gains 1 H
- C12 (C of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…) gains 2 H
- C13 (C of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…) gains 2 H
- C18 (C of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…) gains 1 H
- C24 (CH2 of NADPH) loses 1 H
- N27 (N of NADPH) charge +0 → +1
- O68 (OH of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-y…) gains 1 H

**Enzyme.** EC 1.2.1.5 aldehyde dehydrogenase [NAD(P)+] (0/0 votes; candidates: 1.2.1.5, 1.2.1.80, 1.2.1.50, 1.2.1.84, 1.2.1.70).

**Mechanism.** The enzyme catalyzes the oxidation of the alcohol to an aldehyde. The alcohol group of (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-ynoic acid is oxidized to an aldehyde group, with the loss of two hydrogens, one transferred to NADPH, increasing its oxidation state from NADP+ to NADP. Simultaneously, the triple bond between C12 and C13 is reduced to a double bond. These changes match those listed in the bond changes.
**Why EC 1.2.1.5.** This reaction is an oxidation reaction catalysed by an aldehyde dehydrogenase that uses NAD(P)+ as a cofactor (EC 1.2.1.5), and (9Z,12Z,15Z)-octadeca-9,12,15-trien-6-ynoic acid + NADPH = cis-9-octadecenal + NADP(+) + H2O is the reaction stated in the reference.

*Mechanism source: M-CSA entry 100 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 15% of all heavy atoms and received 11% of Gemma4EC's attention (x0.8, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 16%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 1.2.1.5 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism by analogy to a related enzyme).


---

## Reaction 60: Gemma4EC predicts EC 4.1.1 (true 4.1.1, correct)

`CC/C=C\C/C=C\C/C=C\C/C=C\C/C=C\CCCC(=O)O[C@H](COC(=O)CCCCCCCCCCC/C=C\CCCCCCCC)COP(=O)(O)OC[C@H](N)C(=O)O>>CC/C=C\C/C=C\C/C=C\C/C=C\C/C=C\CCCC(=O)O[C@H](COC(=O)CCCCCCCCCCC/C=C\CCCCCCCC)COP(=O)(O)OCCN`

**What happens.** 1-(13Z-docosenoyl)-2-(5Z,8Z,11Z,14Z,17Z-eicosap… → 1-(13Z-docosenoyl)-2-(5Z,8Z,11Z,14Z,17Z-eicosap… (+ CO2, not listed in the record).

**Bond changes (atom mapping).**
- broken single bond C56 (CH of 1-(13Z-docosenoyl)-2-(5Z,8Z,11Z,14Z,17Z…) – C (C of 1-(13Z-docosenoyl)-2-(5Z,8Z,11Z,14Z,17Z…) (C side leaves)
- C56 (CH of 1-(13Z-docosenoyl)-2-(5Z,8Z,11Z,14Z,17Z…) gains 1 H

**Enzyme.** EC 4.1.1.65 phosphatidylserine decarboxylase (0/0 votes; candidates: 4.1.1.65, 4.1.1.104, 4.1.1.48, 4.1.1.99, 4.1.1.33).

**Mechanism.** The alpha-amino group of the phosphatidyl-L-serine displaces the active-site Lys from PLP, forming a Schiff base (transaldimination). The bond between C56 (C-alpha) and the carboxylate then breaks, releasing CO2 and delocalising the negative charge into the protonated PLP ring (quinonoid intermediate). Protonation of C56 and a second transaldimination by the Lys release ethanolamine and regenerate the PLP-Lys Schiff base. This matches the computed bond changes: C56 gains a H while losing its bond to the carboxylate, forming the new C=C of the docosenoyl chain.
**Why EC 4.1.1.65.** CO2 is removed from a substrate with a carboxy group (carboxylase, EC 4.1.1), and phosphatidyl-L-serine → phosphatidylethanolamine + CO2 is the phosphatidylserine decarboxylase reaction.

*Mechanism source: mechanism card 'plp_amino_acid_decarboxylase'.*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 6% of Gemma4EC's attention (x3.5, enriched on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 4.1.1.65 leads the similarity ranking clearly; no database entry with these exact participants; mechanism from a class reference).


---

## Reaction 61: Gemma4EC predicts EC 6.3.5 (true 6.3.5, correct)

`Nc1nc2c(ncn2[C@@H]2O[C@H](COP(=O)([O-])[O-])[C@@H](O)[C@H]2O)c(=O)[nH]1.Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])[O-])[C@@H](O)[C@H]1O.O=P([O-])([O-])OP(=O)([O-])O>>NC(=O)CC[C@H]([NH3+])C(=O)[O-]`

**What happens.** GMP + AMP + diphosphate → L-glutamine + XMP + ATP + H2O. Participants not in the record (XMP, ATP, H2O) were added from MetaNetX reaction MNXR180538.

**Bond changes (atom mapping).**
- new single bond O22 (O- of GMP) – P29 (P of diphosphate)
- new single bond O23 (O of AMP) – P29 (P of diphosphate)
- broken single bond O23 (O of AMP) – C47 (CH2 of AMP)
- broken single bond C1 (C of GMP) – N (NH2 of GMP) (N side leaves)
- broken double bond C5 (C of GMP) – O (O of GMP) (O side leaves)
- broken single bond C31 (C of AMP) – N (NH2 of AMP) (N side leaves)
- broken single bond P29 (P of diphosphate) – O (O- of diphosphate) (O side leaves)
- broken single bond P29 (P of diphosphate) – O (O of diphosphate) (O side leaves)
- C1 (C of GMP) gains 1 H
- N6 (NH of GMP) loses 1 H
- O22 (O- of GMP) charge -1 → +0
- N32 (N of AMP) gains 1 H
- C33 (CH of AMP) loses 1 H
- N34 (N of AMP) gains 1 H

**Enzyme.** EC 6.3.5.2 GMP synthase (glutamine-hydrolysing) (0/0 votes; candidates: 6.3.5.2, 6.3.4.1, 6.1.1.18, 6.3.5.1, 6.3.5.4).

**Mechanism.** The record looks inconsistent because it implies GMP is formed from AMP and diphosphate, but the mechanism only shows GMP arising from XMP and ATP. The beta-phosphate of ATP is deprotonated, which makes the alpha-phosphate more electrophilic, so the XMP substrate can attack it. This eliminates pyrophosphate and forms an intermediate. Histidine protonates a cysteine, which then attacks L-glutamine, forming a covalent bond. This intermediate collapses, releasing ammonia which gets passed between two histidines. Finally, the negatively charged intermediate is protonated by the phosphate group, activating it for nucleophilic attack by AMP. This releases AMP and GMP.
**Why EC 6.3.5.2.** the reaction makes GMP from XMP and ATP (EC 6.3.5.2), with diphosphate and AMP also formed; this matches only part of the record.

*Mechanism source: M-CSA entry 234.*

**Attention.** the reaction-centre atoms are 18% of all heavy atoms and received 10% of Gemma4EC's attention (x0.6, depleted on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** The product has 19 atom(s) with no source in the reactants: the record is unbalanced or mis-drawn.

**Confidence: high** (EC 6.3.5.2 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism from the M-CSA entry for this enzyme; 1 data caveat(s)).


---

## Reaction 62: Gemma4EC predicts EC 2.3.1 (true 2.3.1, correct)

`CC/C=C\C/C=C\C/C=C\C/C=C\CCCCCCC(=O)O[C@@H](CO)COC(=O)CCCCCCCCCCCCCC.CCCCC/C=C\C/C=C\C/C=C\C/C=C\C/C=C\CCC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)(O)O>>CC/C=C\C/C=C\C/C=C\C/C=C\CCCCCCC(=O)O[C@H](COC(=O)CC/C=C\C/C=C\C/C=C\C/C=C\C/C=C\CCCCC)COC(=O)CCCCCCCCCCCCCC`

**What happens.** 1-pentadecanoyl-2-(8Z,11Z,14Z,17Z-eicosatetraen… + (4Z,7Z,10Z,13Z,16Z)-docosapentaenoyl-CoA → 1-(4Z,7Z,10Z,13Z,16Z-docosapentaenoyl)-2-(8Z,11… (+ CoA, not listed in the record). (4Z,7Z,10Z,13Z,16Z)-docosapentaenoyl-CoA donates its acyl group; CoA is released.

**Bond changes (atom mapping).**
- new single bond O25 (OH of 1-pentadecanoyl-2-(8Z,11Z,14Z,17Z-eicos…) – C26 (C of (4Z,7Z,10Z,13Z,16Z)-docosapentaenoyl-CoA)
- broken single bond C26 (C of (4Z,7Z,10Z,13Z,16Z)-docosapentaenoyl-CoA) – S (S of (4Z,7Z,10Z,13Z,16Z)-docosapentaenoyl-CoA) (S side leaves)
- O25 (OH of 1-pentadecanoyl-2-(8Z,11Z,14Z,17Z-eicos…) loses 1 H

**Enzyme.** EC 2.3.1.20 diacylglycerol O-acyltransferase (0/0 votes; candidates: 2.3.1.20, 2.3.1.15, 2.3.1.51, 2.3.1.22, 2.3.1.74).

**Mechanism.** The mechanism is assumed by analogy to the acyl-CoA:alcohol O-acyltransferase. The hydroxyl group O25 of the first acyl group attacks the thioester carbonyl carbon of the (4Z,7Z,10Z,13Z,16Z)-docosapentaenoyl-CoA. A conserved active-site His acts as a general base, deprotonating O25. This leads to a tetrahedral intermediate that collapses, expelling the CoA thiolate (forming CoA-SH) and forming the ester bond between the two acyl groups.  The new bond is between O25 and C26, and the CoA-SH is the leaving group.
**Why EC 2.3.1.20.** the enzyme transfers an acyl group from CoA to a 1,2-diacylglycerol (this is a sn-glycerol with acyl groups at carbons 1 and 2), forming a triacylglycerol and releasing CoA.

*Mechanism source: mechanism card 'acyl_coa_o_acyltransferase'.*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 1% of Gemma4EC's attention (x0.5, depleted on the reaction centre); cofactor/cosubstrate atoms received 28%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 2.3.1.20 leads the similarity ranking clearly; no database entry with these exact participants; mechanism from a class reference).


---

## Reaction 63: Gemma4EC predicts EC 5.3.1 (true 5.3.1, correct)

`OC[C@H]1OC(O)[C@@H](O)[C@H](O)[C@@H]1O>>O=C(CO)[C@H](O)[C@H](O)[C@H](O)CO`

**What happens.** D-altropyranose → D-allulose.

**Bond changes (atom mapping).**
- changed bond O1 (O of D-altropyranose) – C2 (CH of D-altropyranose): single → double
- broken single bond O1 (O of D-altropyranose) – C11 (CH of D-altropyranose)
- C2 (CH of D-altropyranose) loses 1 H
- C11 (CH of D-altropyranose) gains 1 H

**Enzyme.** EC 5.3.1.15 D-lyxose ketol-isomerase (1/1 votes; candidates: 5.1.3.3, 3.2.1.146, 3.2.1.23, 5.3.1.15, 5.3.1.3).

**Mechanism.**** The mechanism is assumed by analogy to xylose isomerase. The first step likely involves the ring opening of D-altropyranose, similar to the mechanism described for xylose isomerase. Subsequently, a 1,2-hydride shift might occur, potentially mediated by a divalent cationic metal cofactor. This shift could involve a hydroxide anion as a base, resulting in the transfer of a hydrogen atom from C11 to C2 and the formation of a double bond between C2 and O1. The sugar then closes back into a ring. This is consistent with the observed changes: C11 gains a H, the double bond shifts from O1-C2 to O2-C1, and C2 loses a H. However, the exact mechanism and the involvement of a metal cofactor require further investigation.

****Why EC 5.3.1.15.**** The enzyme catalyzes the isomerization of a sugar at the C1 position (EC 5.3.1), and the transformation of D-altropyranose to D-allulose does involve a change at the C1 position. However, the provided information does not definitively confirm that this specific enzyme is responsible for the observed reaction. The analogy to xylose isomerase suggests a possible mechanism, but experimental validation is needed to confirm the identity and role of the enzyme.

*Mechanism source: M-CSA entry 308 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 25% of all heavy atoms and received 22% of Gemma4EC's attention (x0.9, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (1/1 votes for EC 5.3.1.15; no database entry with these exact participants; mechanism by analogy to a related enzyme).


---

## Reaction 64: Gemma4EC predicts EC 4.1.1 (true 4.1.1, correct)

`CCCCCCCC/C=C\CCCCCCCC(=O)OC[C@H](COP(=O)(O)OC[C@H](N)C(=O)O)OC(=O)CCCCCCCCCCCCCCCCCCCCC>>CCCCCCCC/C=C\CCCCCCCC(=O)OC[C@H](COP(=O)(O)OCCN)OC(=O)CCCCCCCCCCCCCCCCCCCCC`

**What happens.** 1-(9Z-octadecenoyl)-2-docosanoyl-sn-glycero-3-p… → 1-(9Z-octadecenoyl)-2-docosanoyl-sn-glycero-3-p… (+ CO2, not listed in the record).

**Bond changes (atom mapping).**
- broken single bond C30 (CH of 1-(9Z-octadecenoyl)-2-docosanoyl-sn-gly…) – C (C of 1-(9Z-octadecenoyl)-2-docosanoyl-sn-gly…) (C side leaves)
- C30 (CH of 1-(9Z-octadecenoyl)-2-docosanoyl-sn-gly…) gains 1 H

**Enzyme.** EC 4.1.1.65 phosphatidylserine decarboxylase (0/0 votes; candidates: 4.1.1.65, 4.1.1.104, 4.1.1.48, 4.1.1.32, 4.1.1.39).

**Mechanism.** The alpha-amino group of the phosphatidyl-L-serine is displaced by an active-site Lys to form an external aldimine (transaldimination). This breaks the bond between C30 and the carboxylate, held perpendicularly to the PLP pyridine ring, and CO2 is released. PLP acts as an electron sink, delocalising the negative charge into the protonated pyridine ring (quinonoid intermediate). Protonation of C30 then occurs, and a second transaldimination by the reactivated Lys releases ethanolamine and regenerates the internal PLP-Lys aldimine.  The product is phosphatidylethanolamine.
**Why EC 4.1.1.65.** a carboxyl group is removed as CO2 by decarboxylation (EC 4.1.1), and phosphatidyl-L-serine = phosphatidylethanolamine + CO2 is the phosphatidylserine decarboxylase reaction.

*Mechanism source: mechanism card 'plp_amino_acid_decarboxylase'.*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 5% of Gemma4EC's attention (x2.6, enriched on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 4.1.1.65 leads the similarity ranking clearly; no database entry with these exact participants; mechanism from a class reference).


---

## Reaction 65: Gemma4EC predicts EC 6.2.1 (true 6.2.1, correct)

`CC(C)(COP(=O)([O-])OP(=O)([O-])OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)([O-])[O-])[C@@H](O)C(=O)NCCC(=O)NCCS.Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])OP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]1O.O=C([O-])CCCCCCCCCCCCCCCCCO>>O=P([O-])([O-])OP(=O)([O-])O`

**What happens.** 18-hydroxyoctadecanoate + CoA + ATP → diphosphate + 18-hydroxystearoyl-CoA + AMP. Participants not in the record (18-hydroxystearoyl-CoA, AMP) were added from MetaNetX reaction MNXR120055. CoA is the CoA acceptor/leaving group; ATP is the phosphoryl/adenylyl donor.

**Bond changes (atom mapping).**
- new single bond P2 (P of ATP) – O3 (O- of 18-hydroxyoctadecanoate)
- broken single bond P2 (P of ATP) – O96 (O of ATP)
- broken single bond O3 (O- of 18-hydroxyoctadecanoate) – C58 (C of 18-hydroxyoctadecanoate)
- new single bond S57 (SH of CoA) – C58 (C of 18-hydroxyoctadecanoate)
- O9 (O- of ATP) gains 1 H and charge -1 → +0
- S57 (SH of CoA) loses 1 H
- O96 (O of ATP) charge +0 → -1

**Enzyme.** EC 6.2.1.3 long-chain-fatty-acid-CoA ligase (0/0 votes; candidates: 6.2.1.3, 6.2.1.12, 6.2.1.2, 6.2.1.1, 6.2.1.25).

**Mechanism.** The carboxyl group of 18-hydroxyoctadecanoate attacks the alpha-phosphorus atom of ATP, forming a negatively charged, penta-coordinated intermediate (this matches the "carbonyl oxygen... nucleophilically attacks the alpha-phosphorus atom" step of the reference). A Trp residue (aided by Mg(II)) stabilizes this intermediate through hydrogen bonding. The P-O bond breaks, releasing diphosphate and forming a fatty-acyl-AMP intermediate (forming the new bonds P2-O3 and S57-C58). This intermediate collapses, expelling AMP and forming the final product, 18-hydroxystearoyl-CoA, along with the leaving group pyrophosphate (O9 gains a H and loses a charge, O96 loses a charge and gains a H). 
**Why EC 6.2.1.3.** the CoA acceptor/leaving group is CoA, the phosphoryl/adenylyl donor is ATP, and this is a general description of the reaction catalyzed by long-chain-fatty-acid-CoA ligase (EC 6.2.1.3).

*Mechanism source: M-CSA entry 198.*

**Attention.** the reaction-centre atoms are 6% of all heavy atoms and received 16% of Gemma4EC's attention (x2.7, enriched on the reaction centre); cofactor/cosubstrate atoms received 33%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 6.2.1.3 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism from the M-CSA entry for this enzyme).


---

## Reaction 66: not explained

`CC(C)(COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)(O)O)[C@@H](O)C(=O)NCCC(=O)NCCS.CCCCC/C=C\C/C=C\CCCCCCCC(=O)O.Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)(O)OP(=O)(O)OP(=O)(O)O)[C@@H](O)[C@H]1O>>CC(C)(N)CO`

record fails the check: {"heavy_atoms_lost": 0.94, "n_bond_changes": 5, "unnamed_main": 0, "ok": false}

---

## Reaction 67: Gemma4EC predicts EC 2.7.8 (true 2.7.8, correct)

`CCC/C=C\CCCCCCCCCC(=O)OC[C@H](COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2ccc(N)nc2=O)C(O)[C@H]1O)OC(=O)CCCCCCC/C=C\CCCCCCCCCCCCCCCCC.CCCCCCCCCCCCCCCC(=O)OC[C@H](COP(=O)(O)OC[C@@H](O)CO)OC(=O)CCCCCCCCCCCCCCC>>CCC/C=C\CCCCCCCCCC(=O)OC[C@H](COP(=O)(O)OC[C@@H](O)COP(=O)(O)OC[C@@H](COC(=O)CCCCCCCCCCCCC)OC(=O)CCCCCCC/C=C\CCCC)OC(=O)CCCCCCC/C=C\CCCCCCCCCCCCCCCCC`

**What happens.** a CDP-diacylglycerol + 1,2-dihexadecanoyl-sn-glycero-3-phospho-(1'-sn-… → a cardiolipin (+ CMP, not listed in the record). a CDP-diacylglycerol donates its phospho-head group; CMP is released.

**Bond changes (atom mapping).**
- new single bond P22 (P of a CDP-diacylglycerol) – O25 (OH of 1,2-dihexadecanoyl-sn-glycero-3-phospho…)
- changed bond C93 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) – C94 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…): single → double
- broken single bond P22 (P of a CDP-diacylglycerol) – O (O of a CDP-diacylglycerol) (O side leaves)
- broken single bond C55 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) – C (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) (C side leaves)
- broken single bond C98 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) – C (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) (C side leaves)
- O25 (OH of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) loses 1 H
- C55 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) gains 1 H
- C93 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) loses 1 H
- C94 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) loses 1 H
- C98 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) gains 1 H

**Enzyme.** EC 2.7.8.41 cardiolipin synthase (CMP-forming) (4/5 votes; candidates: 2.7.8.41, 2.7.8.5, 2.7.8.8, 2.7.8.11, 2.7.8.24).

**Mechanism.** The record lists 4 separate substrate changes, which one enzymatic step rarely does, so it is inconsistent. However, the mechanism reference describes a single step where a CDP-diacylglycerol donates its phospho-head group to a phosphatidylglycerol. A conserved Asp acts as a general base and deprotonates the acceptor hydroxyl, which attacks the phosphorus atom of the CDP-diacylglycerol that is not bound to the cytidine nucleoside. This is an in-line SN2-type substitution. CMP is the leaving group. The product is a new phosphodiester linking the acceptor to the CDP group; CMP is usually omitted from the record. The mechanism reference provides no information about the changes at the other 3 sites listed in the record.
**Why EC 2.7.8.41.** this reaction is a phosphotransferase with a CMP-forming group (EC 2.7.8.41), which is consistent with the mechanism reference. The other part of the record is not included in the mechanism reference.

*Mechanism source: mechanism card 'cdp_alcohol_phosphotransferase'.*

**Attention.** the reaction-centre atoms are 5% of all heavy atoms and received 4% of Gemma4EC's attention (x0.7, depleted on the reaction centre); cofactor/cosubstrate atoms received 21%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** The substrate changes at 4 separate sites, which a single enzymatic step rarely does: the record may merge several steps.

**Confidence: medium** (4/5 votes for EC 2.7.8.41; no database entry with these exact participants; mechanism from a class reference; 1 data caveat(s)).


---

## Reaction 68: Gemma4EC predicts EC 6.2.1 (true 6.2.1, correct)

`CC(C)(COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)(O)O)[C@@H](O)C(=O)NCCC(=O)NCCS.Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)(O)OP(=O)(O)OP(=O)(O)O)[C@@H](O)[C@H]1O.O=C([O-])CCC(=O)c1ccccc1C(=O)[O-]>>O=P([O-])([O-])OP(=O)([O-])[O-]`

**What happens.** 2-succinylbenzoate + CoA + ATP → diphosphate + 2-succinylbenzoyl-CoA + AMP. Participants not in the record (2-succinylbenzoyl-CoA, AMP) were added from MetaNetX reaction MNXR146487. CoA is the CoA acceptor/leaving group; ATP is the phosphoryl/adenylyl donor.

**Bond changes (atom mapping).**
- new single bond P2 (P of ATP) – O3 (O- of 2-succinylbenzoate)
- broken single bond P2 (P of ATP) – O91 (O of ATP)
- broken single bond O3 (O- of 2-succinylbenzoate) – C58 (C of 2-succinylbenzoate)
- new single bond S57 (SH of CoA) – C58 (C of 2-succinylbenzoate)
- O4 (OH of ATP) loses 1 H and charge +0 → -1
- O8 (OH of ATP) loses 1 H and charge +0 → -1
- O9 (OH of ATP) loses 1 H and charge +0 → -1
- O17 (OH of CoA) loses 1 H and charge +0 → -1
- O21 (OH of CoA) loses 1 H and charge +0 → -1
- O43 (OH of CoA) loses 1 H and charge +0 → -1
- O44 (OH of CoA) loses 1 H and charge +0 → -1
- S57 (SH of CoA) loses 1 H
- O90 (OH of ATP) loses 1 H and charge +0 → -1
- O91 (O of ATP) charge +0 → -1

**Enzyme.** EC 6.2.1.26 O-succinylbenzoate-CoA ligase (0/0 votes; candidates: 6.2.1.26, 6.2.1.12, 6.2.1.2, 6.2.1.1, 6.2.1.25).

**Mechanism.** The phosphate group of ATP is transferred from O91 to O3 of 2-succinylbenzoate, breaking the P2–O91 bond and forming a new P2–O3 bond. This is accompanied by the simultaneous loss of a proton from O3, giving it a negative charge. Concurrently, the thiol group of CoA (S57) attacks C58 of 2-succinylbenzoate, breaking the O3–C58 bond and forming a new S57–C58 bond. This also involves proton loss from S57, giving it a negative charge. The remaining phosphate group of ATP is now linked to O90, and the O4, O8, and O9 hydroxyl groups of ATP are all protonated. The product diphosphate results from the elimination of the pyrophosphate group from ATP.
**Why EC 6.2.1.26.** the reaction involves the formation of an ester bond by transferring a group from a carboxylic acid (2-succinylbenzoate) to the thiol group of CoA (EC 6.2.1), and ATP is the phosphate donor and the leaving group (EC 6.2.1.26).

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 14% of all heavy atoms and received 28% of Gemma4EC's attention (x2.0, enriched on the reaction centre); cofactor/cosubstrate atoms received 26%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 6.2.1.26 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 69: Gemma4EC predicts EC 1.14.14 (true 1.14.14, correct)

`CCCCCC1OC1/C=C/C(O)C/C=C\C/C=C\CCCC(=O)O.O>>CCCCCC(O)C(O)/C=C/C(O)C/C=C\C/C=C\CCCC(=O)O`

**What happens.** 11H-14,15-EETA → 11,14,15-trihydroxy-(5Z,8Z,12E)-icosatrienoic a….

**Bond changes (atom mapping).**
- broken single bond O7 (O of 11H-14,15-EETA) – C8 (CH of 11H-14,15-EETA)
- new single bond C8 (CH of 11H-14,15-EETA) – O9 (OH2 of H2O)
- O7 (O of 11H-14,15-EETA) gains 1 H
- O9 (OH2 of H2O) loses 1 H

**Enzyme.** EC 1.14.14.1 unspecific monooxygenase (0/0 votes; candidates: 1.14.14.1, 1.14.14.94, 1.14.14.87, 1.14.14.93, 1.14.14.135).

**Mechanism.** The reaction is the reverse of the one described in the reference, so the steps are run in reverse. The Fe(II) in the P450 haem is oxidised back to Fe(III) by dioxygen, and a second electron is passed to the haem, forming a superoxide species. This is followed by proton donation by catalytic water, which matches the computed changes: O7 of 11H-14,15-EETA gains one H and becomes OH, while O9 of H2O loses one H and becomes part of a new single bond with C8 of 11H-14,15-EETA. 
**Why EC 1.14.14.1.** the enzyme uses NADPH as an electron donor and forms a hydroxyl group from O2 (EC 1.14.14.1), and 11H-14,15-EETA + [oxidized NADPH-hemoprotein reductase] + O2 = 11,14,15-trihydroxy-(5Z,8Z,12E)-icosatrienoic acid… + [reduced NADPH-hemoprotein reductase] + H2O is the unspecific monooxygenase reaction.

*Mechanism source: M-CSA entry 699.*

**Attention.** the reaction-centre atoms are 12% of all heavy atoms and received 18% of Gemma4EC's attention (x1.5, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 1.14.14.1 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism from the M-CSA entry for this enzyme).


---

## Reaction 70: Gemma4EC predicts EC 1.3.1 (true 1.3.1, correct)

`NC(=O)c1ccc[n+]([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)c1.O=C([O-])C(=O)C[C@]1(C(=O)[O-])C=C[C@@H](O)C=C1>>O=C([O-])C(=O)Cc1ccc(O)cc1`

**What happens.** prephenate + NAD(+) → 3-(4-hydroxyphenyl)pyruvate + NADH + CO2. Participants not in the record (NADH, CO2) were added from MetaNetX reaction MNXR146103. NAD(+) accepts a hydride and becomes NADH.

**Bond changes (atom mapping).**
- broken single bond C7 (?, C) – C59 (?, C)
- changed bond C59 (?, C) – O60 (?, O-): single → double
- C10 (?, CH) loses 1 H
- N19 (N+ of NAD(+)) charge +1 → +0
- C57 (CH of NAD(+)) gains 1 H
- O60 (?, O-) charge -1 → +0

**Enzyme.** EC 1.3.1.12 prephenate dehydrogenase (0/0 votes; candidates: 1.3.1.12, 1.3.1.13, 1.3.1.121, 1.1.1.110, 1.1.1.222).

**Mechanism.** The prochiral bridge carbon of prephenate is deprotonated by an Asp acting as a general base, and the resulting hydride is transferred to the nicotinamide ring of NAD+, forming NADH. This matches the computed changes: C7–C59 bond broken, C59–O60 bond formed, C10 loses a hydrogen, and N19 gains a hydrogen, neutralizing its positive charge.  Additionally, C57 of NAD+ gains a hydrogen.  This mechanism is assumed by analogy to the precorrin-2 dehydrogenase. 
**Why EC 1.3.1.12.** the enzyme catalyyses the oxidation of prephenate with NAD+ (EC 1.3.1.12), and prephenate + NAD+ = 4-hydroxyphenylpyruvate + CO2 + NADH is just this reaction.

*Mechanism source: M-CSA entry 610 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 7% of all heavy atoms and received 7% of Gemma4EC's attention (x1.0, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 14%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 1.3.1.12 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism by analogy to a related enzyme).


---

## Reaction 71: Gemma4EC predicts EC 1.3.8 (true 1.3.8, correct)

`CCCCC(=O)SCCNC(=O)CCNC(=O)C(O)C(C)(C)COP(=O)(O)OP(=O)(O)OCC1OC(n2cnc3c(N)ncnc32)C(O)C1OP(=O)(O)O.Cc1cc2nc3c(=O)[nH]c(=O)nc-3n(C[C@H](O)[C@H](O)[C@H](O)COP(=O)(O)OP(=O)(O)OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)c2cc1C>>Cc1cc2c(cc1C)N(CC(O)C(O)C(O)COP(=O)(O)OP(=O)(O)OCC1OC(n3cnc4c(N)ncnc43)C(O)C1O)c1[nH]c(=O)[nH]c(=O)c1N2`

**What happens.** pentanoyl-CoA + FAD → FADH2 (+ CoA, not listed in the record). FAD is an oxidised flavin electron acceptor; pentanoyl-CoA donates its acyl group; CoA is released.

**Bond changes (atom mapping).**
- N46 (N of FAD) gains 1 H
- N53 (N of FAD) gains 1 H

**Enzyme.** EC 1.3.8.1 short-chain acyl-CoA dehydrogenase (2/5 votes; candidates: 1.3.8.1, 1.3.8.4, 1.3.8.7, 1.3.8.6, 1.3.8.8).

**Mechanism.** The record is inconsistent, as it implies two separate changes at the same substrate site. We can only explain the part accounted for by this mechanism reference. A Glu residue abstracts a proton from the pentanoyl-CoA substrate, which then eliminates a hydride to the FAD cofactor, becoming FADH2. The reference does not show any bond changes other than N46 and N53 of FAD gaining one H each, which matches the computed changes, giving FADH2.
**Why EC 1.3.8.1.** this is a short-chain acyl-CoA dehydrogenase (EC 1.3.8.1), and the record mentions that it causes a trans-2,3-dehydroacyl-CoA to form from the pentanoyl-CoA substrate; however, it only describes a hydride transfer leading to reduced cofactor, not the full oxidation and rearrangement.

*Mechanism source: M-CSA entry 893 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 6% of Gemma4EC's attention (x2.4, enriched on the reaction centre); cofactor/cosubstrate atoms received 52%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** The substrate changes at 2 separate sites, which a single enzymatic step rarely does: the record may merge several steps.

**Confidence: low** (2/5 votes for EC 1.3.8.1; no database entry with these exact participants; mechanism by analogy to a related enzyme; 1 data caveat(s)).


---

## Reaction 72: Gemma4EC predicts EC 2.3.1 (true 2.3.1, correct)

`CCCCCC/C=C/CCCCCCCCCC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)C(O)[C@H]1OP(=O)(O)O.CCCCCCCCCCCCCCCCCCCCCC(=O)O[C@@H](CO)COC(=O)CCCCCCCCCCCCCCC>>CCCCCC/C=C\CCCCCCCCCC(=O)OC[C@H](COC(=O)CCCCCCCCCCCCCCC)OC(=O)CCCCCCCCCCCCCCCCCCCCC`

**What happens.** Vaccenyl coenzyme A + 1-hexadecanoyl-2-docosanoyl-sn-glycerol → 1-(11Z-octadecenoyl)-2-docosanoyl-3-hexadecanoy… (+ CoA, not listed in the record). Vaccenyl coenzyme A donates its acyl group; CoA is released.

**Bond changes (atom mapping).**
- new single bond C18 (C of Vaccenyl coenzyme A) – O46 (OH of 1-hexadecanoyl-2-docosanoyl-sn-glycerol)
- broken single bond C18 (C of Vaccenyl coenzyme A) – S (S of Vaccenyl coenzyme A) (S side leaves)
- O46 (OH of 1-hexadecanoyl-2-docosanoyl-sn-glycerol) loses 1 H

**Enzyme.** EC 2.3.1.20 diacylglycerol O-acyltransferase (0/0 votes; candidates: 2.3.1.20, 2.3.1.15, 2.3.1.16, 2.3.1.292, 2.3.1.51).

**Mechanism.** The mechanism is assumed by analogy to the acyl-CoA:alcohol O-acyltransferase. The hydroxyl group of 1-hexadecanoyl-2-docosanoyl-sn-glycerol attacks the thioester carbonyl carbon of vaccenyl coenzyme A. A conserved active-site His acts as general base, deprotonating the hydroxyl group. This forms a tetrahedral intermediate that collapses, expelling the CoA thiolate (protonated to CoA-SH) and forming the ester bond between C18 of vaccenyl CoA and O46 of the glycerol.  This matches the computed changes: a new bond from C18 to O46 and the breaking of the C18-S bond, with the CoA part leaving. The O46 hydroxyl group loses a hydrogen.
**Why EC 2.3.1.20.** the enzyme transfers an acyl group from CoA to a 1,2-diacylglycerol (acyl-CoA + R-OH -> ester + CoA), which is exactly the diacylglycerol O-acyltransferase reaction.

*Mechanism source: mechanism card 'acyl_coa_o_acyltransferase'.*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 3% of Gemma4EC's attention (x1.2, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 23%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 2.3.1.20 leads the similarity ranking clearly; no database entry with these exact participants; mechanism from a class reference).


---

## Reaction 73: Gemma4EC predicts EC 3.1.2 (true 3.1.2, correct)

`CC(C)(COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)(O)O)[C@@H](O)C(=O)NCCC(=O)NCCSC(=O)CCC(=O)O.O>>O=C([O-])CCC(=O)[O-]`

**What happens.** succinyl-CoA → succinate + CoA. Participants not in the record (CoA) were added from MetaNetX reaction MNXR188876. succinyl-CoA donates its acyl group; CoA is released.

**Bond changes (atom mapping).**
- broken single bond S48 (S of succinyl-CoA) – C54 (C of succinyl-CoA)
- new single bond C54 (C of succinyl-CoA) – O56 (OH2 of H2O)
- O8 (OH of succinyl-CoA) loses 1 H and charge +0 → -1
- O12 (OH of succinyl-CoA) loses 1 H and charge +0 → -1
- O23 (OH of succinyl-CoA) loses 1 H and charge +0 → -1
- O24 (OH of succinyl-CoA) loses 1 H and charge +0 → -1
- S48 (S of succinyl-CoA) gains 1 H
- O51 (OH of succinyl-CoA) loses 1 H and charge +0 → -1
- O56 (OH2 of H2O) loses 2 H and charge +0 → -1

**Enzyme.** EC 3.1.2.3 succinyl-CoA hydrolase (5/5 votes; candidates: 3.1.2.2, 3.1.2.3, 6.2.1.4, 2.8.3.5, 3.1.2.13).

**Mechanism.** The bond changes show that the S48 of succinyl-CoA breaks with C54, forming a new O56-C54 bond with water, releasing it as H2O. Concurrently, O8, O12, O23, and O24 of succinyl-CoA each lose a proton, becoming negatively charged. S48 gains a proton. O51 of succinyl-CoA also loses a proton. 
**Why EC 3.1.2.3.** This reaction cleaves a thioester bond (EC 3.1.2) by adding water (EC 3.1.2.3), resulting in succinate and CoA.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 14% of all heavy atoms and received 33% of Gemma4EC's attention (x2.3, enriched on the reaction centre); cofactor/cosubstrate atoms received 22%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (5/5 votes for EC 3.1.2.3; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 75: Gemma4EC predicts EC 4.1.2 (true 4.1.2, correct)

`CCCC=O.[C-]#N>>CCCC(O)C#N`

**What happens.** butanal + cyanide → (2S)-2-hydroxypentanenitrile.

**Bond changes (atom mapping).**
- changed bond C4 (CH of butanal) – O5 (O of butanal): double → single
- new single bond C4 (CH of butanal) – C6 (C- of cyanide)
- O5 (O of butanal) gains 1 H
- C6 (C- of cyanide) charge -1 → +0

**Enzyme.** EC 4.1.2.47 (S)-hydroxynitrile lyase (5/5 votes; candidates: 4.1.2.10, 4.1.2.47, 4.1.2.46, 4.1.2.11, 4.1.2.52).

**Mechanism.** The butanal carbonyl group (C4=O) reacts with cyanide (CN-) non-stereospecifically to form an apparent cyanohydrin intermediate. A His residue abstracts a proton from Ser, which is then protonated by the hydroxyl group of the cyanohydrin. This facilitates elimination of HCN, generating (S)-2-hydroxypentanenitrile. The cyanide gains a positive charge and the butanal O5 loses a proton, as the double bond between C4 and O5 forms. 
**Why EC 4.1.2.47.** the reaction removes HCN from an (S)-hydroxynitrile, generating an aldehyde or ketone (butanal in this case), which matches the description of (S)-hydroxynitrile lyase.

*Mechanism source: M-CSA entry 217.*

**Attention.** the reaction-centre atoms are 43% of all heavy atoms and received 41% of Gemma4EC's attention (x0.9, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (5/5 votes for EC 4.1.2.47; no database entry with these exact participants; mechanism from the M-CSA entry for this enzyme).


---

## Reaction 76: Gemma4EC predicts EC 5.4.99 (true 5.4.99, correct)

`C=C(CCC(=O)[O-])C(=O)[O-]>>C=C(C(=O)[O-])C(C)C(=O)[O-]`

**What happens.** 2-methyleneglutarate → (R)-3-methylitaconate.

**Bond changes (atom mapping).**
- new single bond C2 (C of 2-methyleneglutarate) – C6 (CH2 of 2-methyleneglutarate)
- broken single bond C2 (C of 2-methyleneglutarate) – C7 (CH2 of 2-methyleneglutarate)
- C6 (CH2 of 2-methyleneglutarate) loses 1 H
- C7 (CH2 of 2-methyleneglutarate) gains 1 H

**Enzyme.** EC 5.4.99.4 2-methyleneglutarate mutase (0/0 votes; candidates: 5.4.99.4, 5.4.99.1, 5.4.99.3, 5.4.99.58, 5.4.99.14).

**Mechanism.** The bond between C2 and C7 of 2-methyleneglutarate is broken, and a new bond is formed between C2 and C6. Simultaneously, C6 loses a hydrogen, which is gained by C7. In other words, the double bond between C2 and C7 is replaced by a single bond between C2 and C6, and a single bond between C6 and C7. 
**Why EC 5.4.99.4.** This reaction involves the isomerization of a γ-keto acid (2-methyleneglutarate) to a 4-keto acid (2-methylene-3-methylsuccinate), which is characteristic of mutase EC 5.4.99.4.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 30% of all heavy atoms and received 14% of Gemma4EC's attention (x0.5, depleted on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 5.4.99.4 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 77: Gemma4EC predicts EC 1.1.1 (true 1.1.1, correct)

`CC(=O)C=O.NC(=O)C1=CN([C@@H]2O[C@H](COP(=O)(O)OP(=O)(O)OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](OP(=O)(O)O)[C@@H]3O)[C@@H](O)[C@H]2O)C=CC1.[H+]>>CC(O)C=O`

**What happens.** methylglyoxal + NADPH → lactaldehyde + NADP(+). Participants not in the record (NADP(+)) were added from MetaNetX reaction MNXR101007. NADPH supplies the reducing equivalents (electrons) and becomes NADP+.

**Bond changes (atom mapping).**
- changed bond C2 (C of methylglyoxal) – O3 (O of methylglyoxal): double → single
- C2 (C of methylglyoxal) gains 1 H
- O3 (O of methylglyoxal) gains 1 H
- C10 (CH2 of NADPH) loses 1 H
- N13 (N of NADPH) charge +0 → +1
- O21 (OH of NADPH) loses 1 H and charge +0 → -1
- O25 (OH of NADPH) loses 1 H and charge +0 → -1
- O45 (OH of NADPH) loses 1 H and charge +0 → -1
- O46 (OH of NADPH) loses 1 H and charge +0 → -1

**Enzyme.** EC 1.1.1.283 methylglyoxal reductase (NADPH) (0/0 votes; candidates: 1.1.1.283, 1.1.1.78, 1.1.1.169, 1.1.1.270, 1.1.1.42).

**Mechanism.** The pro-S hydride of NADPH is transferred from its C4 to the C2 carbonyl of methylglyoxal. The developing alkoxide on C2 is protonated by a general acid (a His in the reference), forming the alcohol. Concurrently, the NADPH loses its reducing equivalents to become NADP+, with the N13, O21, O25, O45 and O46 gaining one proton each. This matches the computed changes: the C2=O double bond of methylglyoxal becomes a C2-OH single bond and C2 and O3 each gain one H.
**Why EC 1.1.1.283.** the enzyme reduces a ketone (methylglyoxal) using NADPH (EC 1.1.1), and methylglyoxal + NADPH = 2-oxopropanal + NADP+ + H+ is the methylglyoxal reductase reaction.

*Mechanism source: M-CSA entry 721 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 15% of all heavy atoms and received 14% of Gemma4EC's attention (x0.9, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 17%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 1.1.1.283 leads the similarity ranking clearly; no database entry with these exact participants; mechanism by analogy to a related enzyme).


---

## Reaction 78: not explained

`*CC1OC(n2cnc3c(N)ncnc32)C(OC(=O)C([NH3+])CCCC[NH3+])C1O.Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])[O-])[C@@H](O)[C@H]1O.O=P([O-])([O-])OP(=O)([O-])O>>[NH3+]CCCC[C@H]([NH3+])C(=O)[O-]`

record fails the check: {"heavy_atoms_lost": 0.83, "n_bond_changes": 2, "unnamed_main": 1, "ok": false}

---

## Reaction 79: Gemma4EC predicts EC 4.2.1 (true 5.4.4, WRONG)

`CCCCC/C=C\C/C=C\C=C\[C@H](C/C=C\CCCC(=O)[O-])OO>>CCCCC/C=C\C/C=C\C=C\C(=O)C/C=C\CCCC(=O)[O-]`

**What happens.** (8S)-hydroperoxy-(5Z,9E,11Z,14Z)-eicosatetraeno… → 8-oxo-(5Z,9E,11Z,14Z)-eicosatetraenoate + H2O. Participants not in the record (H2O) were added from MetaNetX reaction MNXR119026.

**Bond changes (atom mapping).**
- changed bond C13 (CH of (8S)-hydroperoxy-(5Z,9E,11Z,14Z)-eicosa…) – O14 (O of (8S)-hydroperoxy-(5Z,9E,11Z,14Z)-eicosa…): single → double
- broken single bond O14 (O of (8S)-hydroperoxy-(5Z,9E,11Z,14Z)-eicosa…) – O24 (OH of (8S)-hydroperoxy-(5Z,9E,11Z,14Z)-eicosa…)
- C13 (CH of (8S)-hydroperoxy-(5Z,9E,11Z,14Z)-eicosa…) loses 1 H
- O24 (OH of (8S)-hydroperoxy-(5Z,9E,11Z,14Z)-eicosa…) gains 1 H

**Enzyme.** EC 4.2.1.152 hydroperoxy icosatetraenoate dehydratase (0/0 votes; candidates: 4.2.1.152, 4.2.1.92, 4.2.1.121, 4.2.1.183, 4.2.1.106).

**Mechanism.** The C13–O14 single bond in the hydroperoxyicosatetraenoate is broken and a double bond is formed between C13 and C14. Simultaneously, the O14–O24 single bond is broken, and O24 gains a hydrogen to become OH. The loss of O14 as H2O matches the addition of H to O24. The mechanism is assumed by analogy.
**Why EC 4.2.1.152.** the reaction removes a water molecule from a hydroperoxyicosatetraenoate (dehydration, EC 4.2.1.x), and hydroperoxyicosatetraenoate = oxoicosatetraenoate + H2O is the specific reaction.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 12% of all heavy atoms and received 24% of Gemma4EC's attention (x1.9, enriched on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 4.2.1.152 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 80: not explained

`CC(=O)N(O)CCCCC(N)C(=O)O.Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)(O)OP(=O)(O)OP(=O)(O)O)[C@@H](O)[C@H]1O.O.O=C([O-])CC(O)(CC(=O)[O-])C(=O)[O-]>>CC(=O)N(O)CCCCC(NC(=O)CC(O)(CC(=O)O)C(=O)O)C(=O)O`

record fails the check: {"heavy_atoms_lost": 0.56, "n_bond_changes": 5, "unnamed_main": 0, "ok": false}

---

## Reaction 81: Gemma4EC predicts EC 1.1.1 (true 1.1.1, correct)

`CC1CCC(=O)CC1.NC(=O)C1=CN([C@@H]2O[C@H](COP(=O)(O)OP(=O)(O)OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](OP(=O)(O)O)[C@@H]3O)[C@@H](O)[C@H]2O)C=CC1.[H+]>>CC1CCC(O)CC1`

**What happens.** 4-methylcyclohexanone + NADPH → 4-methylcyclohexan-1-ol + NADP(+). Participants not in the record (NADP(+)) were added from MetaNetX reaction MNXR172563. NADPH supplies the reducing equivalents (electrons) and becomes NADP+.

**Bond changes (atom mapping).**
- changed bond C5 (C of 4-methylcyclohexanone) – O6 (O of 4-methylcyclohexanone): double → single
- C5 (C of 4-methylcyclohexanone) gains 1 H
- O6 (O of 4-methylcyclohexanone) gains 1 H
- C13 (CH2 of NADPH) loses 1 H
- N16 (N of NADPH) charge +0 → +1
- O24 (OH of NADPH) loses 1 H and charge +0 → -1
- O28 (OH of NADPH) loses 1 H and charge +0 → -1
- O48 (OH of NADPH) loses 1 H and charge +0 → -1
- O49 (OH of NADPH) loses 1 H and charge +0 → -1

**Enzyme.** EC 1.1.1.206 tropinone reductase I (0/0 votes; candidates: 1.1.1.206, 1.1.1.169, 1.1.1.270, 1.1.1.42, 1.1.1.44).

**Mechanism.** The pro-S hydride of NADPH is transferred from C13 to the C5 carbonyl of 4-methylcyclohexanone, which matches the computed changes: the C5–O6 double bond becomes single and C5 and O6 each gain one H. The developing alkoxide is protonated by a Lys. NADP+ then picks up the electrons and protons lost by NADPH: N16 gains a charge, O24, O28, O48, and O49 each gain a charge, and the molecule gains an overall positive charge to become NADP+.
**Why EC 1.1.1.206.** this reaction reduces a ketone to an alcohol with NADPH (EC 1.1.1), and 4-methylcyclohexanone + NADP+ = 4-methylcyclohexan-1-ol + NADP+ is the tropinone reductase I reaction.

*Mechanism source: M-CSA entry 721 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 14% of all heavy atoms and received 19% of Gemma4EC's attention (x1.3, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 16%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 1.1.1.206 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism by analogy to a related enzyme).


---

## Reaction 82: Gemma4EC predicts EC 2.3.1 (true 2.3.1, correct)

`CCCCCC/C=C\CCCCCCCC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)(O)O.CCCCCCCC/C=C\CCCCCCCCCCCCCC(=O)O[C@@H](CO)COC(=O)CCCCCCCCCCCCCC>>CCCCCC/C=C\CCCCCCCC(=O)OC[C@H](COC(=O)CCCCCCCCCCCCCC)OC(=O)CCCCCCCCCCCCC/C=C\CCCCCCCC`

**What happens.** (9Z)-hexadecenoyl-CoA + DG(15:0/24:1(15Z)/0:0) → 1-(9Z-hexadecenoyl)-2-(15Z-tetracosenoyl)-3-pen… (+ CoA, not listed in the record). (9Z)-hexadecenoyl-CoA donates its acyl group; CoA is released.

**Bond changes (atom mapping).**
- new single bond C16 (C of (9Z)-hexadecenoyl-CoA) – O46 (OH of DG(15:0/24:1(15Z)/0:0))
- broken single bond C16 (C of (9Z)-hexadecenoyl-CoA) – S (S of (9Z)-hexadecenoyl-CoA) (S side leaves)
- O46 (OH of DG(15:0/24:1(15Z)/0:0)) loses 1 H

**Enzyme.** EC 2.3.1.20 diacylglycerol O-acyltransferase (0/0 votes; candidates: 2.3.1.20, 2.3.1.15, 2.3.1.22, 2.3.1.51, 2.3.1.16).

**Mechanism.** The mechanism is assumed by analogy to the acyl-CoA:alcohol O-acyltransferase. The hydroxyl group of DG(15:0/24:1(15Z)/0:0) attacks the thioester carbonyl carbon of (9Z)-hexadecenoyl-CoA. A conserved active-site His acts as general base, deprotonating the hydroxyl. The tetrahedral oxyanion intermediate collapses expelling the CoA thiolate (protonated to CoA-SH) and forming the ester bond between C16 of the acyl group and O46 of DG(15:0/24:1(15Z)/0:0).  The other oxygen atom of O46 loses a hydrogen, matching the computed changes: a new C16-O46 bond and the C16-S bond broken with CoA leaving as the thiolate.
**Why EC 2.3.1.20.** the enzyme transfers an acyl group from CoA to a 1,2-diacylglycerol (acyl-CoA + R-OH -> ester + CoA), and (9Z)-hexadecenoyl-CoA + DG(15:0/24:1(15Z)/0:0) = 1-(9Z-hexadecenoyl)-2-(15Z-tetracosenoyl)-3-pen… + CoA is the diacylglycerol O-acyltransferase reaction.

*Mechanism source: mechanism card 'acyl_coa_o_acyltransferase'.*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 2% of Gemma4EC's attention (x0.7, depleted on the reaction centre); cofactor/cosubstrate atoms received 23%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 2.3.1.20 leads the similarity ranking clearly; no database entry with these exact participants; mechanism from a class reference).


---

## Reaction 83: not explained

`CC(C)(COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)(O)O)[C@@H](O)C(=O)NCCC(=O)NCCS.CCCCCCCCCCCC(=O)[O-].Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)(O)OP(=O)(O)OP(=O)(O)O)[C@@H](O)[C@H]1O>>CC(C)(N)CO`

record fails the check: {"heavy_atoms_lost": 0.94, "n_bond_changes": 5, "unnamed_main": 0, "ok": false}

---

## Reaction 84: Gemma4EC predicts EC 3.5.2 (true 3.5.2, correct)

`NC(=O)NC1NC(=O)NC1=O.O>>NC(=O)NC(NC(N)=O)C(=O)O`

**What happens.** allantoin → allantoate.

**Bond changes (atom mapping).**
- broken single bond N1 (NH of allantoin) – C10 (C of allantoin)
- new single bond C10 (C of allantoin) – O12 (OH2 of H2O)
- N1 (NH of allantoin) gains 1 H
- O12 (OH2 of H2O) loses 1 H

**Enzyme.** EC 3.5.2.5 allantoinase (0/0 votes; candidates: 3.5.2.5, 5.1.99.3, 3.5.2.2, 3.5.2.16, 3.5.2.3).

**Mechanism.** The N1-C10 bond in allantoin is broken, and a new N1-H bond is formed with concomitant formation of a C10-O12 bond with a water molecule. This explains the computed changes: N1 gains a hydrogen, C10 gains an oxygen, and O12 gains a hydrogen.
**Why EC 3.5.2.5.** the reaction cleaves a cyclic amide (urea) ring (EC 3.5.2), and allantoin + H2O = allantoate is exactly the allantoinase reaction.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 25% of all heavy atoms and received 15% of Gemma4EC's attention (x0.6, depleted on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 3.5.2.5 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 85: Gemma4EC predicts EC 3.1.1 (true 3.1.1, correct)

`O.O=C1O[C@H](COP(=O)([O-])[O-])[C@@H](O)[C@H](O)[C@H]1O>>O=C([O-])[C@H](O)[C@@H](O)[C@H](O)[C@H](O)COP(=O)([O-])[O-]`

**What happens.** 6-phospho-D-glucono-1,5-lactone → 6-phospho-D-gluconate.

**Bond changes (atom mapping).**
- new single bond C2 (C of 6-phospho-D-glucono-1,5-lactone) – O3 (OH2 of H2O)
- broken single bond C2 (C of 6-phospho-D-glucono-1,5-lactone) – O11 (O of 6-phospho-D-glucono-1,5-lactone)
- new single bond C4 (CH of 6-phospho-D-glucono-1,5-lactone) – C6 (CH of 6-phospho-D-glucono-1,5-lactone)
- broken single bond C4 (CH of 6-phospho-D-glucono-1,5-lactone) – C8 (CH of 6-phospho-D-glucono-1,5-lactone)
- broken single bond C6 (CH of 6-phospho-D-glucono-1,5-lactone) – C10 (CH of 6-phospho-D-glucono-1,5-lactone)
- new single bond C8 (CH of 6-phospho-D-glucono-1,5-lactone) – C10 (CH of 6-phospho-D-glucono-1,5-lactone)
- O3 (OH2 of H2O) loses 2 H and charge +0 → -1
- O11 (O of 6-phospho-D-glucono-1,5-lactone) gains 1 H

**Enzyme.** EC 3.1.1.31 6-phosphogluconolactonase (0/0 votes; candidates: 3.1.1.31, 3.1.1.17, 3.1.1.99, 1.1.1.363, 1.1.1.49).

**Mechanism.** The lactone ring of 6-phospho-D-glucono-1,5-lactone is hydrolysed. The bond C2-O11 breaks, and a new bond forms between C2 and O3 of a water molecule, while O3 loses two H and gains a negative charge. Simultaneously, the bond C4-C8 breaks and a new bond forms between C8 and C10. The changes in the C4-C6-C8-C10 bonds rearrange these four atoms so that they now form a straight chain. 
**Why EC 3.1.1.31.** the reaction cleaves a cyclic anhydride (lactone) by adding water (hydrolysis, EC 3.1.1), and 6-phospho-D-glucono-1,5-lactone + H2O = 6-phospho-D-gluconate is exactly the 6-phosphogluconolactonase reaction.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 41% of all heavy atoms and received 44% of Gemma4EC's attention (x1.1, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 3.1.1.31 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 86: Gemma4EC predicts EC 5.4.2 (true 5.4.2, correct)

`O=P([O-])([O-])O[C@@H]1O[C@H](CO)[C@@H](O)[C@H](O)[C@H]1O>>O=P([O-])([O-])OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O`

**What happens.** beta-D-glucose 1-phosphate → D-glucose 6-phosphate.

**Bond changes (atom mapping).**
- new single bond P2 (P of beta-D-glucose 1-phosphate) – O5 (OH of beta-D-glucose 1-phosphate)
- broken single bond P2 (P of beta-D-glucose 1-phosphate) – O10 (O of beta-D-glucose 1-phosphate)
- O5 (OH of beta-D-glucose 1-phosphate) loses 1 H
- O10 (O of beta-D-glucose 1-phosphate) gains 1 H

**Enzyme.** EC 5.4.2.6 beta-Phosphoglucomutase (5/5 votes; candidates: 5.4.2.10, 5.4.2.6, 5.4.2.2, 5.4.2.5, 5.4.2.8).

**Mechanism.** The record describes two separate reactions as a single step, so it is inconsistent. According to the reference, an Asp residue abstracts a proton from the C2 hydroxyl group of the substrate, which then attacks a phosphate group on another Asp residue within the active site. This forms a pentavalent intermediate which collapses, eliminating the Asp residue in its unphosphorylated state and producing a bisphosphate intermediate. The bisphosphate intermediate then rotates, and another Asp residue attacks the C6 phosphate.  This forms another pentavalent intermediate which collapses, releasing the product, D-glucose 6-phosphate, and regenerating the phosphorylated Asp residue.
**Why EC 5.4.2.6.** this reaction involves the transfer of a phosphate group from one sugar to another (sugar-phosphate isomerization, EC 5.4.2), and beta-D-glucose 1-phosphate = beta-D-glucose 6-phosphate is exactly the beta-phosphoglucomutase reaction.

*Mechanism source: M-CSA entry 206.*

**Attention.** the reaction-centre atoms are 19% of all heavy atoms and received 16% of Gemma4EC's attention (x0.9, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** The substrate changes at 2 separate sites, which a single enzymatic step rarely does: the record may merge several steps.

**Confidence: high** (5/5 votes for EC 5.4.2.6; the exact reaction is listed for this EC in MetaNetX; mechanism from the M-CSA entry for this enzyme; 1 data caveat(s)).


---

## Reaction 87: Gemma4EC predicts EC 4.2.3 (true 4.2.3, correct)

`CC(C)=CCCC(C)=CCCC(C)=CCOP(=O)(O)OP(=O)(O)O.O>>C=CC(C)(O)CCC=C(C)CCC=C(C)C`

**What happens.** farnesyl diphosphate → nerolidol.

**Bond changes (atom mapping).**
- changed bond C1 (CH2 of farnesyl diphosphate) – C2 (CH of farnesyl diphosphate): single → double
- changed bond C2 (CH of farnesyl diphosphate) – C3 (C of farnesyl diphosphate): double → single
- new single bond C3 (C of farnesyl diphosphate) – O5 (OH2 of H2O)
- broken single bond C1 (CH2 of farnesyl diphosphate) – O (O of farnesyl diphosphate) (O side leaves)
- O5 (OH2 of H2O) loses 1 H

**Enzyme.** EC 4.2.3.48 (3S,6E)-nerolidol synthase (3/5 votes; candidates: 4.2.3.48, 4.2.3.49, 4.2.3.46, 4.2.3.47, 4.2.3.138).

**Mechanism.** The farnesyl diphosphate undergoes heterolysis, breaking the C1-O and C2-C3 bonds, and forming the (E,E)-humulyl cation. A 1,2-hydride shift occurs, likely directly, and the resulting protoilludyl cation undergoes a dyotropic rearrangement to form the nerolidol structure with a new C3-O5 bond. Finally, deprotonation of the nerolidol neutralizes the positive charge and completes the reaction. The pyrophosphate group acts as the general acid/base.
**Why EC 4.2.3.48.** this enzyme catalyses the formation of a new C-O bond (EC 4.2.3) from a diphosphate donor (EC 4.2.3.48), specifically in a terpene biosynthesis pathway, as is the pentalenene synthase reference.

*Mechanism source: M-CSA entry 89 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 20% of all heavy atoms and received 17% of Gemma4EC's attention (x0.9, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: low** (3/5 votes for EC 4.2.3.48; no database entry with these exact participants; mechanism by analogy to a related enzyme).


---

## Reaction 88: Gemma4EC predicts EC 3.6.3 (true 7.4.2, WRONG)

`CC(C)C[C@H]([NH3+])C(=O)[O-].Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])OP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]1O.O>>O=P([O-])([O-])O`

**What happens.** L-leucine + N(3)-fumaramoyl-(S)-2,3-diaminopropanoate + ATP → phosphate + dapdiamide C + ADP. Participants not in the record (N(3)-fumaramoyl-(S)-2,3-diaminopropanoa…, dapdiamide C, ADP) were added from MetaNetX reaction MNXR114252. ATP is the phosphoryl/adenylyl donor.

**Bond changes (atom mapping).**
- new single bond P2 (P of ATP) – O4 (O- of N(3)-fumaramoyl-(S)-2,3-diaminopropanoa…)
- broken single bond P2 (P of ATP) – O50 (O of ATP)
- broken single bond O4 (O- of N(3)-fumaramoyl-(S)-2,3-diaminopropanoa…) – C12 (C of N(3)-fumaramoyl-(S)-2,3-diaminopropanoa…)
- new single bond N11 (NH3+ of L-leucine) – C12 (C of N(3)-fumaramoyl-(S)-2,3-diaminopropanoa…)
- O5 (O- of ATP) gains 1 H and charge -1 → +0
- N11 (NH3+ of L-leucine) loses 2 H and charge +1 → +0
- O50 (O of ATP) charge +0 → -1

**Enzyme.** EC 6.3.2.47 dapdiamide synthase (0/0 votes; candidates: 6.3.2.47).

**Mechanism.** ATP is first activated by transferring its gamma-phosphate (O50) to the hydroxyl group of N(3)-fumaramoyl-(S)-2,3-diaminopropanoate, breaking the P2-O50 bond and forming a new P2-O4 bond. This leaves the 5'-pyrophosphate (O5) with a negative charge. L-leucine then donates its amino group (N11) to the C12 of N(3)-fumaramoyl-(S)-2,3-diaminopropanoate, forming a new C-N bond and releasing two protons from the leucine nitrogen, turning it into a neutral amine. Finally, the 5'-pyrophosphate gains a proton to become ADP, and the O4 of the fumaramide gains a proton to become neutral; these steps match the computed changes. 
**Why EC 6.3.2.47.** the reaction connects L-leucine and 3-(amino)-L-alanine (part of N(3)-fumaramoyl-(S)-2,3-diaminopropanoate) by a peptide bond, and ATP is the phosphoryl/adenylyl donor.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 11% of all heavy atoms and received 24% of Gemma4EC's attention (x2.2, enriched on the reaction centre); cofactor/cosubstrate atoms received 21%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 6.3.2.47 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; no mechanism reference).


---

## Reaction 89: not explained

`*CS(=O)(=O)[O-].Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])OP(=O)([O-])OP(=O)([O-])[O-])[C@@H](O)[C@H]1O.O>>O=P([O-])([O-])O`

record fails the check: {"heavy_atoms_lost": 0.86, "n_bond_changes": 4, "unnamed_main": 0, "ok": false}

---

## Reaction 90: Gemma4EC predicts EC 5.4.99 (true 5.4.99, correct)

`Cc1cn(C2CC(O)C(COP(=O)(O)OP(=O)(O)OC3OC(C)C(O)C(O)C3O)O2)c(=O)[nH]c1=O>>Cc1cn(C2CC(O)C(COP(=O)([O-])OP(=O)([O-])OC3OC(C(C)O)C(O)C3O)O2)c(=O)[nH]c1=O`

**What happens.** dTDP-D-fucose → dTDP-beta-D-fucofuranose.

**Bond changes (atom mapping).**
- broken single bond C22 (CH of dTDP-D-fucose) – C24 (CH3 of dTDP-D-fucose)
- new single bond C22 (CH of dTDP-D-fucose) – C26 (CH of dTDP-D-fucose)
- new single bond C23 (CH of dTDP-D-fucose) – C24 (CH3 of dTDP-D-fucose)
- broken single bond C23 (CH of dTDP-D-fucose) – C26 (CH of dTDP-D-fucose)
- O14 (OH of dTDP-D-fucose) loses 1 H and charge +0 → -1
- O18 (OH of dTDP-D-fucose) loses 1 H and charge +0 → -1

**Enzyme.** EC 5.4.99.59 dTDP-fucopyranose mutase (0/0 votes; candidates: 5.4.99.59, 1.1.1.266, 5.4.99.62, 5.4.99.53, 5.4.99.30).

**Mechanism.** The record describes changes at three separate sites, which a single enzymatic step rarely does, so it is inconsistent. Focusing on the part that *is* explained by the mechanism reference, the N5 of FAD acts as a nucleophile, attacking the C1 of dTDP-alpha-D-fucopyranose in an SN2 reaction. This breaks the alpha-D-fucose ring and forms a new furanose ring, with the FAD still bound; this is the mutase activity. The mechanism does not show what happens to the other two sites, so those changes are not explained.
**Why EC 5.4.99.59.** the enzyme causes a rearrangement of a sugar, and the record states that the product is dTDP-beta-D-fucofuranose, which matches the product of this mutase activity, so the EC number is appropriate.

*Mechanism source: M-CSA entry 368 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 17% of all heavy atoms and received 13% of Gemma4EC's attention (x0.8, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** The substrate changes at 3 separate sites, which a single enzymatic step rarely does: the record may merge several steps.

**Confidence: medium** (EC 5.4.99.59 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism by analogy to a related enzyme; 1 data caveat(s)).


---

## Reaction 91: not explained

`**[Fe+2]1(**)S[Fe+3](**)(**)S1.NC(=O)c1ccc[n+]([C@@H]2O[C@H](COP(=O)([O-])OP(=O)([O-])OC[C@H]3O[C@@H](n4cnc5c(N)ncnc54)[C@H](O)[C@@H]3O)[C@@H](O)[C@H]2O)c1.[H+].[Na+]>>**[Fe+3]1(**)S[Fe+3](**)(**)S1`

record fails the check: {"heavy_atoms_lost": 0.92, "n_bond_changes": 1, "unnamed_main": 0, "ok": false}

---

## Reaction 92: Gemma4EC predicts EC 2.7.8 (true 2.7.8, correct)

`CCCCCCCCCCCCCCC/C=C\CCCCCCCCCCC(=O)O[C@H](COC(=O)CCCCCCCCCCCCCCC)COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2ccc(N)nc2=O)C(O)[C@H]1O.CCCCCCCCCCCCCCCC(=O)OC[C@H](COP(=O)(O)OC[C@@H](O)CO)OC(=O)CCCCCCCCCCCCCCC>>CCCCCCCCCCCCCCC/C=C\CCCCCCCCCCC(=O)O[C@H](COC(=O)CCCCCCCCCCCCCCC)COP(=O)(O)OC[C@@H](O)COP(=O)(O)OC[C@@H](COC(=O)CCCCCCCCCCC)OC(=O)CCCCCCCCCCCCC`

**What happens.** a CDP-diacylglycerol + 1,2-dihexadecanoyl-sn-glycero-3-phospho-(1'-sn-… → a cardiolipin (+ CMP, not listed in the record). a CDP-diacylglycerol donates its phospho-head group; CMP is released.

**Bond changes (atom mapping).**
- new single bond P53 (P of a CDP-diacylglycerol) – O56 (OH of 1,2-dihexadecanoyl-sn-glycero-3-phospho…)
- broken single bond P53 (P of a CDP-diacylglycerol) – O (O of a CDP-diacylglycerol) (O side leaves)
- broken single bond C57 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) – C (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) (C side leaves)
- broken single bond C98 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) – C (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) (C side leaves)
- O56 (OH of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) loses 1 H
- C57 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) gains 1 H
- C98 (CH2 of 1,2-dihexadecanoyl-sn-glycero-3-phospho…) gains 1 H

**Enzyme.** EC 2.7.8.41 cardiolipin synthase (CMP-forming) (4/5 votes; candidates: 2.7.8.41, 2.7.8.8, 2.7.8.11, 2.7.8.5, 2.7.8.24).

**Mechanism.** The record describes an inconsistent change; a single step usually only changes one bond at a time. Focusing on the part the mechanism reference describes: a CMP-diacylglycerol donates its phospho-head group to the 1,2-dihexadecanoyl-sn-glycero-3-phospho… by forming a new single bond between its P53 and the O56 of the acceptor and breaking the P53-O bond of the CDP-diacylglycerol. Simultaneously, the acceptor's O56 loses a H, and the mechanism implies the two CH2 groups attached to carbons C57 and C98 of the acceptor gain one H each. This matches the computed changes, which show the formation of a new C-O bond, the breaking of two C-O bonds, and the gain of three H atoms, one to each of the three relevant carbons.
**Why EC 2.7.8.41.** the enzyme transfers a phosphate group from a CDP-diacylglycerol to a phosphatidylglycerol, forming a cardiolipin and releasing CMP (this is the defining characteristic of the EC 2.7.8.41 family). The other changes the record describes are not included in this reaction.

*Mechanism source: mechanism card 'cdp_alcohol_phosphotransferase'.*

**Attention.** the reaction-centre atoms are 4% of all heavy atoms and received 4% of Gemma4EC's attention (x1.0, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 28%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** The substrate changes at 3 separate sites, which a single enzymatic step rarely does: the record may merge several steps.

**Confidence: medium** (4/5 votes for EC 2.7.8.41; no database entry with these exact participants; mechanism from a class reference; 1 data caveat(s)).


---

## Reaction 93: Gemma4EC predicts EC 1.7.7 (true 1.7.7, correct)

`**[Fe+2]1(**)S[Fe+3](**)(**)S1.O=N[O-].[H+]>>**[Fe+3]1(**)S[Fe+3](**)(**)S1`

**What happens.** unknown (not in MetaNetX) + nitrite → unknown (not in MetaNetX).

**Bond changes (atom mapping).**
- Fe3 (Fe+ of unknown (not in MetaNetX)) charge +2 → +3

**Enzyme.** EC 1.7.7.1 ferredoxin-nitrite reductase (3/5 votes; candidates: 1.7.7.1, 1.7.7.2).

**Mechanism.** The unknown substrate (not in MetaNetX) is reduced, gaining an electron to become Fe3+ (from Fe2+). Then nitrite gains that electron and a proton, becoming HNO2 (nitrite). This matches the computed changes: the unknown gains one electron and one proton, becoming Fe3+, while nitrite gains one electron and one proton, becoming HNO2.
**Why EC 1.7.7.1.** the enzyme catalyzes the reduction of nitrite using reduced ferredoxin as the electron donor (EC 1.7.7), and the unknown + nitrite = unknown (Fe3+) + HNO2 is just this reaction read in reverse.

*Mechanism source: M-CSA entry 323.*

**Attention.** the reaction-centre atoms are 18% of all heavy atoms and received 16% of Gemma4EC's attention (x0.9, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (3/5 votes for EC 1.7.7.1; no database entry with these exact participants; mechanism from the M-CSA entry for this enzyme).


---

## Reaction 94: not explained

`*CC1OC(n2cnc3c(N)ncnc32)C(OC(=O)C([NH3+])CC(=O)[O-])C1O.Nc1ncnc2c1ncn2[C@@H]1O[C@H](COP(=O)([O-])[O-])[C@@H](O)[C@H]1O.O=P([O-])([O-])OP(=O)([O-])O>>[NH3+][C@@H](CC(=O)[O-])C(=O)[O-]`

record fails the check: {"heavy_atoms_lost": 0.84, "n_bond_changes": 2, "unnamed_main": 1, "ok": false}

---

## Reaction 95: Gemma4EC predicts EC 5.3.2 (true 5.3.3, WRONG)

`CCCCCCC=C=CC(=O)N(CCS)C(C)=O>>CCCCCCC#CCC(=O)N(CCS)C(C)=O`

**What happens.** (2Z,3Z)-deca-2,3-dienoyl-N-acetylcysteamine → 3-decynoyl-N-acetylcysteamine.

**Bond changes (atom mapping).**
- changed bond C7 (CH of (2Z,3Z)-deca-2,3-dienoyl-N-acetylcystea…) – C8 (C of (2Z,3Z)-deca-2,3-dienoyl-N-acetylcystea…): double → triple
- changed bond C8 (C of (2Z,3Z)-deca-2,3-dienoyl-N-acetylcystea…) – C9 (CH of (2Z,3Z)-deca-2,3-dienoyl-N-acetylcystea…): double → single
- C7 (CH of (2Z,3Z)-deca-2,3-dienoyl-N-acetylcystea…) loses 1 H
- C9 (CH of (2Z,3Z)-deca-2,3-dienoyl-N-acetylcystea…) gains 1 H

**Enzyme.** EC 5.3.3.8 DELTA3-DELTA2-enoyl-CoA isomerase (0/0 votes; candidates: 5.3.3.8, 5.3.2.1, 5.3.2.6, 5.3.2.8, 5.3.2.7).

**Mechanism.** The mechanism is that of an E1cb reaction. A Glu residue deprotonates C7 of the substrate, forming a carbanion which is stabilized by an oxyanion hole formed by a Leu and a Gly. The negatively charged thioester oxygen then picks up a proton from C9, simultaneously forming a double bond between C7 and C8 (with loss of the H from C7 and gain of H by C9, as described in the bond changes). The resulting intermediate then tautomerizes to the product, with protonation of C4 by another Glu residue. 
**Why EC 5.3.3.8.** the EC number refers to an isomerase that acts on enoyl-CoAs, and the bond changes show that a double bond is converted to a triple bond, which is characteristic of a desaturase reaction, a type of isomerization.

*Mechanism source: M-CSA entry 341.*

**Attention.** the reaction-centre atoms are 17% of all heavy atoms and received 8% of Gemma4EC's attention (x0.5, depleted on the reaction centre); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: high** (EC 5.3.3.8 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism from the M-CSA entry for this enzyme).


---

## Reaction 96: Gemma4EC predicts EC 2.3.1 (true 2.3.1, correct)

`CC/C=C\C/C=C\C/C=C\C/C=C\C/C=C\CCCCCC(=O)O[C@@H](CO)COC(=O)CCCCCCCCCCCCCCCCC.CCCCC/C=C\C/C=C\CCCCCCCCCCCC(=O)SCCNC(=O)CCNC(=O)[C@H](O)C(C)(C)COP(=O)(O)OP(=O)(O)OC[C@H]1O[C@@H](n2cnc3c(N)ncnc32)[C@H](O)[C@@H]1OP(=O)(O)O>>CC/C=C\C/C=C\C/C=C\C/C=C\C/C=C\CCCCCC(=O)O[C@H](COC(=O)CCCCCCCCCCC/C=C\C/C=C\CCCCC)COC(=O)CCCCCCCCCCCCCCCCC`

**What happens.** 1-octadecanoyl-2-(7Z,10Z,13Z,16Z,19Z-docosapent… + (13Z,16Z)-docosadienoyl-CoA → 1-(13Z,16Z-docosadienoyl)-2-(7Z,10Z,13Z,16Z,19Z… (+ CoA, not listed in the record). (13Z,16Z)-docosadienoyl-CoA donates its acyl group; CoA is released.

**Bond changes (atom mapping).**
- new single bond O27 (OH of 1-octadecanoyl-2-(7Z,10Z,13Z,16Z,19Z-do…) – C28 (C of (13Z,16Z)-docosadienoyl-CoA)
- broken single bond C28 (C of (13Z,16Z)-docosadienoyl-CoA) – S (S of (13Z,16Z)-docosadienoyl-CoA) (S side leaves)
- O27 (OH of 1-octadecanoyl-2-(7Z,10Z,13Z,16Z,19Z-do…) loses 1 H

**Enzyme.** EC 2.3.1.20 diacylglycerol O-acyltransferase (0/0 votes; candidates: 2.3.1.20, 2.3.1.15, 2.3.1.22, 2.3.1.51, 2.3.1.16).

**Mechanism.** The mechanism is assumed by analogy to the acyl-CoA:alcohol O-acyltransferase. The hydroxyl group O27 of the 1-octadecanoyl-2-(7Z,10Z,13Z,16Z,19Z-docosapentyl]diacylglycerol attacks the thioester carbonyl carbon of (13Z,16Z)-docosadienoyl-CoA.  A conserved active-site His acts as general base, deprotonating the hydroxyl.  This leads to a tetrahedral oxyanion intermediate which collapses, expelling the CoA thiolate (protonated to CoA-SH) and forming the ester bond between the two fatty acids. The CoA thiolate is the leaving group and, as per the reference, is usually omitted from the record.
**Why EC 2.3.1.20.** the enzyme catalyzes the transfer of an acyl group from CoA to a 1,2-diacylglycerol (acyl-CoA + R-OH -> ester + CoA), matching the overall transformation described in the reaction.

*Mechanism source: mechanism card 'acyl_coa_o_acyltransferase'.*

**Attention.** the reaction-centre atoms are 2% of all heavy atoms and received 1% of Gemma4EC's attention (x0.6, depleted on the reaction centre); cofactor/cosubstrate atoms received 26%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** none detected.

**Confidence: medium** (EC 2.3.1.20 leads the similarity ranking clearly; no database entry with these exact participants; mechanism from a class reference).


---

## Reaction 97: Gemma4EC predicts EC 5.5.1 (true 5.5.1, correct)

`C/C(C=O)=C\CC[C@H](C)/C=C/O>>CC1=COC(O)[C@H]2[C@@H](C)CC[C@@H]12`

**What happens.** (S)-8-oxocitronellyl enol → cis-cis-nepetalactol.

**Bond changes (atom mapping).**
- changed bond C2 (C of (S)-8-oxocitronellyl enol) – C3 (CH of (S)-8-oxocitronellyl enol): single → double
- changed bond C2 (C of (S)-8-oxocitronellyl enol) – C12 (CH of (S)-8-oxocitronellyl enol): double → single
- changed bond C3 (CH of (S)-8-oxocitronellyl enol) – O4 (O of (S)-8-oxocitronellyl enol): double → single
- new single bond O4 (O of (S)-8-oxocitronellyl enol) – C5 (CH of (S)-8-oxocitronellyl enol)
- changed bond C5 (CH of (S)-8-oxocitronellyl enol) – C7 (CH of (S)-8-oxocitronellyl enol): double → single
- new single bond C7 (CH of (S)-8-oxocitronellyl enol) – C12 (CH of (S)-8-oxocitronellyl enol)

**Enzyme.** EC 5.5.1.35 (+)-cis,cis-nepetalactol synthase (5/5 votes; candidates: 5.5.1.34, 5.5.1.35, 5.5.1.10, 5.5.1.6, 5.5.1.20).

**Mechanism.** The record describes two locations of change on the substrate, which is unlikely for a single enzymatic step. We can only explain the part the reference mechanism accounts for: the C2–C3 double bond is broken and a double bond is formed between C2 and C12, while simultaneously, the C3–O4 double bond is broken and a single bond formed between O4 and C5. The reference does not describe the formation of a new C7-C12 single bond, nor the breaking of C5-C7.
**Why EC 5.5.1.35.** this is the only reaction listed which produces (+)-cis,cis-nepetalactol from a citronellyl enol.

*No curated mechanism available.*

**Attention.** the reaction-centre atoms are 50% of all heavy atoms and received 36% of Gemma4EC's attention (x0.7, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** The substrate changes at 2 separate sites, which a single enzymatic step rarely does: the record may merge several steps.

**Confidence: medium** (5/5 votes for EC 5.5.1.35; the exact reaction is listed for this EC in MetaNetX; no mechanism reference; 1 data caveat(s)).


---

## Reaction 98: not explained

`O=C1C[C@@](O)(CO)[C@@H](O)[C@H](O)[C@@H]1O>>O=C1C[C@@](O)(CO)[C@@H](O)[C@H](O)[C@H]1O`

record fails the check: {"heavy_atoms_lost": 0.0, "n_bond_changes": 0, "unnamed_main": 0, "ok": false}

---

## Reaction 100: Gemma4EC predicts EC 3.1.4 (true 3.1.4, correct)

`CCCCCCCCCCCCC/C=C\[C@@H](O)[C@@H](N)COP(=O)(O)OCC[N+](C)(C)C.O>>CCCCCCCCCCCCC/C=C\[C@@H](O)[C@@H](N)COP(=O)(O)O`

**What happens.** sphingosylphosphorylcholine → sphing-4-enine 1-phosphate + choline. Participants not in the record (choline) were added from MetaNetX reaction MNXR127310.

**Bond changes (atom mapping).**
- new single bond P22 (P of sphingosylphosphorylcholine) – O24 (OH2 of H2O)
- broken single bond P22 (P of sphingosylphosphorylcholine) – O32 (O of sphingosylphosphorylcholine)
- O24 (OH2 of H2O) loses 1 H
- O32 (O of sphingosylphosphorylcholine) gains 1 H

**Enzyme.** EC 3.1.4.39 alkylglycerophosphoethanolamine phosphodiesterase (0/0 votes; candidates: 3.1.4.39, 3.1.4.41, 3.1.4.12, 3.1.4.38, 3.1.4.2).

**Mechanism.**** The provided information regarding the bond changes and the mechanism reference suggests a hydrolysis reaction where the phosphate group of sphingosylphosphorylcholine is cleaved, forming sphing-4-enine 1-phosphate and choline. The mechanism likely involves a Histidine residue acting as a catalytic base, deprotonating either the hydroxyl group of sphingosylphosphorylcholine or the leaving phosphate group, facilitating nucleophilic attack by water on the phosphate.

****Why EC 3.1.4.39.**** The enzyme EC 3.1.4.39, alkylglycerophosphoethanolamine phosphodiesterase, belongs to the class of phosphodiesterases that cleave P-O bonds. While the provided mechanism does not explicitly involve transferring a P-O group to a different molecule, the general class definition applies.

*Mechanism source: M-CSA entry 300 (analogous enzyme, different substrate).*

**Attention.** the reaction-centre atoms are 9% of all heavy atoms and received 8% of Gemma4EC's attention (x0.8, roughly proportional to the number of centre atoms); cofactor/cosubstrate atoms received 0%. Attention shows what the model looked at, not what caused the prediction.

**Caveats.** The name of Reactant 1 (sphingosylphosphorylcholine) comes from a MetaNetX entry that only shares its connectivity; check it against the formula C23H50N2O5P+. The name of Product 1 (sphing-4-enine 1-phosphate) comes from a MetaNetX entry that only shares its connectivity; check it against the formula C18H38NO5P.

**Confidence: medium** (EC 3.1.4.39 leads the similarity ranking clearly; the exact reaction is listed for this EC in MetaNetX; mechanism by analogy to a related enzyme; 2 data caveat(s)).


---
