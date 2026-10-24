#!/usr/bin/env python3
"""M6 extension stress-test: 120 extra Gen4-6 family lines, after 31-family pilot.
Experimental child branch only; accept into game only after measured ROM, RAM,
encounter validation and mGBA gameplay. Preserves all original wild species by
substituting only duplicate encounter slots.
"""
from pathlib import Path
import argparse
import json
import re
import sys

COUNT=120
GENERATIONS=(4,5,6)

def expand(root, apply):
    cfg=root/"include/config/species_enabled.h"
    json_path=root/"src/data/wild_encounters.json"
    val_path=root/"test/overworld/ValidateGen13.py"
    for p in (cfg,json_path,val_path):
        if not p.is_file():raise ValueError(f"World file missing: {p}")
    text=cfg.read_text()
    val=val_path.read_text()
    blob=json.loads(json_path.read_text())
    groups=blob["wild_encounter_groups"]
    active=groups[0]["encounters"]
    choices=[]
    seen=set()
    for gen in GENERATIONS:
        path=root/f"src/data/pokemon/species_info/gen_{gen}_families.h"
        for fam in re.findall(r"(?m)^#if (P_FAMILY_[A-Z0-9_]+)\b",path.read_text()):
            if fam in seen:continue
            seen.add(fam)
            if re.search(r"(?m)^#define\s+"+fam+r"\s+FALSE\b",text):
                choices.append(fam)
            if len(choices)==COUNT:break
        if len(choices)==COUNT:break
    if len(choices)!=COUNT:raise ValueError(f"expected {COUNT} disabled Gen4-6 families, found {len(choices)}")
    for family in choices:
        pattern=r"(?m)^(#define\s+"+family+r"\s+)FALSE(\s*(?://[^\n]*)?)$"
        text,n=re.subn(pattern,r"\g<1>TRUE\g<2>",text)
        if n!=1:raise ValueError(f"family flag mismatch {family}: {n}")
    regions={"KANTO":[],"JOHTO":[],"HOENN":[]}
    for e in active:
        m=re.fullmatch(r"MAP_ROUTE(\d+)",e.get("map",""))
        if not m or len(e.get("land_mons",{}).get("mons",[]))!=12:
            continue
        n=int(m[1])
        reg=("KANTO" if n<=28 else
             "JOHTO" if 29<=n<=46 else
             "HOENN" if 101<=n<=130 else None)
        if reg:regions[reg].append(e)
    map_groups={reg:{} for reg in regions}
    for reg, entries in regions.items():
        for e in entries:
            map_groups[reg].setdefault(e["map"],[]).append(e)
        if len(map_groups[reg])<10:raise ValueError(f"insufficient {reg} route maps")
    def natural(name):
        return int(re.fullmatch(r"MAP_ROUTE(\d+)",name)[1])
    route_names={reg:sorted(d,key=natural) for reg,d in map_groups.items()}
    pointer={reg:0 for reg in regions}
    reports=[]
    for idx,fam in enumerate(choices):
        reg=("KANTO","JOHTO","HOENN")[idx%3]
        maps=route_names[reg]
        selected=None
        for attempt in range(len(maps)):
            name=maps[(pointer[reg]+attempt)%len(maps)]
            variants=map_groups[reg][name]
            # Each edition/variant must have a repeated original Pokémon.
            if all(any(sum(x["species"]==m["species"] for x in e["land_mons"]["mons"])>1
                       for m in e["land_mons"]["mons"]) for e in variants):
                selected=name
                pointer[reg]=(pointer[reg]+attempt+1)%len(maps)
                break
        if selected is None:raise ValueError(f"no duplicate slot remains for {fam} in {reg}")
        for e in map_groups[reg][selected]:
            mons=e["land_mons"]["mons"]
            options=[i for i,mon in enumerate(mons)
                     if sum(x["species"]==mon["species"] for x in mons)>1]
            if not options:raise ValueError(f"raced away last duplicate in {selected}")
            slot=options[-1]
            original=mons[slot]["species"]
            mons[slot]["species"]="SPECIES_"+fam[len("P_FAMILY_"):]
            if sum(x["species"]==original for x in mons)<1:
                raise ValueError(f"removed sole {original} species on {selected}")
            reports.append({"region":reg,"map":selected,"table":e.get("base_label"),
                            "slot":slot,"original":original,"new":mons[slot]["species"],
                            "level":[mons[slot]["min_level"],mons[slot]["max_level"]]})
    marker="}\n\nMIN_DISABLED_FAMILIES"
    if val.count(marker)!=1:raise ValueError("existing 31-family validator whitelist drift")
    extra="".join(f'    "{x}",\n' for x in choices)
    val=val.replace(marker,extra+marker,1)
    if val.count("MIN_DISABLED_FAMILIES = 300")!=1:
        raise ValueError("validator precondition missing")
    # 339 originally disabled, 31+120 now enabled -> ~188 disabled.
    val=val.replace("MIN_DISABLED_FAMILIES = 300","MIN_DISABLED_FAMILIES = 170",1)
    report={"additional_families":len(choices),"total_gen4plus_families":31+len(choices),
            "species_families":choices,"modified_table_variants":len(reports),
            "region_counts":{r:sum(x["region"]==r for x in reports) for r in regions},
            "changes":reports,"runtime_and_save_playthrough_verified":False}
    if apply:
        cfg.write_text(text)
        json_path.write_text(json.dumps(blob,indent=2,ensure_ascii=False)+"\n")
        val_path.write_text(val)
        (root.parent/"m8-extended-families-evidence.json").write_text(json.dumps(report,indent=2))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("world",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args()
    try:r=expand(a.world,a.apply)
    except (ValueError,AssertionError,OSError,KeyError,TypeError) as e:sys.exit(f"FAIL-CLOSED: {e}")
    print(json.dumps({k:v for k,v in r.items() if k!="changes"},indent=2))
    print("APPLIED" if a.apply else "DRY-RUN")
