#!/usr/bin/env python3
"""Evidence-only evolution lineage audit for grass-only Grand World GBA.

A source-declared evolution path is NOT a guarantee of evolution feasibility,
item/trade availability, parental species encounter, or final Pokédex access.
Never edits the game. Scans real M8 wild tables and pinned World species_info.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import re
import sys

SPECIES_RECORD = re.compile(r"(?m)^\s*\[(SPECIES_[A-Z0-9_]+)\]\s*=")
EVO_EDGE = re.compile(r"\{\s*(EVO_[A-Z0-9_]+)\s*,\s*[^,{}]*,\s*(SPECIES_[A-Z0-9_]+)")
NEVER = {"SPECIES_NONE"}
METADATA_FILES = ["species_info.h"] + [f"species_info/gen_{i}_families.h" for i in range(1, 10)]


def edges_from_text(text):
    """Read only explicit source-declared evolutionary edges, never inferred chains."""
    positions = list(SPECIES_RECORD.finditer(text))
    edges = []
    for i, match in enumerate(positions):
        origin = match.group(1)
        end = positions[i + 1].start() if i + 1 < len(positions) else len(text)
        record = text[match.end():end]
        # Only .evolutions field; other species references in moves/graphics
        # and forms are NOT evidence of an evolutionary relationship.
        ev_start = re.search(r"\.evolutions\s*=\s*EVOLUTION\s*\(", record)
        if ev_start is None:
            continue
        rest = record[ev_start.end():]
        depth, stop = 1, None
        for n, char in enumerate(rest):
            if char == "(": depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    stop = n
                    break
        if stop is None:
            raise ValueError(f"unbalanced evolution expression for {origin}")
        for method, dest in EVO_EDGE.findall(rest[:stop]):
            if dest not in NEVER and dest != origin:
                edges.append((origin, dest, method))
    return edges


def load_edges(info_root):
    root = Path(info_root)
    records = {}
    missing = []
    for relative in METADATA_FILES:
        path = root / relative
        if not path.is_file():
            missing.append(str(path))
            continue
        source = path.read_bytes()
        records[relative] = hashlib.sha256(source).hexdigest()
    if missing:
        raise ValueError("missing pinned World evolution source files: " + "; ".join(missing))
    graph = {}
    for relative in METADATA_FILES:
        for a, b, kind in edges_from_text((root/relative).read_text(encoding="utf-8", errors="replace")):
            graph.setdefault(a, []).append((b, kind))
    return graph, records


def land_species(table_path):
    obj=json.loads(Path(table_path).read_text(encoding="utf-8"))
    groups=[g for g in obj.get("wild_encounter_groups", [])
            if g.get("label") == "gWildMonHeaders" and g.get("for_maps") is True]
    if len(groups)!=1 or len(groups[0].get("encounters", [])) < 300:
        raise ValueError("not the full World mapped encounter table")
    found=set()
    disabled=set()
    for entry in groups[0]["encounters"]:
        for method in ("land_mons","water_mons","fishing_mons","rock_smash_mons"):
            section=entry.get(method)
            if not section or not isinstance(section,dict) or section.get("encounter_rate",0)<=0:
                continue
            mons=section.get("mons")
            if not isinstance(mons,list):
                raise ValueError(f"invalid {method} slots on {entry.get('map')}")
            for mon in mons:
                name=mon.get("species")
                if not isinstance(name,str) or not name.startswith("SPECIES_"):
                    raise ValueError(f"invalid species {name!r} on {entry.get('map')}")
                if name in NEVER:continue
                (found if method=="land_mons" else disabled).add(name)
    return found,disabled


def lineage_path(graph, roots, target):
    if target in roots:return []
    queue=deque(roots)
    parents={x:None for x in roots}
    while queue:
        n=queue.popleft()
        for dest,method in graph.get(n,()):
            if dest in parents:continue
            parents[dest]=(n,method)
            if dest==target:
                path=[]
                k=dest
                while parents[k] is not None:
                    parent,edge=parents[k]
                    path.insert(0,{"from":parent,"to":k,"method":edge})
                    k=parent
                return path
            queue.append(dest)
    return None


def inspect(original, experimental, species_root):
    baseline, disabled=land_species(original)
    candidate,_=land_species(experimental)
    if not baseline.issubset(candidate):
        raise ValueError("experimental land data lost an existing species")
    at_risk=sorted(disabled-baseline)
    proposed=candidate-baseline
    graph,source_hashes=load_edges(species_root)
    items=[]
    status_counts={}
    for name in at_risk:
        original_path=lineage_path(graph,baseline,name)
        candidate_path=lineage_path(graph,candidate,name)
        if original_path is not None:
            status="source_evolution_from_original_land" # not necessarily feasible or fully catchable
        elif name in proposed:
            status="experimental_direct_land_slot"
        elif candidate_path is not None:
            status="source_evolution_dependent_on_experiment"
        else:
            status="no_identified_land_or_evolution_path"
        status_counts[status]=status_counts.get(status,0)+1
        items.append({"species":name,"status":status,
                      "original_land_evolution_chain":original_path,
                      "experimental_land_evolution_chain":candidate_path,
                      "in_original_land_tables":name in baseline,
                      "in_experimental_land_tables":name in candidate,
                      "item_trade_stones_and_conditions_checked_in_game":False,
                      "spawn_or_evolution_in_emulator_verified":False})
    return {"schema_version":1,"target":"M8 Grand World PT-BR grass-only source audit",
            "original_land_species":len(baseline),
            "experiment_land_species":len(candidate),
            "original_species_at_risk":len(at_risk),
            "direct_new_land_species":len(proposed),
            "status_counts":status_counts,
            "species":items,
            "evolution_source_sha256":source_hashes,
            "evolutions_usable_in_playthrough_confirmed":False,
            "original_pokemon_availability_complete":False,
            "rom_modified":False,"saves_modified":False,"release_approved":False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--experimental",type=Path,required=True)
    p.add_argument("--species-root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        report=inspect(args.original,args.experimental,args.species_root)
        args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({k:report[k] for k in ("original_species_at_risk","direct_new_land_species","status_counts")},indent=2))
    except (KeyError,OSError,TypeError,ValueError) as err:
        sys.exit(f"FAIL CLOSED grass evolution lineage audit: {err}")


if __name__=="__main__":
    main()
