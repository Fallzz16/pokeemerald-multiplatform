#!/usr/bin/env python3
"""Classify which GBA grass-only species risks have source-defined level evolutions.

Never equate a source-defined EVO_LEVEL edge with actual obtainable Pokémon.
Compiled feature flags, walkable grass, capture, gifts and save behaviour still
require separate evidence. This is a read-only refinement of the 36-species risk.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

SPECIES = re.compile(r"\[(SPECIES_[A-Z0-9_]+)\]\s*=\s*\{")
EVOLUTIONS = re.compile(r"\.evolutions\s*=\s*EVOLUTION\(([\s\S]*?)\),")
LEVEL_TO = re.compile(r"\{\s*EVO_LEVEL\s*,\s*[0-9]+\s*,\s*(SPECIES_[A-Z0-9_]+)\s*\}")


def extract_level_edges(files):
    """Only exact EVO_LEVEL data (not trade, item, script or cosmetic form)."""
    edges = defaultdict(set)
    total_sources = 0
    for path in files:
        data = Path(path).read_text(encoding="utf-8")
        blocks = list(SPECIES.finditer(data))
        if not blocks:
            raise ValueError(f"no species definitions in {path}")
        total_sources += len(blocks)
        for i, m in enumerate(blocks):
            src = m.group(1)
            block = data[m.end():blocks[i + 1].start() if i + 1 < len(blocks) else len(data)]
            detail = EVOLUTIONS.search(block)
            if not detail:
                continue
            for target in LEVEL_TO.findall(detail.group(1)):
                edges[target].add(src)
    if not total_sources:
        raise ValueError("no species data")
    return edges, total_sources


def audit(wild_path, access_path, plan_path, family_files):
    # Inputs are anchored to the disposable integrated World checkout.
    encounter = json.loads(Path(wild_path).read_text(encoding="utf-8"))
    groups = [x for x in encounter["wild_encounter_groups"] if x.get("label") == "gWildMonHeaders"
              and x.get("for_maps") is True]
    if len(groups) != 1 or len(groups[0]["encounters"]) < 300:
        raise ValueError("full World map encounter source is missing")
    land = set()
    for e in groups[0]["encounters"]:
        value = e.get("land_mons")
        if value and value.get("encounter_rate", 0) > 0:
            land.update(x["species"] for x in value["mons"] if x["species"] != "SPECIES_NONE")
    access = json.loads(Path(access_path).read_text(encoding="utf-8"))
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    at_risk = {x["species"] for x in access["species_for_review"]}
    candidates = {x["species"] for x in plan["proposals"]}
    if len(at_risk) != access["disabled_method_species_not_in_any_land_table_count"]:
        raise ValueError("at-risk species count mismatch")
    if (len(candidates) != plan["proposed_count"]
        or len(candidates) + plan["needs_manual_design_count"] != len(at_risk)
        or not candidates.issubset(at_risk)
        or not land.isdisjoint(at_risk)):
        raise ValueError("unreconciled candidate set, baseline land species or audit")
    edges, source_count = extract_level_edges(family_files)
    result = {
        "schema": 1,
        "encounter_sha256": hashlib.sha256(Path(wild_path).read_bytes()).hexdigest(),
        "level_evolution_source_files": [Path(p).name for p in family_files],
        "source_species_records": source_count,
        "at_risk_species": len(at_risk),
        "candidate_land_species": len(candidates),
        "already_in_land_level_evolution": [],
        "conditional_on_candidate_level_evolution": [],
        "not_explained_by_direct_level_evolution": [],
        "source_level_only": True,
        "compiled_evolution_flags_verified": False,
        "wild_capture_verified_by_this_tool": False,
        "gift_trade_event_availability_verified": False,
        "release_approved": False,
    }
    for species in sorted(at_risk - candidates):
        parents = edges.get(species, set())
        from_existing = sorted(parents & land)
        from_candidate = sorted(parents & candidates)
        if from_existing:
            result["already_in_land_level_evolution"].append(
                {"species": species, "possible_level_parent": from_existing})
        elif from_candidate:
            result["conditional_on_candidate_level_evolution"].append(
                {"species": species, "possible_level_parent": from_candidate})
        else:
            result["not_explained_by_direct_level_evolution"].append(
                {"species": species,
                 "other_level_parents_not_proven_land_obtainable": sorted(parents - land - candidates)})
    n = sum(len(result[x]) for x in (
        "already_in_land_level_evolution",
        "conditional_on_candidate_level_evolution",
        "not_explained_by_direct_level_evolution",
    ))
    if n + len(candidates) != len(at_risk):
        raise ValueError("classified count mismatch")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wild", type=Path, required=True)
    p.add_argument("--access", type=Path, required=True)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--species-info-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    paths = sorted(args.species_info_dir.glob("gen_*_families.h"))
    if len(paths) < 9:
        sys.exit("FAIL CLOSED: must inspect all nine generations of species metadata")
    try:
        result = audit(args.wild, args.access, args.plan, paths)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("SOURCE-ONLY:",len(result["already_in_land_level_evolution"]),
              "existing land-parent evolutions;",
              len(result["conditional_on_candidate_level_evolution"]),
              "dependent on experimental land-parent candidates;",
              len(result["not_explained_by_direct_level_evolution"]),
              "still require other-source gameplay review.")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        sys.exit("FAIL CLOSED: " + str(exc))


if __name__ == "__main__":
    main()
