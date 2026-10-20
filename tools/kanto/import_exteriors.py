#!/usr/bin/env python3
"""Materialize original FRLG Kanto exterior geography into Emerald Hybrid.

The source tree is read-only; never run on personal saves. The game output is
a stage-1 outdoor geometry preview: exterior locations and collision exist,
but story/NPCs, doors, wild encounters, heals and original music are pending.
Windows build must invoke this before Makefile_pc.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import subprocess

from preflight import exterior_names, load_json, PINNED_FIRE_RED_SHA

MILESTONE = "Kanto exterior geometry stage 1"
ORIGINAL_EXTERIOR_MINIMUM = 35
CITIES = ("PalletTown", "ViridianCity", "PewterCity", "CeruleanCity",
          "LavenderTown", "VermilionCity", "CeladonCity", "FuchsiaCity",
          "CinnabarIsland", "IndigoPlateau_Exterior", "SaffronCity",
          "SaffronCity_Connection")


def emit_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def append_once(path: Path, marker: str, addition: str) -> None:
    src = path.read_text(encoding="utf-8")
    if marker in src:
        return
    path.write_text(src.rstrip() + "\n\n" + addition + "\n", encoding="utf-8")


def checkout_guard(root: Path) -> None:
    if (root / ".git").exists():
        head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                       text=True).strip()
        if head != PINNED_FIRE_RED_SHA:
            raise RuntimeError(f"FireRed SHA mismatch {head}, expected {PINNED_FIRE_RED_SHA}")


def dest_metatile_behaviors(emerald: Path) -> dict[str, int]:
    content = (emerald / "include/constants/metatile_behaviors.h").read_text(encoding="utf-8")
    enum = content.split("enum {", 1)[1].split("};", 1)[0]
    values = {}
    index = 0
    for row in enum.splitlines():
        row = row.split("//", 1)[0].strip().rstrip(",")
        match = re.fullmatch(r"(MB_[A-Z0-9_]+)(?:\s*=\s*(0x[0-9A-Fa-f]+|\d+))?", row)
        if match:
            if match.group(2):
                index = int(match.group(2), 0)
            values[match.group(1)] = index
            index += 1
    assert values["MB_NORMAL"] == 0
    assert "MB_OCEAN_WATER" in values
    return values


BEHAVIOR_ALIASES = {
    "MB_RUNNING_DISALLOWED": "MB_NO_RUNNING",
    "MB_FAST_WATER": "MB_DEEP_WATER",
    "MB_UNDERWATER_BLOCKED_ABOVE": "MB_NO_SURFACING",
    "MB_CYCLING_ROAD_WATER": "MB_OCEAN_WATER",
    "MB_JUMP_EAST": "MB_JUMP_EAST", "MB_JUMP_WEST": "MB_JUMP_WEST",
    "MB_JUMP_NORTH": "MB_JUMP_NORTH", "MB_JUMP_SOUTH": "MB_JUMP_SOUTH",
    "MB_REGULAR_WARP": "MB_AQUA_HIDEOUT_WARP",
    "MB_WARP_DOOR": "MB_ANIMATED_DOOR",
    "MB_CAVE_DOOR": "MB_NON_ANIMATED_DOOR",
    "MB_FALL_WARP": "MB_CRACKED_FLOOR_HOLE",
    "MB_STRENGTH_BUTTON": "MB_NORMAL",
    "MB_SIGNPOST": "MB_NORMAL",
    "MB_ROCK_STAIRS": "MB_NORMAL",
}


def src_behavior_names(source: Path) -> dict[int, str]:
    text = (source / "include/constants/metatile_behaviors.h").read_text(encoding="utf-8")
    matches = re.findall(r"^#define\s+(MB_[A-Z0-9_]+)\s+(0x[0-9A-Fa-f]+|\d+)", text, re.M)
    return {int(value, 0): name for name, value in matches}


def convert_attributes(raw: bytes, names: dict[int, str],
                       target: dict[str, int], unknown: Counter) -> bytes:
    if len(raw) % 4:
        raise RuntimeError("Corrupt FRLG 32-bit metatile attributes")
    output = bytearray()
    for idx in range(0, len(raw), 4):
        value = int.from_bytes(raw[idx:idx + 4], "little")
        src_behavior = value & 0x1ff
        src_name = names.get(src_behavior)
        dest_name = BEHAVIOR_ALIASES.get(src_name, src_name)
        if dest_name not in target:
            unknown[src_name or f"0x{src_behavior:03x}"] += 1
            dest_name = "MB_NORMAL"
        layer = (value >> 29) & 3
        if layer > 2:
            raise RuntimeError(f"FRLG unsupported layer type {layer} at index {idx // 4}")
        packed = (layer << 12) | target[dest_name]
        output.extend(packed.to_bytes(2, "little"))
    return bytes(output)


def source_tileset_paths(source: Path, label: str) -> Path:
    # FRLG's primary General graphics are declared in src/graphics.c,
    # while every secondary city tileset is declared in tilesets/graphics.h.
    if label == "gTileset_General":
        return source / "data/tilesets/primary/general"
    name = label.removeprefix("gTileset_")
    header = (source / "src/data/tilesets/graphics.h").read_text(encoding="utf-8")
    match = re.search(r'const u32 gTilesetTiles_' + re.escape(name) +
                      r'\[\]\s*=\s*INCBIN_U32\("([^"]+)/tiles\.4bpp\.lz"\)', header)
    if not match:
        raise RuntimeError("Missing original FireRed tileset graphic path for " + label)
    root = source / match.group(1)
    if not root.is_dir():
        raise RuntimeError("Missing original tileset directory " + str(root))
    return root


def create_tileset(source: Path, emerald: Path, original_label: str,
                   prefix: str, target: dict[str, int],
                   source_names: dict[int, str], unknown: Counter) -> tuple[str, str]:
    suffix = original_label.removeprefix("gTileset_")
    dest_label = "gTileset_Kanto" + suffix
    root = source_tileset_paths(source, original_label)
    folder = f"data/tilesets/kanto/{prefix}/{root.name}"
    dst = emerald / folder
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("tiles.png", "metatiles.bin"):
        shutil.copy2(root / name, dst / name)
    (dst / "metatile_attributes.bin").write_bytes(
        convert_attributes((root / "metatile_attributes.bin").read_bytes(),
                           source_names, target, unknown)
    )
    (dst / "palettes").mkdir(exist_ok=True)
    for idx in range(16):
        palette = root / "palettes" / f"{idx:02d}.pal"
        # The decomp stores raw colors as PNG? Source palettes are text '.pal'
        # or '.gbapal'; detect actual format and copy the canonical source.
        if not palette.exists():
            palette = root / "palettes" / f"{idx:02d}.gbapal"
        if not palette.exists():
            raise RuntimeError(f"{original_label}: source palette {idx:02d} missing")
        shutil.copy2(palette, dst / "palettes" / palette.name)

    graphics = [f'const u32 gTilesetTiles_Kanto{suffix}[] = INCBIN_U32("{folder}/tiles.4bpp.lz");',
                f'const u16 gTilesetPalettes_Kanto{suffix}[][16] = {{']
    for idx in range(16):
        graphics.append(f'    INCBIN_U16("{folder}/palettes/{idx:02d}.gbapal"),')
    graphics.append("};")
    metatiles = [
        f'const u16 gMetatiles_Kanto{suffix}[] = INCBIN_U16("{folder}/metatiles.bin");',
        f'const u16 gMetatileAttributes_Kanto{suffix}[] = INCBIN_U16("{folder}/metatile_attributes.bin");',
    ]
    header = f"""const struct Tileset {dest_label} = {{
    .isCompressed = TRUE,
    .isSecondary = {"FALSE" if prefix == "primary" else "TRUE"},
    .tiles = gTilesetTiles_Kanto{suffix},
    .palettes = gTilesetPalettes_Kanto{suffix},
    .metatiles = gMetatiles_Kanto{suffix},
    .metatileAttributes = gMetatileAttributes_Kanto{suffix},
    .callback = NULL,
}};"""
    append_once(emerald / "src/data/tilesets/graphics.h",
                f"const u32 gTilesetTiles_Kanto{suffix}[]", "\n".join(graphics))
    append_once(emerald / "src/data/tilesets/metatiles.h",
                f"const u16 gMetatiles_Kanto{suffix}[]", "\n".join(metatiles))
    append_once(emerald / "src/data/tilesets/headers.h",
                f"const struct Tileset {dest_label} =", header)
    return dest_label, folder


def safe_port_positions(blockdata: bytes, width: int, height: int) -> dict:
    """Pick connected non-collision tiles near the original Vermilion port."""
    if len(blockdata) != width * height * 2:
        raise RuntimeError("Port geometry binary size mismatch")

    def cell(x: int, y: int) -> tuple[int, int] | None:
        if x < 2 or y < 2 or x >= width - 2 or y >= height - 2:
            return None
        offset = 2 * (y * width + x)
        word = int.from_bytes(blockdata[offset:offset + 2], "little")
        if word & 0x0C00:  # GBA collision bits
            return None
        return word & 1023, (word >> 12) & 15

    # Prefer the S.S. Anne pier, but never hard-code an unverified tile.
    primary = [(x, y) for y in range(26, min(height - 2, 37))
               for x in range(17, min(width - 2, 29)) if cell(x, y)]
    primary.sort(key=lambda xy: (abs(xy[0] - 23) + abs(xy[1] - 34), xy[1], xy[0]))
    directions = [(0, -1), (-1, 0), (1, 0), (0, 1)]
    for nx, ny in primary:
        n = cell(nx, ny)
        if not n:
            continue
        for dx, dy in directions:
            px, py = nx + dx, ny + dy
            p = cell(px, py)
            if p is None or p[1] != n[1]:
                continue
            # Some maps store different elevations at a shoreline boundary.
            # Select two other walkable, same-elevation tiles for test NPCs.
            reachable = []
            for sx, sy in primary:
                if abs(sx - nx) + abs(sy - ny) < 3 or (sx, sy) == (px, py):
                    continue
                s = cell(sx, sy)
                if s is None or s[1] != n[1]:
                    continue
                if any(cell(sx + ux, sy + uy) is not None and
                       cell(sx + ux, sy + uy)[1] == s[1]
                       for ux, uy in directions):
                    reachable.append((sx, sy))
            if len(reachable) >= 2:
                # Fixed selection: deterministic across all platforms/builds.
                return {"sailor": (nx, ny, n[1]),
                        "arrival": (px, py, p[1]),
                        "healer": (*reachable[0], n[1]),
                        "encounter": (*reachable[1], n[1])}
    raise RuntimeError("Unable to find collision-free ferry + QA NPC positions in source map")


def make_qa_npc(graphics: str, script: str, spot: tuple[int, int, int]) -> dict:
    x, y, elevation = spot
    return {
        "graphics_id": graphics,
        "x": x, "y": y, "elevation": elevation,
        "movement_type": "MOVEMENT_TYPE_FACE_UP",
        "movement_range_x": 0, "movement_range_y": 0,
        "trainer_type": "TRAINER_TYPE_NONE",
        "trainer_sight_or_berry_tree_id": "0",
        "script": script, "flag": "0",
    }


def make_map(name: str, original: dict, valid: set[str]) -> dict:
    return {
        "id": "MAP_KANTO_" + name.upper(),
        "name": "Kanto_" + name,
        "layout": "LAYOUT_KANTO_" + name.upper(),
        "music": "MUS_RG_SEVII_ROUTE",
        "region_map_section": "MAPSEC_NONE",
        "requires_flash": False,
        "weather": "WEATHER_SUNNY",
        "map_type": "MAP_TYPE_CITY" if original["map_type"] == "MAP_TYPE_TOWN"
                    else original["map_type"],
        "allow_cycling": original.get("allow_cycling", True),
        "allow_escaping": False,
        "allow_running": True,
        "show_map_name": False,
        "battle_scene": "MAP_BATTLE_SCENE_NORMAL",
        "connections": [
            {"map": "MAP_KANTO_" + c["map"].removeprefix("MAP_"), # fixed below
             "offset": c["offset"], "direction": c["direction"]}
            for c in []  # filled after resolving source map ID -> directory name
        ] or None,
        "object_events": [],
        "warp_events": [],
        "coord_events": [],
        "bg_events": [],
    }


def add_firered_encounters(source: Path, emerald: Path,
                           original_id_to_name: dict[str, str]) -> int:
    """Preserve FireRed, not LeafGreen, outdoor encounter tables verbatim."""
    src = load_json(source, "src/data/wild_encounters.json")
    dest = load_json(emerald, "src/data/wild_encounters.json")
    if not src["wild_encounter_groups"] or not dest["wild_encounter_groups"]:
        raise RuntimeError("Missing encounter table structure")
    source_group = next((group for group in src["wild_encounter_groups"]
                         if group["label"] == "gWildMonHeaders" and group.get("for_maps")), None)
    target_group = next((group for group in dest["wild_encounter_groups"]
                         if group["label"] == "gWildMonHeaders" and group.get("for_maps")), None)
    if source_group is None or target_group is None:
        raise RuntimeError("Cannot locate canonical encounter group")
    species_text = (emerald / "include/constants/species.h").read_text(encoding="utf-8")
    available_species = set(re.findall(r"\bSPECIES_[A-Z0-9_]+\b", species_text))
    added = []
    used = {enc["map"] for enc in target_group["encounters"]}
    for enc in source_group["encounters"]:
        source_map = enc.get("map")
        if source_map not in original_id_to_name or not enc.get("base_label", "").endswith("_FireRed"):
            continue
        target_map = "MAP_KANTO_" + original_id_to_name[source_map].upper()
        if target_map in used:
            raise RuntimeError(f"Duplicate generated wild table: {target_map}")
        imported = json.loads(json.dumps(enc))
        imported["map"] = target_map
        imported["base_label"] = "sKanto_" + enc["base_label"]
        for key in ("land_mons", "water_mons", "rock_smash_mons", "fishing_mons"):
            for mon in imported.get(key, {}).get("mons", []):
                if mon["species"] not in available_species:
                    raise RuntimeError(f"Unknown Emerald species: {mon['species']}")
        target_group["encounters"].append(imported)
        used.add(target_map)
        added.append(target_map)
    if not added or "MAP_KANTO_ROUTE1" not in added:
        raise RuntimeError("Missing original FireRed Route 1 encounters")
    emit_json(emerald / "src/data/wild_encounters.json", dest)
    return len(added)


def copy_exteriors(source: Path, emerald: Path) -> dict:
    checkout_guard(source)
    group = load_json(source, "data/maps/map_groups.json")
    source_layouts = load_json(source, "data/layouts/layouts.json")
    target_layouts = load_json(emerald, "data/layouts/layouts.json")
    target_groups = load_json(emerald, "data/maps/map_groups.json")
    names = exterior_names(group["gMapGroup_TownsAndRoutes"])
    if len(names) < ORIGINAL_EXTERIOR_MINIMUM:
        raise RuntimeError("The pinned source unexpectedly lost Kanto exterior maps")
    if "Kanto_VermilionCity" in target_groups["gMapGroup_Kanto"]:
        raise RuntimeError("Kanto exteriors already registered: refusing duplicate import")
    layouts = {x["id"]: x for x in source_layouts["layouts"] if x.get("id")}
    source_maps = {n: load_json(source, f"data/maps/{n}/map.json") for n in names}
    source_to_name = {m["id"]: name for name, m in source_maps.items()}
    secondaries = {layouts[m["layout"]]["secondary_tileset"] for m in source_maps.values()}
    dest_behavior = dest_metatile_behaviors(emerald)
    source_behavior = src_behavior_names(source)
    unknown = Counter()
    create_tileset(source, emerald, "gTileset_General", "primary",
                   dest_behavior, source_behavior, unknown)
    for label in sorted(secondaries):
        create_tileset(source, emerald, label, "secondary",
                       dest_behavior, source_behavior, unknown)
    report = {"source_commit": PINNED_FIRE_RED_SHA,
              "state": MILESTONE,
              "geometry_maps_created": len(names),
              "graphics_tilesets_created": 1 + len(secondaries),
              "original_npcs_ported": 0,
              "interior_warps_ported": 0,
              "trainer_battles_ported": 0,
              "wild_encounters_ported": False,
              "qa_npcs_added_in_vermilion": 3,
              "qa_scripted_pidgey_battle": True,
              "qa_party_heal": True,
              "pokemon_center_heal_locations_ported": 0,
              "unknown_metatile_behaviors": dict(unknown),
              "maps": []}
    for n in names:
        m = source_maps[n]
        source_layout = layouts[m["layout"]]
        prefixed = "Kanto_" + n
        new_layout = dict(source_layout)
        new_layout.pop("border_width", None)
        new_layout.pop("border_height", None)
        new_layout["id"] = "LAYOUT_KANTO_" + n.upper()
        new_layout["name"] = prefixed + "_Layout"
        new_layout["primary_tileset"] = "gTileset_KantoGeneral"
        new_layout["secondary_tileset"] = "gTileset_Kanto" + source_layout["secondary_tileset"].removeprefix("gTileset_")
        for source_key, filename in (("border_filepath", "border.bin"),
                                     ("blockdata_filepath", "map.bin")):
            output_rel = f"data/layouts/{prefixed}/{filename}"
            output = emerald / output_rel
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / source_layout[source_key], output)
            new_layout[source_key] = output_rel
        block = (emerald / new_layout["blockdata_filepath"]).read_bytes()
        if len(block) != new_layout["width"] * new_layout["height"] * 2:
            raise RuntimeError(f"{n}: invalid source geography size")
        target_layouts["layouts"].append(new_layout)
        target_map = make_map(n, m, set(names))
        target_map["connections"] = [
            {"map": "MAP_KANTO_" + source_to_name[c["map"]].upper(),
             "offset": c["offset"], "direction": c["direction"]}
            for c in (m.get("connections") or []) if c["map"] in source_to_name
        ] or None
        if n == "VermilionCity":
            dock = safe_port_positions(block, new_layout["width"], new_layout["height"])
            target_map["object_events"].extend([
                make_qa_npc("OBJ_EVENT_GFX_SAILOR",
                            "Kanto_VermilionCity_EventScript_ReturnFerry", dock["sailor"]),
                make_qa_npc("OBJ_EVENT_GFX_NURSE",
                            "Kanto_VermilionCity_EventScript_TestHeal", dock["healer"]),
                make_qa_npc("OBJ_EVENT_GFX_BOY_1",
                            "Kanto_VermilionCity_EventScript_TestWildBattle", dock["encounter"]),
            ])
            report["landing"] = dock
        out_dir = emerald / "data/maps" / prefixed
        emit_json(out_dir / "map.json", target_map)
        scripts = f"{prefixed}_MapScripts::\n    .byte 0\n"
        if n == "VermilionCity":
            scripts += """
