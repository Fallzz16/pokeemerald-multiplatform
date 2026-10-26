#!/usr/bin/env python3
"""Propose safe-invariant, opt-in grass table entries for otherwise lost encounters.

NOT an automatic shipping fix: map tile grass, gifts and story availability
still require live verification. Never mutate World without an explicit flag.
Only use existing land slots on the SAME route where the original source has
that Pokemon via a disabled method; do not change species IDs or save layout.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

METHODS = ("water_mons", "rock_smash_mons", "fishing_mons")
ROUTE = re.compile(r"^MAP_ROUTE[0-9]")
EXPECTED_SLOTS = 12


def active_species(encounter, method):
    data = encounter.get(method)
    if not data or not isinstance(data, dict) or data.get("encounter_rate", 0) <= 0:
        return []
    mons = data.get("mons")
    if not isinstance(mons, list):
        raise ValueError(f"invalid {method} mons on {encounter.get('map')}")
    species = [x.get("species") for x in mons]
    if any(not isinstance(s, str) or not s.startswith("SPECIES_") for s in species):
        raise ValueError(f"invalid species in {method} on {encounter.get('map')}")
    return [x for x in species if x != "SPECIES_NONE"]


def propose(path):
    raw = Path(path).read_bytes()
    root = json.loads(raw)
    groups = [g for g in root["wild_encounter_groups"]
              if g.get("label") == "gWildMonHeaders" and g.get("for_maps") is True]
    if len(groups) != 1 or len(groups[0].get("encounters", [])) < 300:
        raise ValueError("missing full mapped World wild table")
    encounters = groups[0]["encounters"]
    land_global = {s for e in encounters for s in active_species(e, "land_mons")}
    disabled = {s for e in encounters for method in METHODS for s in active_species(e, method)}
    risk = sorted(disabled - land_global)
    used_maps = set()
    map_counts = Counter(e.get('map') for e in encounters)
    proposals, blocked = [], []

    # Deterministic decisions: prefer a route with >=12 conventional land slots,
    # a repeated incumbent species, and no earlier redistribution.
    for species in risk:
        candidates = []
        for entry in encounters:
            name = entry.get("map", "")
            if not isinstance(name, str) or not ROUTE.match(name) or name in used_maps or map_counts[name] != 1:
                continue
            land = entry.get("land_mons")
            if not isinstance(land, dict) or land.get("encounter_rate", 0) <= 0:
                continue
            slots = land.get("mons")
            if not isinstance(slots, list) or len(slots) != EXPECTED_SLOTS:
                continue
            method = next((m for m in METHODS if species in active_species(entry, m)), None)
            if method is None:
                continue
            incumbents = [p.get("species") for p in slots]
            if any(not isinstance(s, str) or not s.startswith("SPECIES_") for s in incumbents):
                raise ValueError(f"invalid incumbent slots on {name}")
            counts = Counter(incumbents)
            redundant = [(i, s) for i, s in enumerate(incumbents)
                         if counts[s] >= 2 and s != "SPECIES_NONE"]
            if not redundant:
                continue
            # Replace the last copy of the most-repeated incumbent,
            # guaranteeing that incumbent stays available on THIS same map.
            i, replace = max(redundant, key=lambda t: (counts[t[1]], t[0]))
            candidates.append((-counts[replace], name, i, replace, method, entry))
        if not candidates:
            blocked.append({"species": species, "reason": "no unique same-route land table with replaceable duplicate; manual grass-tile/biome review required"})
            continue
        _, route, slot, replace, method, entry = min(candidates, key=lambda t: t[:3])
        proposal = {
            "species": species, "map": route, "slot": slot,
            "replaces_one_duplicate_of": replace,
            "original_wild_method": method,
            "preserves_original_map_species": True,
            "keeps_current_route_level_curve": True,
            "grass_metatile_exists_verified": False,
            "gameplay_capture_verified": False,
            "approved_for_release": False,
        }
        proposals.append(proposal)
        used_maps.add(route)

    return root, {
        "version": 1, "source_sha256": hashlib.sha256(raw).hexdigest(),
        "mapped_records": len(encounters),
        "original_land_species": len(land_global),
        "disabled_method_species_without_land": len(risk),
        "proposed_count": len(proposals),
        "needs_manual_design_count": len(blocked),
        "proposals": proposals,
        "blocked": blocked,
        "has_modified_game": False,
        "grass_tiles_verified": False,
        "rom_emulator_verified": False,
        "release_approved": False,
    }


def make_experimental_table(path, output):
    original = Path(path)
    source_bytes = original.read_bytes()
    root, report = propose(original)
    if not report["proposals"]:
        raise ValueError("no conservative same-route recovery entries to experiment with")
    group = next(g for g in root["wild_encounter_groups"] if g.get("label") == "gWildMonHeaders")
    by_map = defaultdict(list)
    for entry in group["encounters"]:
        by_map[entry["map"]].append(entry)
    before_land = {s for e in group["encounters"] for s in active_species(e, "land_mons")}
    for item in report["proposals"]:
        entries = [e for e in by_map[item["map"]]
                   if item["species"] in active_species(e, item["original_wild_method"])]
        if len(entries) != 1:
            # Duplicate time-of-day map entries cannot be silently patched.
            raise ValueError("ambiguous encounter route: " + item["map"])
        entry = entries[0]
        arr = entry["land_mons"]["mons"]
        old = arr[item["slot"]]
        if old["species"] != item["replaces_one_duplicate_of"]:
            raise ValueError("source slot changed before applying")
        count = sum(x["species"] == old["species"] for x in arr)
        if count < 2:
            raise ValueError("would erase an incumbent species")
        # Leave min/max levels UNCHANGED to stay inside the route's progression curve.
        arr[item["slot"]] = {**old, "species": item["species"]}
    new_land = {s for e in group["encounters"] for s in active_species(e, "land_mons")}
    if not before_land.issubset(new_land):
        raise ValueError("lost original land encounter species")
    for item in report["proposals"]:
        if item["species"] not in new_land:
            raise ValueError("proposed species did not become land-encounterable")
    target = Path(output)
    if target.resolve() == original.resolve():
        raise ValueError("refusing to overwrite integrated game's original table")
    if target.exists():
        raise ValueError("experimental output already exists")
    target.write_text(json.dumps(root, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if original.read_bytes() != source_bytes:
        target.unlink(missing_ok=True)
        raise ValueError("source changed while generating experimental table")
    report["has_modified_game"] = False
    report["wrote_separate_experimental_table"] = str(target)
    report["net_new_land_species_count"] = len(new_land - before_land)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--experimental-output", type=Path,
                   help="Write a SEPARATE candidate JSON. Never overwrites the real World data")
    args = p.parse_args()
    try:
        if args.experimental_output:
            result = make_experimental_table(args.source, args.experimental_output)
        else:
            _, result = propose(args.source)
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"{result['proposed_count']} cautious same-route proposals; "
              f"{result['needs_manual_design_count']} still need manual region/biome design. "
              "No production game file changed.")
    except (ValueError, KeyError, OSError, TypeError) as err:
        sys.exit("FAIL CLOSED: " + str(err))


if __name__ == "__main__":
    main()
