#!/usr/bin/env python3
"""Read-only FireRed -> Emerald exterior-map compatibility audit.

No graphics, warps, source binaries or saves are changed. This report is
NOT an import and does NOT imply that any FireRed map is playable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

PINNED_FIRE_RED_SHA = "ce6406d8c2eaf46d543c8a2606de0c3cb1951982"
CITY_NAMES = frozenset((
    "PalletTown", "ViridianCity", "PewterCity", "CeruleanCity",
    "LavenderTown", "VermilionCity", "CeladonCity", "FuchsiaCity",
    "CinnabarIsland", "IndigoPlateau_Exterior", "SaffronCity",
    "SaffronCity_Connection",
))
ROUTE_RE = re.compile(r"Route(?:[1-9]|1[0-9]|2[0-5])(?:_(?:North|South))?$")
REQUIRED = frozenset(("PalletTown", "VermilionCity", "Route1", "Route6", "Route11"))


class PreflightError(Exception):
    pass


def load_json(root: Path, path: str) -> dict:
    try:
        return json.loads((root / path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PreflightError(f"{path}: {exc}") from exc


def exterior_names(names: list[str]) -> list[str]:
    result, seen = [], set()
    for name in names:
        if name in CITY_NAMES or ROUTE_RE.fullmatch(name):
            if name in seen:
                raise PreflightError(f"duplicate exterior name: {name}")
            seen.add(name)
            result.append(name)
    return result


def validate_layout(source: Path, entry: dict, map_name: str) -> dict:
    w, h = entry.get("width"), entry.get("height")
    if not isinstance(w, int) or not isinstance(h, int) or w <= 0 or h <= 0:
        raise PreflightError(f"{map_name}: invalid dimensions")
    blockpath = entry["blockdata_filepath"]
    borderpath = entry["border_filepath"]
    block, border = source / blockpath, source / borderpath
    if not block.is_file() or not border.is_file():
        raise PreflightError(f"{map_name}: missing binary layout or border")
    if block.stat().st_size != w * h * 2:
        raise PreflightError(f"{map_name}: corrupt or unexpected map.bin size")
    expected_border = entry.get("border_width", 2) * entry.get("border_height", 2) * 2
    if border.stat().st_size != expected_border:
        raise PreflightError(f"{map_name}: corrupt or unexpected border.bin size")
    return {
        "width": w, "height": h,
        "blockdata_filepath": blockpath,
        "border_filepath": borderpath,
        "primary_tileset": entry["primary_tileset"],
        "secondary_tileset": entry["secondary_tileset"],
    }


def inspect(firered: Path, emerald: Path, minimum: int = 35,
            required: frozenset[str] = REQUIRED) -> dict:
    source_groups = load_json(firered, "data/maps/map_groups.json")
    source_layouts = load_json(firered, "data/layouts/layouts.json")
    target_groups = load_json(emerald, "data/maps/map_groups.json")
    target_layouts = load_json(emerald, "data/layouts/layouts.json")
    names = exterior_names(source_groups["gMapGroup_TownsAndRoutes"])
    if len(names) < minimum:
        raise PreflightError(f"expected at least {minimum} exteriors, found {len(names)}")
    missing = required.difference(names)
    if missing:
        raise PreflightError("missing required landmarks: " + ", ".join(sorted(missing)))
    # FireRed preserves empty {} positions in layouts.json for unused layout IDs.
    # They are deliberate holes in the original table, not malformed entries.
    defined_layouts = [item for item in source_layouts["layouts"] if item.get("id")]
    source_by_id = {x["id"]: x for x in defined_layouts}
    if len(source_by_id) != len(defined_layouts):
        raise PreflightError("duplicate source layout ID")
    target_layout_ids = {x["id"] for x in target_layouts["layouts"]}
    target_maps = set()
    for group in target_groups["group_order"]:
        target_maps.update(target_groups[group])

    result = {
        "source": "pret/pokefirered",
        "source_commit": PINNED_FIRE_RED_SHA,
        "mode": "READ_ONLY_PREFLIGHT",
        "imported_map_count": 0,
        "playable": False,
        "exterior_count": len(names),
        "includes_sevii": False,
        "maps": [],
    }
    for name in names:
        m = load_json(firered, f"data/maps/{name}/map.json")
        if m.get("name") != name or not str(m.get("id", "")).startswith("MAP_"):
            raise PreflightError(f"{name}: invalid identity")
        if name in target_maps:
            raise PreflightError(f"{name}: target map collision")
        src_layout = source_by_id.get(m.get("layout"))
        if src_layout is None:
            raise PreflightError(f"{name}: missing layout metadata")
        lay = validate_layout(firered, src_layout, name)
        conn = [c["map"] for c in (m.get("connections") or [])]
        warps = [w["dest_map"] for w in m.get("warp_events", [])]
        blockers = [
            "original tilesets/palettes require a separate safe port",
            "raw FRLG metatile IDs/behaviors must be mapped and collisions verified",
            "event NPC scripts/flags/vars require Emerald-compatible conversion",
            "warp destination map IDs and local indices must be validated",
            "region map/PokeNav selection must support Kanto",
        ]
        if m["layout"] not in target_layout_ids:
            blockers.append("original layout ID not registered in Emerald")
        result["maps"].append({
            "name": name, "source_id": m["id"],
            "source_layout_id": m["layout"], "layout": lay,
            "region_section": m.get("region_map_section"),
            "source_map_type": m.get("map_type"),
            "connections": conn, "warps": warps,
            "npc_count": len(m.get("object_events", [])),
            "import_status": "NOT_IMPORTED", "playable": False,
            "blockers": blockers,
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firered", type=Path, required=True)
    parser.add_argument("--emerald", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    try:
        result = inspect(options.firered, options.emerald)
    except (PreflightError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Reviewed {result['exterior_count']} original Kanto exterior maps.")
    print("Maps imported: 0. Maps playable: 0. No existing map/save modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
