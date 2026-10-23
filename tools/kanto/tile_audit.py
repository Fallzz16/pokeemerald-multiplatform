#!/usr/bin/env python3
"""Conservative read-only Kanto tile/walkability QA, never gameplay proof.

Analyzes the 0x0C00 collision mask on generated Emerald layout blockdata,
groups walkable cells into 4-neighbor components, and reports possible warp
and event isolation. Does NOT emulate elevation rules, Surf, ledges, currents,
doors, scripted movement, Strength, Cut, trainer movement or runtime saves.
Consequently split regions are warnings, not automatic build failures.
"""
from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
import struct

BLOCK_COLLISION = 0x0C00
REGIONS = ("gMapGroup_Kanto", "gMapGroup_Kanto_League")


def read_json(root: Path, relative: str):
    return json.loads((root / relative).read_text(encoding="utf-8"))


def collision_grid(data: bytes, width: int, height: int) -> list[bool]:
    """True means nominally walkable; only simple collision bits are checked."""
    if width <= 0 or height <= 0:
        raise ValueError(f"Non-positive layout dimensions: {width}x{height}")
    expected = width * height * 2
    if len(data) != expected:
        raise ValueError(
            f"Layout blockdata size {len(data)} differs from {expected} "
            f"for {width}x{height}")
    return [(tile & BLOCK_COLLISION) == 0
            for (tile,) in struct.iter_unpack("<H", data)]


def connected_components(passable: list[bool], width: int,
                         height: int) -> tuple[list[int], list[int]]:
    """A component ID for each cell (-1 blocked), and component sizes."""
    if len(passable) != width * height or width <= 0 or height <= 0:
        raise ValueError("Passability grid dimensions do not match layout")
    labels = [-1] * (width * height)
    sizes: list[int] = []
    for first, is_open in enumerate(passable):
        if not is_open or labels[first] >= 0:
            continue
        region = len(sizes)
        labels[first] = region
        queue = deque([first])
        count = 0
        while queue:
            pos = queue.popleft()
            count += 1
            x, y = pos % width, pos // width
            neighbors = []
            if x > 0:
                neighbors.append(pos - 1)
            if x + 1 < width:
                neighbors.append(pos + 1)
            if y > 0:
                neighbors.append(pos - width)
            if y + 1 < height:
                neighbors.append(pos + width)
            for nxt in neighbors:
                if passable[nxt] and labels[nxt] == -1:
                    labels[nxt] = region
                    queue.append(nxt)
        sizes.append(count)
    return labels, sizes


def adjacent_components(x: int, y: int, width: int, height: int,
                        labels: list[int]) -> set[int]:
    """Allow an adjacent clear tile if a warp/NPC itself occupies a blocked cell."""
    if not (0 <= x < width and 0 <= y < height):
        return set()
    cells = [(x, y), (x + 1, y), (x - 1, y),
             (x, y + 1), (x, y - 1)]
    return {labels[ty * width + tx]
            for tx, ty in cells
            if 0 <= tx < width and 0 <= ty < height
            and labels[ty * width + tx] != -1}


