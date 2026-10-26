#!/usr/bin/env python3
"""Conservative trade-lead scan for residual grass-only Grand World GBA gaps.

A source trade offer is not proof that the NPC/event can be reached, that trade
is usable, or that the offered mon joins the party. Does not edit any file.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

TARGETS=(
    "SPECIES_CLAMPERL","SPECIES_FINNEON","SPECIES_HORSEA","SPECIES_LUVDISC",
    "SPECIES_MANTINE","SPECIES_NOSEPASS","SPECIES_OCTILLERY","SPECIES_RELICANTH",
    "SPECIES_REMORAID","SPECIES_SEADRA","SPECIES_SHELLDER","SPECIES_SHELLOS",
)
TRADE_RECORD=re.compile(r"(?m)^    \[(INGAME_TRADE_[A-Z0-9_]+)\]\s*=\s*\n    \{")
FIELD=re.compile(r"(?m)^\s*\.(species|requestedSpecies)\s*=\s*(SPECIES_[A-Z0-9_]+)\s*,?")


def land_species(file):
    j=json.loads(Path(file).read_text())
    g=[v for v in j.get("wild_encounter_groups",[])
       if v.get("label")=="gWildMonHeaders" and v.get("for_maps") is True]
    if len(g)!=1 or len(g[0].get("encounters",[]))<300:
        raise ValueError("incomplete pinned World map species table")
    out=set()
    for m in g[0]["encounters"]:
        v=m.get("land_mons")
        if not v or v.get("encounter_rate",0)<=0:continue
        for row in v.get("mons",[]):
            sp=row.get("species")
            if not isinstance(sp,str) or not sp.startswith("SPECIES_"):
                raise ValueError("invalid original land species")
            if sp!="SPECIES_NONE":out.add(sp)
    return out


def trade_entries(text):
    matches=list(TRADE_RECORD.finditer(text))
    result=[]
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(text)
        chunk=text[m.end():end]
        fields=dict(FIELD.findall(chunk))
        if "species" in fields and "requestedSpecies" in fields:
            result.append({"id":m.group(1),"offers":fields["species"],
                           "requires":fields["requestedSpecies"]})
    return result


def inspect(table,source,min_trades=8):
    available=land_species(table)
    raw=Path(source).read_bytes()
    entries=trade_entries(raw.decode("utf-8",errors="replace"))
    if len(entries)<min_trades:
        raise ValueError(f"incomplete World in-game trades: {len(entries)}")
    leads=[]
    for t in entries:
        if t["offers"] not in TARGETS:continue
        leads.append({**t,"requested_species_in_original_land_table":t["requires"] in available,
                      "trade_event_in_game_verified":False,
                      "request_species_actually_catchable_verified":False,
                      "offered_pokemon_received_in_game_verified":False})
    return {"schema":1,
            "reference_event_audit_run":"https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40316833046",
            "target_12_species":list(TARGETS),
            "trade_entries_parsed":len(entries),
            "trade_lead_species":len(set(x["offers"] for x in leads)),
            "trades_with_requested_species_in_land_source":sum(v["requested_species_in_original_land_table"] for v in leads),
            "leads":leads,
            "trade_source_sha256":hashlib.sha256(raw).hexdigest(),
            "unscanned_indirect_trade_forms":True,
            "in_game_npc_story_accessibility_verified":False,
            "trade_gameplay_verified":False,
            "source_scans_can_prove_obtainability":False,
            "rom_modified":False,"saves_modified":False,"release_approved":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wild-table",type=Path,required=True)
    p.add_argument("--trade-header",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        report=inspect(a.wild_table,a.trade_header)
        a.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(f"{report['trade_entries_parsed']} pinned game trades; "
              f"{report['trade_lead_species']} residual Pokémon offered; "
              f"{report['trades_with_requested_species_in_land_source']} request species "
              "have a land-table entry. No NPC story accessibility certified.")
    except (OSError,ValueError,TypeError,KeyError) as err:
        sys.exit("FAIL CLOSED trade species audit: "+str(err))


if __name__=="__main__":
    main()
