#!/usr/bin/env python3
"""Inspect navigable map references, not gameplay completion.

Read-only checker for Kanto map-to-map links. Only reports graph reachability;
does not claim that collision, scripts, battles or saves work.
"""
from __future__ import annotations
import argparse
from collections import deque
import json
from pathlib import Path


def load(root: Path, path: str):
    return json.loads((root / path).read_text(encoding="utf-8"))


def inspect(root: Path, origin: str = "Kanto_VermilionCity") -> dict:
    groups = load(root, "data/maps/map_groups.json")
    kanto_groups = [g for g in groups["group_order"]
                    if g == "gMapGroup_Kanto" or g.startswith("gMapGroup_Kanto_")]
    map_names = [name for g in kanto_groups for name in groups[g]]
    if len(map_names) != len(set(map_names)):
        raise ValueError("Duplicate Kanto group names")
    maps = {name: load(root, f"data/maps/{name}/map.json") for name in map_names}
    by_id = {}
    for name, value in maps.items():
        mid = value["id"]
        if mid in by_id:
            raise ValueError(f"Duplicate map ID: {mid}")
        by_id[mid] = name
    if origin not in maps:
        raise ValueError(f"Missing Kanto starting map: {origin}")
    edges = {name: set() for name in maps}
    outgoing_other_regions = {}
    for name, value in maps.items():
        for conn in value.get("connections") or []:
            dest = conn["map"]
            if dest not in by_id:
                raise ValueError(f"{name} references unregistered connection {dest}")
            edges[name].add(by_id[dest])
        for w in value.get("warp_events") or []:
            dest = w["dest_map"]
            if dest not in by_id:
                if dest.startswith("MAP_KANTO_"):
                    raise ValueError(f"{name} references missing Kanto warp target {dest}")
                outgoing_other_regions.setdefault(name, set()).add(dest)
                continue
            idx = int(w["dest_warp_id"])
            target = maps[by_id[dest]]
            if not 0 <= idx < len(target["warp_events"]):
                raise ValueError(f"{name} warp to {dest}: invalid exit index {idx}")
            edges[name].add(by_id[dest])
    visited = {origin}
    to_visit = deque([origin])
    while to_visit:
        at = to_visit.popleft()
        for dest in sorted(edges[at]):
            if dest not in visited:
                visited.add(dest)
                to_visit.append(dest)
    return {
        "mode": "KANTO_GRAPH_ONLY_NOT_GAMEPLAY_QA",
        "origin": origin,
        "total_maps": len(map_names),
        "reachable_count": len(visited),
        "unreachable_count": len(map_names)-len(visited),
        "reachable_maps": sorted(visited),
        "unreachable_maps": sorted(set(map_names)-visited),
        "off_region_map_links": {
            name: sorted(targets) for name, targets in outgoing_other_regions.items()
        },
        "all_kanto_destinations_and_indices_valid": True,
        "gameplay_verified": False,
        "collision_verified": False,
        "saves_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emerald", type=Path, default=Path("."))
    parser.add_argument("--origin", default="Kanto_VermilionCity")
    parser.add_argument("--output", type=Path, default=Path("kanto-reachability.json"))
    args = parser.parse_args()
    data = inspect(args.emerald.resolve(), args.origin)
    args.output.write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
    print(f"Kanto geometry: {data['reachable_count']}/{data['total_maps']} maps "
          f"reachable from {args.origin} by declared map edges/warps.")
    print("Graph report only; not evidence of working movement or story.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
