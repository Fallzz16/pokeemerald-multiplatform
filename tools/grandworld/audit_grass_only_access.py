#!/usr/bin/env python3
"""Evidence-only wild encounter species access inventory for Grand World GBA.

This reads ACTUAL integrated World wild encounter JSON. It never edits the
game, and cannot prove that a species is globally unavailable (scripted
encounters, trades, evolution and events are outside this source table).
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

METHODS = ("land_mons", "water_mons", "rock_smash_mons", "fishing_mons")
DISABLED = METHODS[1:]
REQUIRED_GROUP = "gWildMonHeaders"


def read_table(path):
    payload = path.read_bytes()
    data = json.loads(payload)
    if not isinstance(data, dict) or not isinstance(data.get("wild_encounter_groups"), list):
        raise ValueError("wild encounters JSON lacks groups")
    relevant = [g for g in data["wild_encounter_groups"]
                if g.get("label") == REQUIRED_GROUP and g.get("for_maps") is True]
    if len(relevant) != 1 or not isinstance(relevant[0].get("encounters"), list):
        raise ValueError("expected exactly one mapped gWildMonHeaders group")
    return payload, relevant[0]["encounters"]


def species_for(encounter, method):
    field = encounter.get(method)
    if not field:
        return set()
    if not isinstance(field, dict):
        raise ValueError(f"{encounter.get('map')}: unsupported {method} shape")
    rate = field.get("encounter_rate", 0)
    if not isinstance(rate, int) or rate < 0:
        raise ValueError(f"{encounter.get('map')}: invalid {method} encounter rate")
    if rate == 0:
        return set()
    mons = field.get("mons")
    if not isinstance(mons, list) or not mons:
        raise ValueError(f"{encounter.get('map')}: positive {method} rate with no slots")
    names = set()
    for mon in mons:
        species = mon.get("species") if isinstance(mon, dict) else None
        if not isinstance(species, str) or not species.startswith("SPECIES_"):
            raise ValueError(f"{encounter.get('map')}: malformed {method} species")
        if species == "SPECIES_NONE":
            continue
        names.add(species)
    return names


def inventory(path, min_maps=300):
    source, entries = read_table(Path(path))
    if len(entries) < min_maps:
        raise ValueError(f"incomplete World encounter table: {len(entries)} maps")
    per_method = {m: defaultdict(set) for m in METHODS}
    map_count = 0
    for e in entries:
        if not isinstance(e, dict) or not isinstance(e.get("map"), str):
            raise ValueError("map record missing stable name")
        map_name = e["map"]
        if not map_name.startswith("MAP_"):
            raise ValueError("non-map wild record in map header table")
        map_count += 1
        for method in METHODS:
            for name in species_for(e, method):
                per_method[method][name].add(map_name)

    # Because the grass-only configuration disables water, fishing and rocks,
    # flag species that have NO land-table alternative anywhere. Do not call
    # these "unobtainable": other game mechanisms can still supply them.
    land = set(per_method["land_mons"])
    disabled_species = set().union(*(set(per_method[m]) for m in DISABLED))
    needs_review = sorted(disabled_species - land)
    rows = []
    for species in needs_review:
        methods = {m: sorted(per_method[m][species]) for m in DISABLED
                   if species in per_method[m]}
        rows.append({"species": species, "disabled_encounter_methods": methods,
                     "has_land_table_entry": False,
                     "not_proof_of_global_unavailability": True})
    return {
        "schema_version": 1,
        "target": "GBA_grass_only_PTBR_M8",
        "source_path": "src/data/wild_encounters.json",
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "mapped_encounter_records": map_count,
        "species_count_by_original_method":
            {m: len(per_method[m]) for m in METHODS},
        "disabled_method_species_not_in_any_land_table_count": len(rows),
        "species_for_review": rows,
        "method_change_applied_by_this_script": False,
        "map_grass_tiles_verified": False,
        "evolution_trade_story_and_gift_availability_verified": False,
        "globally_unobtainable_species_proven": False,
        "release_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("table", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = inventory(args.table)
    except (ValueError, OSError, TypeError) as err:
        sys.exit(f"FAIL CLOSED GBA wild method audit: {err}")
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"Reviewed {report['mapped_encounter_records']} map encounters; "
          f"{report['disabled_method_species_not_in_any_land_table_count']} "
          "species need other acquisition-method review. No data mutated.")


if __name__ == "__main__":
    main()
