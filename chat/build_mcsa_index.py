#!/usr/bin/env python3
"""
Compact M-CSA (Mechanism and Catalytic Site Atlas, EBI) index for mechanism retrieval in the chat pipeline.

Input: the paged API dump in chat/data/mcsa/entries_p*.json, fetched with
    curl "https://www.ebi.ac.uk/thornton-srv/m-csa/api/entries/?format=json&page_size=100&page=N"
Output: chat/data/mcsa_index.json = [{mcsa_id, enzyme, ecs, reaction, mechanism, components, steps, residues}]
"""
import glob
import json
from pathlib import Path

src = Path("chat/data/mcsa")
out = []
for f in sorted(glob.glob(str(src / "entries_p*.json"))):
    for e in json.load(open(f))["results"]:
        r = e["reaction"]
        mechs = sorted(r.get("mechanisms") or [], key=lambda m: (not m.get("is_detailed"), -(m.get("rating") or 0)))
        m = mechs[0] if mechs else {}
        names = lambda t: [c["name"] for c in r.get("compounds", []) if c["type"] == t]
        ecs = sorted({x for x in (e.get("all_ecs") or []) + [r.get("ec")] if x})
        out.append({
            "mcsa_id": e["mcsa_id"], "enzyme": e["enzyme_name"], "ecs": ecs,
            "reaction": ' + '.join(names("reactant")) + ' = ' + ' + '.join(names("product")),
            "mechanism": (m.get("mechanism_text") or "").strip(),
            "components": m.get("components_summary") or "",
            "steps": [s["description"].strip() for s in m.get("steps", []) if s.get("description")],
            "residues": sorted({f"{c['resid']}{c.get('auth_resid') or ''}" if False else
                                f"{rc.get('code', '')}{rc.get('resid', '')}"
                                for res in e.get("residues", []) for rc in res.get("residue_chains", [])[:1]
                                if rc.get("code")})[:12],
        })
Path("chat/data/mcsa_index.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(f"{len(out)} M-CSA entries, {sum(bool(o['mechanism']) for o in out)} with mechanism text "
      f"→ chat/data/mcsa_index.json")