Kanto_VermilionCity_EventScript_ReturnFerry::
    lock
    faceplayer
    msgbox Kanto_VermilionCity_Text_ReturnToHoenn, MSGBOX_YESNO
    goto_if_eq VAR_RESULT, NO, Kanto_VermilionCity_EventScript_Stay
    closemessage
    special Kanto_ReturnToHoennHealWarp
    waitstate
    release
    end

Kanto_VermilionCity_EventScript_Stay::
    msgbox Kanto_VermilionCity_Text_Stay, MSGBOX_DEFAULT
    release
    end

Kanto_VermilionCity_Text_ReturnToHoenn:
    .string "Sail back to SLATEPORT in HOENN?$"

Kanto_VermilionCity_Text_Stay:
    .string "Enjoy KANTO!$"

@ Temporary non-original QA interactions until the interior PokeCenter
@ and the real encounters/trainer scripts are ported.
Kanto_VermilionCity_EventScript_TestHeal::
    lock
    faceplayer
    special HealPlayerParty
    msgbox Kanto_VermilionCity_Text_Healed, MSGBOX_DEFAULT
    release
    end

Kanto_VermilionCity_EventScript_TestWildBattle::
    lock
    faceplayer
    msgbox Kanto_VermilionCity_Text_BattleQuestion, MSGBOX_YESNO
    goto_if_eq VAR_RESULT, NO, Kanto_VermilionCity_EventScript_Stay
    closemessage
    setwildbattle SPECIES_PIDGEY, 5, ITEM_NONE
    dowildbattle
    release
    end

