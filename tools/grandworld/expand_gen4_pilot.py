#!/usr/bin/env python3
"""Grand World M6: deterministic 31-family Gen4 pilot for a pinned PKMN-World.
Preserve wild encounter encounter_rate, min/max level and canonical map labels.
Require at least one original instance of every displaced species to remain.
Adapt the legacy Gen1-3 validator to an EXACT, reviewed Gen4 exception set.
This is a reproducible trial, not a claim of maximum Pokedex capacity.
"""
from pathlib import Path
import argparse
import json
import re
import sys

REGIONS = {
    "KANTO": [
        ("MAP_ROUTE3", "TURTWIG"), ("MAP_ROUTE4", "CHIMCHAR"),
        ("MAP_ROUTE5", "PIPLUP"), ("MAP_ROUTE6", "STARLY"),
        ("MAP_ROUTE7", "BIDOOF"), ("MAP_ROUTE8", "KRICKETOT"),
        ("MAP_ROUTE9", "SHINX"), ("MAP_ROUTE10", "CRANIDOS"),
        ("MAP_ROUTE11", "SHIELDON"), ("MAP_ROUTE12", "BURMY"),
        ("MAP_ROUTE23", "COMBEE"),
    ],
    "JOHTO": [
        ("MAP_ROUTE29", "PACHIRISU"), ("MAP_ROUTE30", "BUIZEL"),
        ("MAP_ROUTE31", "CHERUBI"), ("MAP_ROUTE32", "SHELLOS"),
        ("MAP_ROUTE33", "DRIFLOON"), ("MAP_ROUTE34", "BUNEARY"),
        ("MAP_ROUTE35", "GLAMEOW"), ("MAP_ROUTE36", "STUNKY"),
        ("MAP_ROUTE37", "BRONZOR"), ("MAP_ROUTE38", "CHATOT"),
    ],
    "HOENN": [
        ("MAP_ROUTE111", "SPIRITOMB"), ("MAP_ROUTE112", "GIBLE"),
        ("MAP_ROUTE113", "RIOLU"), ("MAP_ROUTE114", "HIPPOPOTAS"),
        ("MAP_ROUTE115", "SKORUPI"), ("MAP_ROUTE116", "CROAGUNK"),
        ("MAP_ROUTE117", "CARNIVINE"), ("MAP_ROUTE118", "FINNEON"),
        ("MAP_ROUTE119", "SNOVER"), ("MAP_ROUTE120", "ROTOM"),
    ],
}
PILOT = tuple(f for region in REGIONS.values() for _, f in region)

def patch(root: Path, write: bool):
    flags_path=root/"include/config/species_enabled.h"
    json_path=root/"src/data/wild_encounters.json"
    validator_path=root/"test/overworld/ValidateGen13.py"
    for path in (flags_path,json_path,validator_path):
        if not path.is_file():
            raise ValueError(f"missing World source: {path}")
    flags=flags_path.read_text()
    wild=json.loads(json_path.read_text())
    validator=validator_path.read_text()
    assert len(PILOT)==len(set(PILOT))==31
    for name in PILOT:
        patt=r"(?m)^(#define P_FAMILY_"+name+r"\s+)FALSE(\s*(?://[^\n]*)?)$"
        flags,n=re.subn(patt,r"\g<1>TRUE\g<2>",flags)
        if n!=1:raise ValueError(f"family gate mismatch: {name} matches {n}")
    entries=wild.get("wild_encounter_groups",[{}])[0].get("encounters",[])
    touched=[]
    for region, routes in REGIONS.items():
        for map_name, family in routes:
            # Aquatic species belong in water rather than walking on land.
            habitat="water_mons" if family in ("BUIZEL","SHELLOS","FINNEON") else "land_mons"
            expected=5 if habitat=="water_mons" else 12
            matches=[e for e in entries if e.get("map")==map_name and len(e.get(habitat,{}).get("mons",[]))==expected]
            if not matches:raise ValueError(f"no {expected}-slot {habitat} encounter entry: {map_name}")
            for entry in matches:
                mons=entry[habitat]["mons"]
                # Replace only a repeat: guarantee the displaced species survives on this route.
                repeated=[i for i,mon in enumerate(mons) if sum(other["species"]==mon["species"] for other in mons)>1]
                if not repeated:raise ValueError(f"no safe duplicate slot: {entry.get('base_label')}")
                slot=repeated[-1]
                old=mons[slot]["species"]
                mons[slot]["species"]="SPECIES_"+family
                if not any(i!=slot and x["species"]==old for i,x in enumerate(mons)):
                    raise ValueError("last original species mistakenly removed")
                touched.append({"region":region,"map":map_name,"table":entry.get("base_label"),"habitat":habitat,"slot":slot,"previous":old,"new":mons[slot]["species"],"levels":[mons[slot]["min_level"],mons[slot]["max_level"]]})
    # Existing validator enforces ALL gen4 families disabled. Extend only exact,
    # explicitly enumerable pilot families; all others are still rejected.
    signature="MIN_DISABLED_FAMILIES = 300"
    if validator.count(signature)!=1:raise ValueError("validator version changed")
    whitelist="GRANDWORLD_EXTRA_FAMILIES = {\n"+ "".join(f'    "P_FAMILY_{f}",\n' for f in PILOT)+"}\n"
    validator=validator.replace(signature,whitelist+"\n"+signature,1)
    old="if fam not in disabled_families:\n            enabled_late.append((gen, fam))"
    new="if fam not in disabled_families and fam not in GRANDWORLD_EXTRA_FAMILIES:\n            enabled_late.append((gen, fam))"
    if validator.count(old)!=1:raise ValueError("validator late-family invariant changed")
    validator=validator.replace(old,new,1)
    needle='print("OK — no disabled-species references in obtainable content; all Gen 4+ families stripped.")'
    if validator.count(needle)!=1:raise ValueError("validator final status changed")
    validator=validator.replace(needle,'print("OK — all obtainable species enabled; only explicitly audited Grand World pilot families may be late-generation.")')
    # The original validator treats FALSE as disabled. Check exactly PILOT is new.
    for name in PILOT:
        if re.search(r"(?m)^#define P_FAMILY_"+name+r"\s+FALSE\b",flags):
            raise ValueError("pilot species remains disabled")
    summary={"family_count":len(PILOT),"table_variants_modified":len(touched),"region_counts":{reg:sum(e["region"]==reg for e in touched) for reg in REGIONS},"changes":touched,"source":"PKMN-World pinned checkout","continuous_gameplay_verified":False}
    if write:
        flags_path.write_text(flags)
        json_path.write_text(json.dumps(wild,ensure_ascii=False,indent=2)+"\n")
        validator_path.write_text(validator)
        (root.parent/"m8-gen4-encounters-evidence.json").write_text(json.dumps(summary,indent=2))
    return summary

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("world",type=Path)
    parser.add_argument("--apply",action="store_true",help="Write files in isolated checkout")
    args=parser.parse_args()
    try:
        result=patch(args.world,args.apply)
    except (ValueError,AssertionError,KeyError,TypeError,OSError) as ex:
        sys.exit(f"FAIL-CLOSED: {ex}")
    print(json.dumps({k:v for k,v in result.items() if k!="changes"},indent=2))
    print("WROTE" if args.apply else "DRY RUN - no source changes")