def audit_layout(name: str, map_data: dict, layout: dict,
                 blockdata: bytes) -> dict:
    """Independently evaluate one map's static tile geometry."""
    width, height = int(layout["width"]), int(layout["height"])
    walkable = collision_grid(blockdata, width, height)
    labels, sizes = connected_components(walkable, width, height)
    warnings = []
    candidates = []
    out_of_bounds = []
    no_approach = []
    for idx, warp in enumerate(map_data.get("warp_events") or []):
        x, y = int(warp["x"]), int(warp["y"])
        if not (0 <= x < width and 0 <= y < height):
            out_of_bounds.append({"type": "warp", "index": idx, "x": x, "y": y})
            continue
        near = adjacent_components(x, y, width, height, labels)
        if not near:
            no_approach.append({"type": "warp", "index": idx, "x": x, "y": y})
        candidates.append((idx, near))
    isolated_warp_pairs = []
    for first in range(len(candidates)):
        for second in range(first + 1, len(candidates)):
            a, ca = candidates[first]
            b, cb = candidates[second]
            if ca and cb and not ca.intersection(cb):
                isolated_warp_pairs.append([a, b])
    for idx, obj in enumerate(map_data.get("object_events") or []):
        if "x" not in obj or "y" not in obj:
            warnings.append(f"object[{idx}] has no static coordinates")
            continue
        x, y = int(obj["x"]), int(obj["y"])
        if not (0 <= x < width and 0 <= y < height):
            out_of_bounds.append({"type": "object", "index": idx, "x": x, "y": y})
            continue
        if not adjacent_components(x, y, width, height, labels):
            no_approach.append({"type": "object", "index": idx,
                                "x": x, "y": y,
                                "script": obj.get("script", "")})
    if out_of_bounds:
        warnings.append(f"{len(out_of_bounds)} warp/object coordinates outside layout")
    if no_approach:
        warnings.append(f"{len(no_approach)} warp/NPC events have no adjacent clear tile")
    if isolated_warp_pairs:
        warnings.append(
            f"{len(isolated_warp_pairs)} pairs of warp anchors in disconnected "
            "nominally walkable components (may be Surf/ledge/puzzle)")
    if not sizes:
        warnings.append("Map contains no nominally walkable tile")
    return {
        "map": name,
        "width": width,
        "height": height,
        "layout_id": map_data["layout"],
        "total_tiles": width * height,
        "nominally_walkable_tiles": sum(walkable),
        "nominally_blocked_tiles": len(walkable) - sum(walkable),
        "walkable_components": len(sizes),
        "largest_component_tiles": max(sizes, default=0),
        "warp_count": len(map_data.get("warp_events") or []),
        "npc_count": len(map_data.get("object_events") or []),
        "out_of_bounds": out_of_bounds,
        "potentially_unapproachable_events": no_approach,
        "disconnected_warp_pairs": isolated_warp_pairs,
        "warnings": warnings,
    }


def inspect(root: Path) -> dict:
    groups = read_json(root, "data/maps/map_groups.json")
    order = groups.get("group_order", [])
    found = [key for key in order if key in REGIONS
             or key.startswith("gMapGroup_Kanto_")]
    if not found or "gMapGroup_Kanto" not in found:
        raise ValueError("Kanto map group is not registered")
    names = [name for group in found for name in groups[group]]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate Kanto map name in registry")
    index = {x["id"]: x
             for x in read_json(root, "data/layouts/layouts.json")["layouts"]}
    summaries = []
    for name in names:
        m = read_json(root, f"data/maps/{name}/map.json")
        layout = index[m["layout"]]
        data = (root / layout["blockdata_filepath"]).read_bytes()
        summaries.append(audit_layout(name, m, layout, data))
    suspect = [m for m in summaries
               if m["warnings"]]
    return {
        "mode": "KANTO_STATIC_TILE_COLLISION_AUDIT_NOT_RUNTIME_GAMEPLAY",
        "maps_audited": len(summaries),
        "map_groups_audited": found,
        "total_nominally_walkable_tiles": sum(
            v["nominally_walkable_tiles"] for v in summaries),
        "total_nominally_blocked_tiles": sum(
            v["nominally_blocked_tiles"] for v in summaries),
        "maps_with_warnings": len(suspect),
        "maps_with_out_of_bounds_events": sum(
            bool(x["out_of_bounds"]) for x in summaries),
        "maps_with_potentially_unapproachable_events": sum(
            bool(x["potentially_unapproachable_events"]) for x in summaries),
        "maps_with_disconnected_warp_pairs": sum(
            bool(x["disconnected_warp_pairs"]) for x in summaries),
        "maps": summaries,
        "supports_surf_or_puzzles": False,
        "elevation_verified": False,
        "gameplay_verified": False,
        "save_reload_verified": False,
        "notes": [
            "Collision mask only. Possible false positives near doors and NPCs.",
            "Map graph reachability is not proof of pathfinding or gameplay.",
            "Surf, ledges, currents, Strength, Cut and scripted movement unmodelled.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emerald", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path,
                        default=Path("kanto-v24-tile-audit.json"))
    args = parser.parse_args()
    report = inspect(args.emerald.resolve())
    args.output.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Audited {report['maps_audited']} Kanto maps: "
          f"{report['maps_with_warnings']} have collision advisories.")
    print("Warnings are advisory only, not human gameplay results.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