Kanto_VermilionCity_Text_Healed:
    .string "Your team was fully healed.$"

Kanto_VermilionCity_Text_BattleQuestion:
    .string "Test battle with wild PIDGEY?$"
"""
        (out_dir / "scripts.inc").write_text(scripts, encoding="utf-8")
        report["maps"].append({
            "name": n, "dimensions": [new_layout["width"], new_layout["height"]],
            "original_warps_disabled": len(m.get("warp_events", [])),
            "original_npcs_disabled": len(m.get("object_events", [])),
            "connected_exterior_edges": len(target_map["connections"] or []),
        })
    report["wild_encounter_maps_ported"] = add_firered_encounters(
        source, emerald, source_to_name)
    report["wild_encounters_ported"] = report["wild_encounter_maps_ported"] > 0
    target_groups["gMapGroup_Kanto"].extend("Kanto_" + n for n in names)
    target_groups["connections_include_order"].extend("Kanto_" + n for n in names)
    emit_json(emerald / "data/maps/map_groups.json", target_groups)
    emit_json(emerald / "data/layouts/layouts.json", target_layouts)
    inc = emerald / "data/event_scripts.s"
    code = inc.read_text(encoding="utf-8")
    anchor = '\t.include "data/maps/Kanto_Harbor/scripts.inc"'
    if anchor not in code:
        raise RuntimeError("Expected original Kanto Harbor script include not found")
    includes = "".join(f'\n\t.include "data/maps/Kanto_{n}/scripts.inc"' for n in names)
    inc.write_text(code.replace(anchor, anchor + includes, 1), encoding="utf-8")
    ferry = emerald / "data/maps/SlateportCity_Harbor/scripts.inc"
    s = ferry.read_text(encoding="utf-8")
    old = "warp MAP_KANTO_HARBOR, 8, 4"
    if s.count(old) != 1:
        raise RuntimeError("Original ferry warp modified unexpectedly")
    ax, ay, _ = report["landing"]["arrival"]
    ferry.write_text(s.replace(old, f"warp MAP_KANTO_VERMILIONCITY, {ax}, {ay}"),
                     encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firered", type=Path, required=True)
    parser.add_argument("--emerald", type=Path, default=Path("."))
    parser.add_argument("--report", type=Path, default=Path("kanto-exteriors-import.json"))
    opts = parser.parse_args()
    result = copy_exteriors(opts.firered.resolve(), opts.emerald.resolve())
    opts.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Materialized {result['geometry_maps_created']} original exterior maps "
          f"and {result['graphics_tilesets_created']} graphics sets.")
    print("WARNING: Interiors/NPCs/trainer battles/encounters/center heals remain pending.")
    print("Verify collision, palettes, map edges, ferry and save by real gameplay.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
