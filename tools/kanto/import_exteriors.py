#!/usr/bin/env python3
"""Materialize original FRLG Kanto exterior geography into Emerald Hybrid.

The pinned FireRed source tree is read-only and must never touch personal saves.
The importer builds a V0.13 experimental Kanto preview with exterior regions,
selected interiors, connected caves and towers, encounters, items, five trainers,
and separate regional whiteout; a complete story, gyms, original music, PokeNav
and real gameplay QA remain pending. Run it before Makefile_pc.
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



def render_firered_mart_stock(source: Path, emerald: Path,
                             original_map: str, new_label: str) -> str:
    """Port only the original FRLG ITEM_* constants, not its story scripts."""
    content = (source / "data/maps" / original_map / "scripts.inc").read_text(encoding="utf-8")
    needle = original_map + "_Items"
    matches = list(re.finditer(r"(?m)^\s*" + re.escape(needle) + r"::\s*$", content))
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one inventory for {original_map}")
    defs = (emerald / "include/constants/items.h").read_text(encoding="utf-8")
    known = set(re.findall(r"(?m)^\s*#define\s+(ITEM_[A-Z0-9_]+)\s+", defs))
    items = []
    for line in content[matches[0].end():].splitlines():
        m = re.match(r"^\s*\.2byte\s+(ITEM_[A-Z0-9_]+)\s*(?:@.*)?$", line)
        if m is None:
            if line.strip().startswith(".2byte"):
                raise RuntimeError(f"Invalid stock entry in {original_map}: {line}")
            continue
        item = m.group(1)
        if item == "ITEM_NONE":
            if not items or len(items) > 32 or len(set(items)) != len(items):
                raise RuntimeError(f"Empty/duplicate/oversized stock: {original_map}")
            return ("\n    .align 2\n" + new_label + ":\n"
                    + "".join(f"    .short {name}\n" for name in items)
                    + "    pokemartlistend\n")
        if item not in known:
            raise RuntimeError(f"Unavailable Emerald item {item} from {original_map}")
        items.append(item)
    raise RuntimeError(f"Unterminated FireRed inventory: {original_map}")


# Region-specific last-heal index is persistent in save var 0x40F7.
# Append-only IDs; keep synchronized with include/constants/vars.h.
KANTO_HEAL_LOCATIONS = {
    "VermilionCity": 1,
    "ViridianCity": 2,
    "PewterCity": 3,
    "CeruleanCity": 4,
    "LavenderTown": 5,
    "CeladonCity": 6,
    "FuchsiaCity": 7,
    "CinnabarIsland": 8,
    "SaffronCity": 9,
}


def add_vermilion_interiors(source: Path, emerald: Path, layouts: dict,
                           target_layouts: dict, target_groups: dict,
                           vermilion: dict) -> list[str]:
    """Port the original FireRed Pokemon Center and Mart geometries.

    Use exact original entry tiles and interior dimensions. Only the selected
    building entrance/exit warps are enabled; the upstairs Cable Club is left
    disabled until it has an individually QA-tested Kanto map.
    """
    specs = [
        ("VermilionCity_PokemonCenter_1F", "LAYOUT_POKEMON_CENTER_1F",
         "LAYOUT_KANTO_POKEMON_CENTER_1F", "gTileset_KantoPokemonCenter",
         "MUS_POKE_CENTER", "Kanto_VermilionCity_PokemonCenter_1F", 0,
         "OBJ_EVENT_GFX_NURSE", "Kanto_VermilionCenter_EventScript_Nurse", (7, 2, 3)),
        ("VermilionCity_Mart", "LAYOUT_MART", "LAYOUT_KANTO_MART",
         "gTileset_KantoMart", "MUS_POKE_MART",
         "Kanto_VermilionCity_Mart", 1,
         "OBJ_EVENT_GFX_MART_EMPLOYEE", "Kanto_VermilionMart_EventScript_Clerk", (2, 3, 0)),
    ]
    created = []
    original_exits = vermilion.get("warp_events") or []
    for (source_name, source_layout_id, target_layout_id, secondary, music,
         target_name, outside_index, gfx, script_label, npc) in specs:
        m = load_json(source, f"data/maps/{source_name}/map.json")
        if m["layout"] != source_layout_id:
            raise RuntimeError(f"Unexpected FireRed interior layout for {source_name}")
        l = layouts[source_layout_id]
        new_layout = dict(l)
        new_layout.pop("border_width", None)
        new_layout.pop("border_height", None)
        new_layout.update({
            "id": target_layout_id,
            "name": target_name + "_Layout",
            "primary_tileset": "gTileset_KantoBuilding",
            "secondary_tileset": secondary,
        })
        for source_key, filename in (("border_filepath", "border.bin"),
                                     ("blockdata_filepath", "map.bin")):
            output_rel = f"data/layouts/{target_name}/{filename}"
            output = emerald / output_rel
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / l[source_key], output)
            new_layout[source_key] = output_rel
        raw = (emerald / new_layout["blockdata_filepath"]).read_bytes()
        if len(raw) != new_layout["width"] * new_layout["height"] * 2:
            raise RuntimeError(f"Wrong FireRed interior blockdata size: {target_name}")
        target_layouts["layouts"].append(new_layout)

        outside_warp_id = 4 if outside_index == 0 else 7
        outside = original_exits[outside_warp_id]
        if outside["dest_map"] != m["id"]:
            raise RuntimeError(f"Source outdoor warp #{outside_warp_id} mismatch")

        # The original source has three adjacent exit tiles for both buildings.
        door_events = [e for e in m["warp_events"]
                       if e["dest_map"] == "MAP_VERMILION_CITY"]
        if len(door_events) != 3:
            raise RuntimeError(f"Unexpected number of original exits: {source_name}")
        target_warps = [{
            "x": e["x"], "y": e["y"], "elevation": e["elevation"],
            "dest_map": "MAP_KANTO_VERMILIONCITY",
            "dest_warp_id": str(outside_index),
        } for e in door_events]
        x, y, elevation = npc
        obj = make_qa_npc(gfx, script_label, npc)
        if outside_index == 0:
            obj["local_id"] = "LOCALID_KANTO_VERMILION_NURSE"
        map_obj = {
            "id": "MAP_KANTO_" + source_name.upper(),
            "name": target_name, "layout": target_layout_id, "music": music,
            "region_map_section": "MAPSEC_NONE",
            "requires_flash": False, "weather": "WEATHER_NONE",
            "map_type": "MAP_TYPE_INDOOR", "allow_cycling": False,
            "allow_escaping": False, "allow_running": False,
            "show_map_name": False, "battle_scene": "MAP_BATTLE_SCENE_NORMAL",
            "connections": None, "object_events": [obj],
            "warp_events": target_warps, "coord_events": [], "bg_events": [],
        }
        out = emerald / "data/maps" / target_name
        emit_json(out / "map.json", map_obj)
        if outside_index == 0:
            scripts = """Kanto_VermilionCity_PokemonCenter_1F_MapScripts::
    map_script MAP_SCRIPT_ON_TRANSITION, Kanto_VermilionCenter_SetHealLocation
    .byte 0

@ Save an independent regional Center ID without overwriting Hoenn's heal warp.
Kanto_VermilionCenter_SetHealLocation:
    setvar VAR_KANTO_LAST_HEAL_LOCATION, KANTO_HEAL_VERMILION_CITY
    end
Kanto_VermilionCenter_EventScript_Nurse::
    setvar VAR_0x800B, LOCALID_KANTO_VERMILION_NURSE
    call Common_EventScript_PkmnCenterNurse
    waitmessage
    waitbuttonpress
    release
    end
"""
        else:
            scripts = """Kanto_VermilionCity_Mart_MapScripts::
    .byte 0

Kanto_VermilionMart_EventScript_Clerk::
    lock
    faceplayer
    message gText_HowMayIServeYou
    waitmessage
    pokemart Kanto_VermilionMart_Items
    msgbox gText_PleaseComeAgain, MSGBOX_DEFAULT
    release
    end

"""
        if outside_index == 1:
            scripts += render_firered_mart_stock(
                source, emerald, source_name, "Kanto_VermilionMart_Items")
        (out / "scripts.inc").write_text(scripts, encoding="utf-8")
        # Use original exterior entrance coordinates, but new warp IDs (0/1)
        # reflect the subset of usable doors at this milestone.
        entry = {
            "x": outside["x"], "y": outside["y"],
            "elevation": outside["elevation"], "dest_map": map_obj["id"],
            "dest_warp_id": "1",
        }
        created.append(target_name)
    target_groups["gMapGroup_Kanto"].extend(created)
    return created




def add_regional_service_interiors(source: Path, emerald: Path, source_maps: dict,
                                  target_groups: dict) -> list[str]:
    """Enable the canonical 1F centers and Marts of Kanto's other cities.

    Reuse the already-ported original FRLG interior layouts, graphics and
    metatiles; require original source exits/entries for every generated
    door. Only service NPCs are initially brought over. No upstairs link-room
    warp is activated and no new save-block field is introduced.
    """
    cities = (
        "ViridianCity", "PewterCity", "CeruleanCity", "LavenderTown",
        "CeladonCity", "FuchsiaCity", "CinnabarIsland", "SaffronCity",
    )
    created: list[str] = []
    for city in cities:
        outside_source = source_maps.get(city)
        if outside_source is None:
            raise RuntimeError(f"Missing expected original Kanto city: {city}")
        external_path = emerald / "data/maps" / f"Kanto_{city}" / "map.json"
        exterior = load_json(emerald, str(external_path.relative_to(emerald)))
        for kind in ("PokemonCenter_1F", "Mart"):
            source_name = f"{city}_{kind}"
            file = source / "data/maps" / source_name / "map.json"
            if not file.is_file():
                if city == "CeladonCity" and kind == "Mart":
                    # The original Celadon city uses a department store.
                    continue
                raise RuntimeError(f"Missing expected FRLG service interior: {source_name}")
            original = load_json(source, f"data/maps/{source_name}/map.json")
            is_center = kind == "PokemonCenter_1F"
            expected_layout = "LAYOUT_POKEMON_CENTER_1F" if is_center else "LAYOUT_MART"
            if original["layout"] != expected_layout:
                raise RuntimeError(f"Unsupported nonstandard layout for {source_name}")
            entrances = [w for w in outside_source["warp_events"]
                         if w["dest_map"] == original["id"]]
            if not entrances:
                raise RuntimeError(f"{city}: FireRed city has no entrance to {source_name}")
            exits = [w for w in original["warp_events"]
                     if w["dest_map"] == outside_source["id"]]
            if not exits:
                raise RuntimeError(f"{source_name}: missing original exterior exit")
            exterior_warp_id = len(exterior["warp_events"])
            target_name = "Kanto_" + source_name
            target_id = "MAP_KANTO_" + source_name.upper()
            local_id = f"LOCALID_KANTO_{city.upper()}_NURSE"
            suffix = "Nurse" if is_center else "Clerk"
            script_label = f"{target_name}_EventScript_{suffix}"
            role = "OBJ_EVENT_GFX_NURSE" if is_center else "OBJ_EVENT_GFX_CLERK"
            actors = [o for o in original["object_events"]
                      if o.get("graphics_id") == role]
            if len(actors) != 1:
                raise RuntimeError(f"{source_name}: expected one canonical service NPC; found {len(actors)}")
            npc = actors[0]
            role_gfx = "OBJ_EVENT_GFX_NURSE" if is_center else "OBJ_EVENT_GFX_MART_EMPLOYEE"
            obj = make_qa_npc(role_gfx, script_label,
                              (npc["x"], npc["y"], npc["elevation"]))
            if is_center:
                obj["local_id"] = local_id

            map_obj = {
                "id": target_id, "name": target_name,
                "layout": "LAYOUT_KANTO_POKEMON_CENTER_1F" if is_center else "LAYOUT_KANTO_MART",
                "music": "MUS_POKE_CENTER" if is_center else "MUS_POKE_MART",
                "region_map_section": "MAPSEC_NONE", "requires_flash": False,
                "weather": "WEATHER_NONE", "map_type": "MAP_TYPE_INDOOR",
                "allow_cycling": False, "allow_escaping": False,
                "allow_running": False, "show_map_name": False,
                "battle_scene": "MAP_BATTLE_SCENE_NORMAL",
                "connections": None,
                "object_events": [obj],
                "warp_events": [{
                    "x": w["x"], "y": w["y"], "elevation": w["elevation"],
                    "dest_map": exterior["id"],
                    "dest_warp_id": str(exterior_warp_id),
                } for w in exits],
                "coord_events": [], "bg_events": [],
            }
            if is_center:
                heal_macro = "KANTO_HEAL_" + re.sub(r"(?<!^)(?=[A-Z])", "_", city).upper()
                if KANTO_HEAL_LOCATIONS.get(city) is None:
                    raise RuntimeError(f"Unknown Kanto Center for regional heal {city}")
                transition_label = target_name + "_SetHealLocation"
                scripts = f"""{target_name}_MapScripts::
    map_script MAP_SCRIPT_ON_TRANSITION, {transition_label}
    .byte 0

{transition_label}:
    setvar VAR_KANTO_LAST_HEAL_LOCATION, {heal_macro}
    end

{script_label}::
    setvar VAR_0x800B, {local_id}
    call Common_EventScript_PkmnCenterNurse
    waitmessage
    waitbuttonpress
    release
    end
"""
            else:
                scripts = f"""{target_name}_MapScripts::
    .byte 0

{script_label}::
    lock
    faceplayer
    message gText_HowMayIServeYou
    waitmessage
    pokemart {target_name}_Items
    msgbox gText_PleaseComeAgain, MSGBOX_DEFAULT
    release
    end
"""
            out = emerald / "data/maps" / target_name
            emit_json(out / "map.json", map_obj)
            if not is_center:
                scripts += render_firered_mart_stock(
                    source, emerald, source_name, target_name + "_Items")
            (out / "scripts.inc").write_text(scripts, encoding="utf-8")
            for w in entrances:
                exterior["warp_events"].append({
                    "x": w["x"], "y": w["y"],
                    "elevation": w["elevation"],
                    "dest_map": target_id,
                    # Original 1F source warp 1 is a safe lobby entrance.
                    # Use the first interior exit/entry warp when there is only one.
                    "dest_warp_id": "1" if len(exits) > 1 else "0",
                })
            created.append(target_name)
        emit_json(external_path, exterior)

    if len(created) != 15:
        raise RuntimeError(f"Wrong Kanto city service count: {len(created)}, expected 15")

    # Delay registration to preserve V0.2 map indices during version upgrades.
    return created


def add_saffron_gatehouses(source: Path, emerald: Path, source_maps: dict,
                          layouts: dict, target_layouts: dict,
                          target_groups: dict) -> list[str]:
    """Port real FRLG north/south/east/west Saffron gatehouse passages.

    Preserve the FireRed index of the entrance inside each gate. Original
    exterior warp indices must be explicitly remapped because V0.3 exteriors
    already contain new generated services. All old map IDs are untouched.
    """
    gate_names = ("Route5_SouthEntrance", "Route6_NorthEntrance",
                  "Route7_EastEntrance", "Route8_WestEntrance")
    gates = {name: load_json(source, f"data/maps/{name}/map.json")
             for name in gate_names}
    if len({obj["id"] for obj in gates.values()}) != len(gates):
        raise RuntimeError("Duplicate original Saffron gate IDs")
    gate_by_id = {m["id"]: name for name, m in gates.items()}
    outdoor_by_id = {m["id"]: name for name, m in source_maps.items()}
    named_gate_layouts = {
        "LAYOUT_SAFFRON_CITY_NORTH_SOUTH_ENTRANCE": "LAYOUT_KANTO_SAFFRON_GATE_NS",
        "LAYOUT_SAFFRON_CITY_EAST_WEST_ENTRANCE": "LAYOUT_KANTO_SAFFRON_GATE_EW",
    }
    for original_id, dest_id in named_gate_layouts.items():
        item = layouts[original_id]
        if (item["primary_tileset"] != "gTileset_Building"
                or item["secondary_tileset"] != "gTileset_GenericBuilding2"):
            raise RuntimeError(f"Unexpected FireRed gatehouse tilesets: {original_id}")
        new_layout = dict(item)
        new_layout.pop("border_width", None)
        new_layout.pop("border_height", None)
        new_layout["id"] = dest_id
        new_layout["name"] = dest_id + "_Layout"
        new_layout["primary_tileset"] = "gTileset_KantoBuilding"
        new_layout["secondary_tileset"] = "gTileset_KantoGenericBuilding2"
        for source_key, filename in (("border_filepath", "border.bin"),
                                     ("blockdata_filepath", "map.bin")):
            dest_rel = f"data/layouts/{dest_id}/{filename}"
            dest = emerald / dest_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / item[source_key], dest)
            new_layout[source_key] = dest_rel
        if (emerald / new_layout["blockdata_filepath"]).stat().st_size != (
                new_layout["width"] * new_layout["height"] * 2):
            raise RuntimeError(f"Malformed FireRed gatehouse layout {original_id}")
        target_layouts["layouts"].append(new_layout)

    # Copy ONLY the exterior doors whose original destination is one of
    # these four gates; never bring across incomplete locations.
    original_to_new_warp = {}
    for outside_name, original in source_maps.items():
        matching = [(idx, w) for idx, w in enumerate(original.get("warp_events") or [])
                    if w["dest_map"] in gate_by_id]
        if not matching:
            continue
        path = emerald / "data/maps" / ("Kanto_" + outside_name) / "map.json"
        target = load_json(emerald, str(path.relative_to(emerald)))
        for original_idx, w in matching:
            gate_name = gate_by_id[w["dest_map"]]
            local_idx = len(target["warp_events"])
            target["warp_events"].append({
                "x": w["x"], "y": w["y"], "elevation": w["elevation"],
                "dest_map": "MAP_KANTO_" + gate_name.upper(),
                "dest_warp_id": str(w["dest_warp_id"]),
            })
            original_to_new_warp[(original["id"], original_idx)] = local_idx
        emit_json(path, target)

    created = []
    for name in gate_names:
        original = gates[name]
        src_layout_id = original["layout"]
        if src_layout_id not in named_gate_layouts:
            raise RuntimeError(f"Unsupported Saffron gate layout: {src_layout_id}")
        target_name = "Kanto_" + name
        warps = []
        for src_warp in original["warp_events"]:
            outside_original_id = src_warp["dest_map"]
            if outside_original_id not in outdoor_by_id:
                raise RuntimeError(f"{name}: gate warp targets an unported exterior")
            outside_idx = int(src_warp["dest_warp_id"])
            lookup = (outside_original_id, outside_idx)
            if lookup not in original_to_new_warp:
                raise RuntimeError(f"{name}: destination exterior warp not materialized: {lookup}")
            warps.append({
                "x": src_warp["x"], "y": src_warp["y"],
                "elevation": src_warp["elevation"],
                "dest_map": "MAP_KANTO_" + outdoor_by_id[outside_original_id].upper(),
                "dest_warp_id": str(original_to_new_warp[lookup]),
            })
        if not warps:
            raise RuntimeError(f"{name}: gatehouse has no active warp events")
        map_obj = {
            "id": "MAP_KANTO_" + name.upper(),
            "name": target_name, "layout": named_gate_layouts[src_layout_id],
            "music": "MUS_RG_SEVII_ROUTE", "region_map_section": "MAPSEC_NONE",
            "requires_flash": False, "weather": "WEATHER_NONE",
            "map_type": "MAP_TYPE_INDOOR", "allow_cycling": False,
            "allow_escaping": False, "allow_running": False,
            "show_map_name": False, "battle_scene": "MAP_BATTLE_SCENE_NORMAL",
            "connections": None, "object_events": [],
            "warp_events": warps, "coord_events": [], "bg_events": [],
        }
        dest = emerald / "data/maps" / target_name
        emit_json(dest / "map.json", map_obj)
        (dest / "scripts.inc").write_text(
            target_name + "_MapScripts::\n    .byte 0\n", encoding="utf-8"
        )
        created.append(target_name)
    # Keep previously released Kanto map IDs unchanged; registration happens
    # only after exteriors and service interiors are fully registered.
    return created


# Core original dungeon transitions that make route-level Kanto navigation useful.
# Order is append-only: existing V0.5 IDs must never be renumbered.
KANTO_V06_DUNGEONS = (
    "ViridianForest",
    "Route2_ViridianForest_NorthEntrance",
    "Route2_ViridianForest_SouthEntrance",
    "DiglettsCave_NorthEntrance",
    "DiglettsCave_B1F",
    "DiglettsCave_SouthEntrance",
    "MtMoon_1F",
    "MtMoon_B1F",
    "MtMoon_B2F",
)


KANTO_V07_DUNGEONS = (
    "UndergroundPath_NorthEntrance",
    "UndergroundPath_NorthSouthTunnel",
    "UndergroundPath_SouthEntrance",
    "UndergroundPath_WestEntrance",
    "UndergroundPath_EastWestTunnel",
    "UndergroundPath_EastEntrance",
    "RockTunnel_1F",
    "RockTunnel_B1F",
    "PokemonTower_1F",
    "PokemonTower_2F",
    "PokemonTower_3F",
    "PokemonTower_4F",
    "PokemonTower_5F",
    "PokemonTower_6F",
    "PokemonTower_7F",
)


KANTO_V12_DUNGEONS = (
    "VictoryRoad_1F", "VictoryRoad_2F", "VictoryRoad_3F",
    "PokemonMansion_1F", "PokemonMansion_2F",
    "PokemonMansion_3F", "PokemonMansion_B1F",
    "CeruleanCave_1F", "CeruleanCave_2F", "CeruleanCave_B1F",
    "SeafoamIslands_1F", "SeafoamIslands_B1F",
    "SeafoamIslands_B2F", "SeafoamIslands_B3F", "SeafoamIslands_B4F",
)


KANTO_V14_GYMS = (
    "ViridianCity_Gym", "PewterCity_Gym",
    "CeruleanCity_Gym", "VermilionCity_Gym",
    "CeladonCity_Gym", "FuchsiaCity_Gym",
    "CinnabarIsland_Gym", "SaffronCity_Gym",
)


KANTO_V15_LEAGUE = (
    "IndigoPlateau_PokemonCenter_1F",
    "PokemonLeague_LoreleisRoom", "PokemonLeague_BrunosRoom",
    "PokemonLeague_AgathasRoom", "PokemonLeague_LancesRoom",
    "PokemonLeague_ChampionsRoom", "PokemonLeague_HallOfFame",
)


def add_kanto_v06_dungeons(source: Path, emerald: Path, source_maps: dict,
                          layouts: dict, target_layouts: dict,
                          selected: tuple[str, ...] = KANTO_V06_DUNGEONS,
                          omitted_warp_destinations: tuple[str,...] = ()) -> dict:
    """Port all 9 original layouts and their real intra-dungeon/exterior doors.

    Original interior warp indices are retained in complete dungeons. Exterior
    warp indices differ in Emerald because services/gates were already ported;
    remap them to generated new indices and reject dangling destinations.
    Existing exterior warp indices are NEVER reordered.
    """
    maps = {name: load_json(source, f"data/maps/{name}/map.json")
            for name in selected}
    by_source_id = {entry["id"]: name for name, entry in maps.items()}
    if len(by_source_id) != len(maps):
        raise RuntimeError("Duplicate source Kanto dungeon map IDs")
    outside_by_source_id = {obj["id"]: name for name, obj in source_maps.items()}
    old_warp_to_new = {}
    exterior_warps_added = 0

    # First create every new outward door on previously generated exterior
    # maps, appending at the end; record a precise (map, old warp id) remap.
    for outer_name, original in source_maps.items():
        relevant = [
            (idx, w) for idx, w in enumerate(original.get("warp_events") or [])
            if w["dest_map"] in by_source_id
        ]
        if not relevant:
            continue
        relative = f"data/maps/Kanto_{outer_name}/map.json"
        target = load_json(emerald, relative)
        for src_idx, entry in relevant:
            target_idx = len(target["warp_events"])
            target["warp_events"].append({
                "x": entry["x"], "y": entry["y"],
                "elevation": entry["elevation"],
                "dest_map": "MAP_KANTO_" + by_source_id[entry["dest_map"]].upper(),
                "dest_warp_id": str(entry["dest_warp_id"]),
            })
            old_warp_to_new[(original["id"], src_idx)] = target_idx
            exterior_warps_added += 1
        emit_json(emerald / relative, target)

    # All original warp targets in the selected nine maps must be either
    # another fully ported dungeon map or one of the 38 existing exteriors.
    warps_created = 0
    for name in selected:
        original = maps[name]
        lay = layouts.get(original["layout"])
        if lay is None:
            raise RuntimeError(f"{name}: missing FireRed dungeon layout")
        if lay["primary_tileset"] not in ("gTileset_General", "gTileset_Building"):
            raise RuntimeError(f"{name}: unsupported dungeon primary tileset")
        if original.get("connections"):
            raise RuntimeError(f"{name}: unported connected dungeon edges")
        target_name = "Kanto_" + name
        dest_id = "MAP_KANTO_" + name.upper()
        new_layout = dict(lay)
        new_layout.pop("border_width", None)
        new_layout.pop("border_height", None)
        new_layout["id"] = "LAYOUT_KANTO_" + name.upper()
        new_layout["name"] = target_name + "_Layout"
        new_layout["primary_tileset"] = (
            "gTileset_KantoGeneral" if lay["primary_tileset"] == "gTileset_General"
            else "gTileset_KantoBuilding"
        )
        new_layout["secondary_tileset"] = (
            "gTileset_Kanto" + lay["secondary_tileset"].removeprefix("gTileset_")
        )
        for key, filename in (("border_filepath", "border.bin"),
                              ("blockdata_filepath", "map.bin")):
            path = f"data/layouts/{target_name}/{filename}"
            output = emerald / path
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / lay[key], output)
            new_layout[key] = path
        if (emerald / new_layout["blockdata_filepath"]).stat().st_size != (
                new_layout["width"] * new_layout["height"] * 2):
            raise RuntimeError(f"{name}: source map binary size mismatch")
        expected_border = (lay.get("border_width", 2)
                           * lay.get("border_height", 2) * 2)
        if (emerald / new_layout["border_filepath"]).stat().st_size != expected_border:
            raise RuntimeError(f"{name}: unexpected border size")
        target_layouts["layouts"].append(new_layout)

        warps = []
        for i, entry in enumerate(original.get("warp_events") or []):
            dest_src = entry["dest_map"]
            # Leave the unsupported original upstairs link/Cable Club
            # inaccessible. No dynamic warp or save/link emulation.
            if dest_src in omitted_warp_destinations:
                continue
            if dest_src in by_source_id:
                destination = "MAP_KANTO_" + by_source_id[dest_src].upper()
                dest_warp_id = int(entry["dest_warp_id"])
                if not 0 <= dest_warp_id < len(maps[by_source_id[dest_src]]["warp_events"]):
                    raise RuntimeError(f"{name} warp {i}: invalid internal warp index")
            elif dest_src in outside_by_source_id:
                destination = "MAP_KANTO_" + outside_by_source_id[dest_src].upper()
                key = (dest_src, int(entry["dest_warp_id"]))
                if key not in old_warp_to_new:
                    raise RuntimeError(f"{name} warp {i}: exterior destination not linked {key}")
                dest_warp_id = old_warp_to_new[key]
            else:
                raise RuntimeError(f"{name} warp {i}: target not imported {dest_src}")
            warps.append({
                "x": entry["x"], "y": entry["y"],
                "elevation": entry["elevation"],
                "dest_map": destination,
                "dest_warp_id": str(dest_warp_id),
            })
        map_obj = {
            "id": dest_id,
            "name": target_name,
            "layout": new_layout["id"],
            "music": "MUS_RG_SEVII_ROUTE",
            "region_map_section": "MAPSEC_NONE",
            "requires_flash": original.get("requires_flash", False),
            "weather": "WEATHER_NONE",
            "map_type": original["map_type"],
            "allow_cycling": original.get("allow_cycling", False),
            "allow_escaping": original.get("allow_escaping", True),
            "allow_running": original.get("allow_running", True),
            "show_map_name": False,
            "battle_scene": "MAP_BATTLE_SCENE_NORMAL",
            "connections": None,
            "object_events": [],
            "warp_events": warps,
            "coord_events": [],
            "bg_events": [],
        }
        out = emerald / "data/maps" / target_name
        emit_json(out / "map.json", map_obj)
        (out / "scripts.inc").write_text(
            target_name + "_MapScripts::\n    .byte 0\n",
            encoding="utf-8"
        )
        warps_created += len(warps)
    return {
        "names": ["Kanto_" + n for n in selected],
        "source_ids": {maps[n]["id"]: n for n in selected},
        "internal_warps": warps_created,
        "exterior_warps": exterior_warps_added,
    }


def import_kanto_visible_items(source: Path, emerald: Path,
                               original_map_names: list[str],
                               minimum: int = 15) -> dict:
    """Enable FireRed item balls with permanent, isolated save flags.

    Deterministic allocation uses original V0.2–V0.7 map order and original
    NPC order. All future maps MUST be appended to original_map_names, never
    inserted or reordered, to preserve item pickup flags in existing saves.
    """
    script_source = (source / "data/scripts/item_ball_scripts.inc").read_text(
        encoding="utf-8"
    )
    source_items = {}
    for label, item in re.findall(
        r"(?m)^\s*([A-Za-z0-9_]+)::\s*\n\s*finditem\s+"
        r"(ITEM_[A-Z0-9_]+)\s*\n\s*end\b", script_source
    ):
        if label in source_items:
            raise RuntimeError(f"Duplicate FireRed item ball script {label}")
        source_items[label] = item
    flag_header = emerald / "include/constants/flags.h"
    header = flag_header.read_text(encoding="utf-8")
    reserved = sorted(
        {int(x,16) for x in re.findall(
            r"(?m)^#define FLAG_UNUSED_0x([0-9A-Fa-f]{3})\s+", header
        ) if 0x264 <= int(x,16) < 0x500}
    )
    item_definitions = (emerald / "include/constants/items.h").read_text(
        encoding="utf-8"
    )
    valid_items = set(re.findall(
        r"(?m)^\s*#define\s+(ITEM_[A-Z0-9_]+)\s+", item_definitions
    ))
    if not reserved:
        raise RuntimeError("Missing permanent flag allocation pool")
    count = 0
    inventory = []
    for name in original_map_names:
        original = load_json(source, f"data/maps/{name}/map.json")
        balls = [o for o in original.get("object_events", [])
                 if o.get("graphics_id") == "OBJ_EVENT_GFX_ITEM_BALL"]
        if not balls:
            continue
        target_name = "Kanto_" + name
        target_path = f"data/maps/{target_name}/map.json"
        m = load_json(emerald, target_path)
        scripts_path = emerald / "data/maps" / target_name / "scripts.inc"
        scripts = scripts_path.read_text(encoding="utf-8")
        for within, obj in enumerate(balls):
            if count >= len(reserved):
                raise RuntimeError(f"Permanent Kanto item flag pool exhausted: {count}")
            original_label = obj["script"]
            item = source_items.get(original_label)
            if item is None:
                raise RuntimeError(f"{name}: unsupported original item script {original_label}")
            if item not in valid_items:
                raise RuntimeError(f"{name}: Emerald does not provide original item {item}")
            flag = f"FLAG_KANTO_ITEM_{count:03d}"
            label = f"Kanto_{name}_EventScript_ItemBall_{within:03d}"
            if label + "::" in scripts:
                raise RuntimeError(f"{name}: item script already installed {label}")
            new_obj = {
                "graphics_id": "OBJ_EVENT_GFX_ITEM_BALL",
                "x": obj["x"], "y": obj["y"],
                "elevation": obj["elevation"],
                "movement_type": "MOVEMENT_TYPE_FACE_DOWN",
                "movement_range_x": 0, "movement_range_y": 0,
                "trainer_type": "TRAINER_TYPE_NONE",
                "trainer_sight_or_berry_tree_id": "0",
                "script": label,
                "flag": flag,
            }
            if any(event["x"] == obj["x"] and event["y"] == obj["y"]
                   for event in m["object_events"]):
                raise RuntimeError(f"{name}: item collides with another object at "
                                   f"{obj['x']}, {obj['y']}")
            m["object_events"].append(new_obj)
            scripts += f"\n{label}::\n    finditem {item}\n    end\n"
            inventory.append({
                "map": target_name,
                "position": [obj["x"], obj["y"]],
                "item": item,
                "source_script": original_label,
                "generated_script": label,
                "flag": flag,
                "flag_value": reserved[count],
            })
            count += 1
        emit_json(emerald / target_path, m)
        scripts_path.write_text(scripts, encoding="utf-8")

    if count < minimum:
        raise RuntimeError(f"Suspiciously few FireRed item balls found: {count}")
    final_defines = "".join(
        f"#define {row['flag']:<36} FLAG_UNUSED_0x{row['flag_value']:03X}\n"
        for row in inventory
    )
    footer = "#endif // GUARD_CONSTANTS_FLAGS_H"
    if footer not in header or "FLAG_KANTO_ITEM_000" in header:
        raise RuntimeError("Cannot allocate Kanto item flags: header changed")
    flag_header.write_text(
        header.replace(footer, f"// Kanto persistent item balls (reserved unused flags).\n"
                       + final_defines + "\n" + footer),
        encoding="utf-8"
    )
    return {"total": count, "items": inventory}


def import_kanto_hidden_items(source: Path, emerald: Path,
                              original_map_names: list[str],
                              visible_item_flags: list[dict],
                              minimum: int = 5) -> dict:
    """Port original FireRed hidden items without reusing visible-item save bits.

    Hidden flags are append-only after the existing V0.8 visible-item flag
    allocation. Caller must not reorder earlier source map lists.
    """
    header_path = emerald / "include/constants/flags.h"
    header = header_path.read_text(encoding="utf-8")
    if "FLAG_KANTO_HIDDEN_000" in header:
        raise RuntimeError("Kanto hidden items already registered")
    reserved = sorted({
        int(v, 16) for v in re.findall(
            r"(?m)^#define FLAG_UNUSED_0x([0-9A-Fa-f]{3})\s+", header
        ) if 0x264 <= int(v, 16) < 0x500
    })
    used_visible = {x["flag_value"] for x in visible_item_flags}
    if len(used_visible) != len(visible_item_flags):
        raise RuntimeError("Duplicate previous visible item save flags")
    if not used_visible.issubset(set(reserved)):
        raise RuntimeError("Visible items use flags outside permanent spare pool")
    spare = [flag for flag in reserved if flag not in used_visible]
    defined_items = set(re.findall(
        r"(?m)^\s*#define\s+(ITEM_[A-Z0-9_]+)\s+",
        (emerald / "include/constants/items.h").read_text(encoding="utf-8")
    ))
    rows = []
    for name in original_map_names:
        frmap = load_json(source, f"data/maps/{name}/map.json")
        found = [event for event in frmap.get("bg_events", [])
                 if event.get("type") == "hidden_item"]
        if not found:
            continue
        target_name = "Kanto_" + name
        target_path = f"data/maps/{target_name}/map.json"
        target = load_json(emerald, target_path)
        for ev in found:
            if len(rows) >= len(spare):
                raise RuntimeError("Kanto hidden item flag capacity exhausted")
            if ev["item"] not in defined_items:
                raise RuntimeError(
                    f"{name}: hidden item unavailable in Emerald: {ev['item']}")
            if ev.get("quantity", 1) < 1:
                raise RuntimeError(f"{name}: invalid hidden item quantity")
            if any(bg["x"] == ev["x"] and bg["y"] == ev["y"]
                   and bg.get("type") == "hidden_item"
                   for bg in target["bg_events"]):
                raise RuntimeError(f"{name}: duplicate hidden item position")
            flag = f"FLAG_KANTO_HIDDEN_{len(rows):03d}"
            target["bg_events"].append({
                "type": "hidden_item",
                "x": ev["x"], "y": ev["y"],
                "elevation": ev["elevation"],
                "item": ev["item"],
                "flag": flag,
                "quantity": ev.get("quantity", 1),
                "underfoot": ev.get("underfoot", False),
            })
            rows.append({
                "map": target_name,
                "position": [ev["x"], ev["y"]],
                "item": ev["item"],
                "quantity": ev.get("quantity", 1),
                "underfoot": ev.get("underfoot", False),
                "flag": flag,
                "flag_value": spare[len(rows)],
            })
        emit_json(emerald / target_path, target)
    if len(rows) < minimum:
        raise RuntimeError("Far too few FireRed hidden items found")
    footer = "#endif // GUARD_CONSTANTS_FLAGS_H"
    if footer not in header:
        raise RuntimeError("Invalid permanent flag constants header")
    definitions = "".join(
        f"#define {x['flag']:<36} FLAG_UNUSED_0x{x['flag_value']:03X}\n"
        for x in rows
    )
    header_path.write_text(
        header.replace(footer, "// Kanto original hidden items; flags independent of visible pickups.\n"
                       + definitions + "\n" + footer), encoding="utf-8"
    )
    return {"total":len(rows), "items":rows}


def import_v13_major_dungeon_items(source: Path, emerald: Path,
                                   dungeon_names: tuple[str, ...],
                                   prior_visible: list[dict],
                                   prior_hidden: list[dict],
                                   minimum_visible: int = 30,
                                   minimum_hidden: int = 5) -> dict:
    """Append fresh pickup flags AFTER all 119 V0.8–V0.11 flags.

    Never reuse or renumber historical item definitions. Newly added
    dungeons are processed in a pinned map order, first visible, then
    hidden, so a save stays stable across identical source revisions.
    """
    flagfile = emerald / "include/constants/flags.h"
    flags = flagfile.read_text(encoding="utf-8")
    old = prior_visible + prior_hidden
    previous = [row["flag_value"] for row in old]
    if len(previous) != len(set(previous)):
        raise RuntimeError("Previous Kanto pickup flag collision")
    reserved = sorted(set(
        int(x,16) for x in re.findall(
            r"(?m)^#define FLAG_UNUSED_0x([0-9A-Fa-f]{3})\s+", flags)
        if 0x264 <= int(x,16) < 0x500
    ))
    free = [value for value in reserved if value not in set(previous)]
    valid_items = set(re.findall(
        r"(?m)^\s*#define\s+(ITEM_[A-Z0-9_]+)\s+",
        (emerald / "include/constants/items.h").read_text(encoding="utf-8")
    ))
    original_script = (
        source / "data/scripts/item_ball_scripts.inc"
    ).read_text(encoding="utf-8")
    item_scripts = dict(re.findall(
        r"(?m)^\s*([A-Za-z0-9_]+)::\s*\n\s*finditem\s+"
        r"(ITEM_[A-Z0-9_]+)\s*\n\s*end\b", original_script
    ))
    pending = []
    snapshots = {}
    for map_name in dungeon_names:
        original = load_json(source,f"data/maps/{map_name}/map.json")
        target = load_json(emerald,f"data/maps/Kanto_{map_name}/map.json")
        script_path = emerald / "data/maps" / ("Kanto_"+map_name) / "scripts.inc"
        snapshots[map_name] = (original,target,script_path,
                               script_path.read_text(encoding="utf-8"))
    for category in ("visible","hidden"):
        for name in dungeon_names:
            original,target,path,scripts=snapshots[name]
            if category=="visible":
                balls = [o for o in original["object_events"]
                         if o.get("graphics_id")=="OBJ_EVENT_GFX_ITEM_BALL"]
                for obj in balls:
                    source_label=obj["script"]
                    item=item_scripts.get(source_label)
                    if item is None or item not in valid_items:
                        raise RuntimeError(f"{name}: unavailable source item ball {source_label}")
                    num=sum(1 for row in pending if row["category"]=="visible")
                    flag=f"FLAG_KANTO_V13_BALL_{num:03d}"
                    label=f"Kanto_{name}_EventScript_V13Item_{num:03d}"
                    if any(x["x"]==obj["x"] and x["y"]==obj["y"]
                           for x in target["object_events"]):
                        raise RuntimeError(f"{name}: item ball position already occupied")
                    target["object_events"].append({
                        "graphics_id":"OBJ_EVENT_GFX_ITEM_BALL",
                        "x":obj["x"],"y":obj["y"],"elevation":obj["elevation"],
                        "movement_type":"MOVEMENT_TYPE_FACE_DOWN",
                        "movement_range_x":0,"movement_range_y":0,
                        "trainer_type":"TRAINER_TYPE_NONE",
                        "trainer_sight_or_berry_tree_id":"0",
                        "script":label,"flag":flag,
                    })
                    scripts+=f"\n{label}::\n    finditem {item}\n    end\n"
                    pending.append({"category":"visible","map":"Kanto_"+name,
                                    "position":[obj["x"],obj["y"]],
                                    "item":item,"flag":flag,
                                    "generated_script":label})
            else:
                for obj in original["bg_events"]:
                    if obj.get("type") != "hidden_item":
                        continue
                    item=obj["item"]
                    if item not in valid_items:
                        raise RuntimeError(f"{name}: unknown hidden item {item}")
                    num=sum(1 for row in pending if row["category"]=="hidden")
                    flag=f"FLAG_KANTO_V13_HIDDEN_{num:03d}"
                    target["bg_events"].append({
                        "type":"hidden_item","x":obj["x"],"y":obj["y"],
                        "elevation":obj["elevation"],"item":item,"flag":flag,
                        "quantity":obj.get("quantity",1),
                        "underfoot":obj.get("underfoot",False),
                    })
                    pending.append({"category":"hidden","map":"Kanto_"+name,
                                    "position":[obj["x"],obj["y"]],"item":item,
                                    "quantity":obj.get("quantity",1),
                                    "underfoot":obj.get("underfoot",False),
                                    "flag":flag})
            snapshots[name]=(original,target,path,scripts)
    nv=sum(row["category"]=="visible" for row in pending)
    nh=sum(row["category"]=="hidden" for row in pending)
    if nv<minimum_visible or nh<minimum_hidden or len(pending)>len(free):
        raise RuntimeError(f"Unsafe original dungeon pickups: visible={nv}, hidden={nh}, free={len(free)}")
    if "FLAG_KANTO_V13_BALL_000" in flags or "FLAG_KANTO_V13_HIDDEN_000" in flags:
        raise RuntimeError("Dungeon item flags already allocated")
    for i,row in enumerate(pending):
        row["flag_value"]=free[i]
    for name in dungeon_names:
        original,target,path,scripts=snapshots[name]
        emit_json(path.parent/"map.json",target)
        path.write_text(scripts,encoding="utf-8")
    footer="#endif // GUARD_CONSTANTS_FLAGS_H"
    if footer not in flags:
        raise RuntimeError("Flag header footer missing")
    defines="".join(
        f"#define {row['flag']:<38} FLAG_UNUSED_0x{row['flag_value']:03X}\n"
        for row in pending)
    flagfile.write_text(
        flags.replace(footer,"// V0.13 dungeon pickups allocated AFTER 119 original item flags.\n"
                      +defines+"\n"+footer),encoding="utf-8"
    )
    return {"visible_count":nv,"hidden_count":nh,"items":pending}


def import_viridian_forest_trainers(source: Path, emerald: Path) -> dict:
    """Port the five original FRLG Viridian Forest Bug Catchers.

    Reuses only five of the nine already-reserved unused trainer flag slots
    (IDs 855..859). Does not grow save flags or override Hoenn trainers.
    The original species/levels/party order are retained, with locally
    authored short dialogue until a complete script/text port is QA-approved.
    """
    originals = ("Rick", "Doug", "Sammy", "Anthony", "Charlie")
    source_map = load_json(source, "data/maps/ViridianForest/map.json")
    original_parties = (
        source / "src/data/trainer_parties.h"
    ).read_text(encoding="utf-8")
    original_definitions = (
        source / "src/data/trainers.h"
    ).read_text(encoding="utf-8")
    opponents = emerald / "include/constants/opponents.h"
    trainer_header = emerald / "src/data/trainers.h"
    party_header = emerald / "src/data/trainer_parties.h"
    limits = opponents.read_text(encoding="utf-8")
    if "#define TRAINERS_COUNT                      855" not in limits:
        raise RuntimeError("Unexpected trainer table size; spare IDs may be used")
    if "#define MAX_TRAINERS_COUNT                  864" not in limits:
        raise RuntimeError("Unexpected trainer flag reservation; unsafe to append")
    selected = []
    new_party_data = []
    new_trainer_data = []
    map_path = emerald / "data/maps/Kanto_ViridianForest/map.json"
    forest = load_json(emerald, "data/maps/Kanto_ViridianForest/map.json")
    forest_scripts = emerald / "data/maps/Kanto_ViridianForest/scripts.inc"
    scripts = forest_scripts.read_text(encoding="utf-8")
    trainer_texts = {}
    for index, name in enumerate(originals):
        source_trainer = "TRAINER_BUG_CATCHER_" + name.upper()
        target_trainer = "TRAINER_KANTO_FOREST_" + name.upper()
        object_label = "ViridianForest_EventScript_" + name
        actors = [o for o in source_map["object_events"]
                  if o.get("script") == object_label
                  and o["trainer_type"] == "TRAINER_TYPE_NORMAL"]
        if len(actors) != 1:
            raise RuntimeError(f"Unexpected source Bug Catcher event: {name}")
        assert target_trainer not in limits
        if source_trainer not in original_definitions:
            raise RuntimeError(f"Original trainer data missing: {source_trainer}")
        original_party = "sParty_BugCatcher" + name
        pattern = (r"static const struct TrainerMonNoItemDefaultMoves "
                   + re.escape(original_party) + r"\[\]\s*=\s*\{"
                   + r"([\s\S]*?)\n\};")
        match = re.search(pattern, original_parties)
        if match is None:
            raise RuntimeError(f"Cannot find original party {original_party}")
        body = match.group(1)
        if not re.search(r"\.lvl\s*=\s*\d+", body) or not re.search(r"\.species\s*=\s*SPECIES_", body):
            raise RuntimeError(f"Empty or invalid original party {original_party}")
        new_party_name = "sParty_KantoForest" + name
        new_party_data.append(
            f"static const struct TrainerMonNoItemDefaultMoves {new_party_name}[] = {{"
            + body + "\n};\n"
        )
        new_trainer_data.append(f"""    [{target_trainer}] =
    {{
        .trainerClass = TRAINER_CLASS_BUG_CATCHER,
        .encounterMusic_gender = TRAINER_ENCOUNTER_MUSIC_MALE,
        .trainerPic = TRAINER_PIC_BUG_CATCHER,
        .trainerName = _("{name.upper()}"),
        .items = {{}},
        .doubleBattle = FALSE,
        .aiFlags = AI_SCRIPT_CHECK_BAD_MOVE,
        .party = NO_ITEM_DEFAULT_MOVES({new_party_name}),
    }},
""")
        obj = actors[0]
        event_label = "Kanto_ViridianForest_EventScript_BugCatcher" + name
        intro = "Kanto_Forest_Text_" + name + "_Intro"
        defeat = "Kanto_Forest_Text_" + name + "_Defeat"
        after = "Kanto_Forest_Text_" + name + "_After"
        forest["object_events"].append({
            "graphics_id": "OBJ_EVENT_GFX_BUG_CATCHER",
            "x": obj["x"], "y": obj["y"],
            "elevation": obj["elevation"],
            "movement_type": obj["movement_type"],
            "movement_range_x": obj["movement_range_x"],
            "movement_range_y": obj["movement_range_y"],
            "trainer_type": "TRAINER_TYPE_NORMAL",
            "trainer_sight_or_berry_tree_id": obj["trainer_sight_or_berry_tree_id"],
            "script": event_label, "flag": "0",
        })
        scripts += (
            f"\n{event_label}::\n"
            f"    trainerbattle_single {target_trainer}, {intro}, {defeat}\n"
            f"    msgbox {after}, MSGBOX_AUTOCLOSE\n"
            "    end\n\n"
            f'{intro}:\n    .string "My BUG POKeMON are ready!$"\n\n'
            f'{defeat}:\n    .string "Good battle!$"\n\n'
            f'{after}:\n    .string "I will keep training here.$"\n'
        )
        selected.append({"name":name, "id":855+index,
                         "original":source_trainer,
                         "party":new_party_name,
                         "coords":[obj["x"],obj["y"]]})
    assert len(selected)==5
    limits=limits.replace("#define TRAINERS_COUNT                      855",
                          "".join(
                              f"#define TRAINER_KANTO_FOREST_{n.upper():<16} {855+i}\n"
                              for i,n in enumerate(originals)
                          ) + "#define TRAINERS_COUNT                      860")
    opponents.write_text(limits,encoding="utf-8")
    parties=party_header.read_text(encoding="utf-8")
    if "sParty_KantoForestRick" in parties:
        raise RuntimeError("Forest trainers already in target trainer parties")
    party_header.write_text(parties.rstrip()+"\n\n"+"\n".join(new_party_data),encoding="utf-8")
    trainers=trainer_header.read_text(encoding="utf-8")
    if "TRAINER_KANTO_FOREST_RICK" in trainers or not trainers.rstrip().endswith("};"):
        raise RuntimeError("Trainer array cannot be safely extended")
    index=trainers.rfind("};")
    trainer_header.write_text(
        trainers[:index]+ "\n" + "\n".join(new_trainer_data) + trainers[index:],
        encoding="utf-8"
    )
    emit_json(map_path,forest)
    forest_scripts.write_text(scripts,encoding="utf-8")
    return {"count":len(selected),"trainers":selected}



KANTO_V16_LEADERS = (
    ("Brock", "PewterCity", "BOULDER", "ITEM_TM39", "ROXANNE"),
    ("Misty", "CeruleanCity", "CASCADE", "ITEM_TM03", "WINONA"),
    ("LtSurge", "VermilionCity", "THUNDER", "ITEM_TM34", "WATTSON"),
    ("Erika", "CeladonCity", "RAINBOW", "ITEM_TM19", "FLANNERY"),
)


def import_first_kanto_gym_leaders(source: Path, emerald: Path,
                                   all_used_item_flags: list[dict]) -> dict:
    """Four real FireRed parties, original locations and isolated Kanto badges.

    This uses the final four trainer IDs 860–863 already reserved in Emerald's
    864-bit trainer defeat field. Do not add trainer IDs past 863 without
    designing and verifying a backwards-compatible save migration.
    """
    opponents = emerald / "include/constants/opponents.h"
    parties_path = emerald / "src/data/trainer_parties.h"
    trainers_path = emerald / "src/data/trainers.h"
    flags_path = emerald / "include/constants/flags.h"
    limits = opponents.read_text(encoding="utf-8")
    if "#define TRAINERS_COUNT                      860" not in limits:
        raise RuntimeError("Forest trainer setup missing or table size changed")
    if "#define MAX_TRAINERS_COUNT                  864" not in limits:
        raise RuntimeError("Cannot extend trainer table without safe flags")
    raw_party = (source / "src/data/trainer_parties.h").read_text(encoding="utf-8")
    raw_trainers = (source / "src/data/trainers.h").read_text(encoding="utf-8")
    emerald_items = (emerald / "include/constants/items.h").read_text(encoding="utf-8")
    item_constants = set(re.findall(
        r"(?m)^\s*#define\s+(ITEM_[A-Z0-9_]+)\s+", emerald_items))
    emerald_species = (emerald / "include/constants/species.h").read_text(encoding="utf-8")
    emerald_moves = (emerald / "include/constants/moves.h").read_text(encoding="utf-8")
    available_species = set(re.findall(r"\bSPECIES_[A-Z0-9_]+\b", emerald_species))
    available_moves = set(re.findall(r"\bMOVE_[A-Z0-9_]+\b", emerald_moves))
    flags = flags_path.read_text(encoding="utf-8")
    used = [row["flag_value"] for row in all_used_item_flags]
    if len(used) != len(set(used)) or len(used) < 160:
        raise RuntimeError("Prior permanent Kanto item flags invalid")
    available = sorted({
        int(value, 16) for value in re.findall(
            r"(?m)^#define FLAG_UNUSED_0x([0-9A-Fa-f]{3})\s+", flags)
        if 0x264 <= int(value, 16) < 0x500
    })
    free = [value for value in available if value not in set(used)]
    if len(free) < 8:
        raise RuntimeError("Not enough saved flag bits for Kanto badges and TM grants")
    if "FLAG_KANTO_BADGE_BOULDER" in flags:
        raise RuntimeError("Kanto gym badges already initialized")
    additional_parties, additional_trainers, declarations = [], [], []
    new_flags, results = [], []
    for index, (leader, city, badge, tm, portrait) in enumerate(KANTO_V16_LEADERS):
        if tm not in item_constants:
            raise RuntimeError(f"Original TM unavailable in Emerald: {tm}")
        source_trainer = "TRAINER_LEADER_" + re.sub(r"(?<!^)(?=[A-Z])", "_", leader).upper()
        source_map = load_json(source, f"data/maps/{city}_Gym/map.json")
        actors = [o for o in source_map["object_events"]
                  if o.get("script","").endswith("_EventScript_"+leader)]
        if len(actors) != 1:
            raise RuntimeError(f"Expected exactly one original {leader} in {city} Gym")
        original_party = "sParty_Leader" + leader
        match = re.search(
            r"static const struct TrainerMonNoItemCustomMoves\s+"
            + re.escape(original_party) + r"\[\]\s*=\s*\{([\s\S]*?)\n\};",
            raw_party)
        if not match:
            raise RuntimeError(f"Missing original FireRed party for {leader}")
        body = match.group(1)
        for mon in re.findall(r"\bSPECIES_[A-Z0-9_]+\b", body):
            if mon not in available_species:
                raise RuntimeError(f"Emerald lacks FireRed gym Pokemon {mon}")
        for move in re.findall(r"\bMOVE_[A-Z0-9_]+\b", body):
            if move not in available_moves:
                raise RuntimeError(f"Emerald lacks FireRed gym move {move}")
        if ".lvl" not in body or ".moves" not in body:
            raise RuntimeError(f"Malformed original FireRed trainer party for {leader}")
        leader_def = re.search(
            r"\[" + re.escape(source_trainer) + r"\]\s*=\s*\{([\s\S]*?)\n\s*\},",
            raw_trainers)
        if not leader_def:
            raise RuntimeError(f"Missing original FRLG leader {source_trainer}")
        original_items = re.search(r"\.items\s*=\s*(\{[^\}]*\})", leader_def.group(1))
        if not original_items:
            raise RuntimeError(f"Missing original medicine for {leader}")
        for item in re.findall(r"ITEM_[A-Z0-9_]+", original_items.group(1)):
            if item not in item_constants:
                raise RuntimeError(f"Unsupported source trainer item {item}")
        target = "TRAINER_KANTO_LEADER_" + re.sub(
            r"(?<!^)(?=[A-Z])", "_", leader).upper()
        party_label = "sParty_KantoLeader" + leader
        additional_parties.append(
            f"static const struct TrainerMonNoItemCustomMoves {party_label}[] = {{"
            + body + "\n};\n")
        is_female = leader in ("Misty", "Erika")
        additional_trainers.append(f"""    [{target}] =
    {{
        .trainerClass = TRAINER_CLASS_LEADER,
        .encounterMusic_gender = {"F_TRAINER_FEMALE | TRAINER_ENCOUNTER_MUSIC_FEMALE" if is_female else "TRAINER_ENCOUNTER_MUSIC_MALE"},
        .trainerPic = TRAINER_PIC_LEADER_{portrait},
        .trainerName = _("{'LT. SURGE' if leader == 'LtSurge' else leader.upper()}"),
        .items = {original_items.group(1)},
        .doubleBattle = FALSE,
        .aiFlags = AI_SCRIPT_CHECK_BAD_MOVE | AI_SCRIPT_TRY_TO_FAINT | AI_SCRIPT_CHECK_VIABILITY,
        .party = NO_ITEM_CUSTOM_MOVES({party_label}),
    }},
""")
        declarations.append(f"#define {target:<45} {860+index}\n")
        path = f"data/maps/Kanto_{city}_Gym/map.json"
        output = load_json(emerald, path)
        event_script = f"Kanto_{city}_Gym_EventScript_Leader{leader}"
        if any(o.get("script") == event_script for o in output["object_events"]):
            raise RuntimeError(f"Duplicate gym leader in {city}")
        original = actors[0]
        output["object_events"].append({
            "graphics_id": "OBJ_EVENT_GFX_" + portrait,
            "x": original["x"], "y": original["y"],
            "elevation": original["elevation"],
            "movement_type": "MOVEMENT_TYPE_FACE_DOWN",
            "movement_range_x": 0, "movement_range_y": 0,
            "trainer_type": "TRAINER_TYPE_NONE",
            "trainer_sight_or_berry_tree_id": "0",
            "script": event_script, "flag": "0",
        })
        emit_json(emerald / path, output)
        scriptfile = emerald / "data/maps" / f"Kanto_{city}_Gym/scripts.inc"
        scripts = scriptfile.read_text(encoding="utf-8")
        intro, defeat, after = [f"Kanto_{city}_Gym_Text_{leader}_{suffix}"
                                for suffix in ("Intro", "Defeat", "After")]
        won = f"Kanto_{city}_Gym_EventScript_{leader}Won"
        reward = f"Kanto_{city}_Gym_EventScript_{leader}TM"
        badge_symbol = f"FLAG_KANTO_BADGE_{badge}"
        tm_symbol = f"FLAG_KANTO_TM_{badge}"
        scripts += f"""
{event_script}::
    lock
    faceplayer
    goto_if_set {badge_symbol}, {reward}
    trainerbattle_single {target}, {intro}, {defeat}, {won}, NO_MUSIC
    msgbox {after}, MSGBOX_DEFAULT
    release
    end

{won}::
    setflag {badge_symbol}
    call Common_EventScript_PlayGymBadgeFanfare
    goto {reward}
    end

{reward}::
    goto_if_set {tm_symbol}, Kanto_{city}_Gym_EventScript_{leader}AfterTM
    giveitem {tm}
    goto_if_eq VAR_RESULT, FALSE, Common_EventScript_ShowBagIsFull
    setflag {tm_symbol}
Kanto_{city}_Gym_EventScript_{leader}AfterTM::
    msgbox {after}, MSGBOX_DEFAULT
    release
    end

{intro}:
    .string "Challenge me for a KANTO BADGE?$"

{defeat}:
    .string "Your team fought well.$"

{after}:
    .string "You earned the {badge} BADGE!$"
"""
        scriptfile.write_text(scripts, encoding="utf-8")
        new_flags.extend([
            (badge_symbol, free[2*index]),
            (tm_symbol, free[2*index+1]),
        ])
        results.append({
            "name": leader, "city": city,
            "trainer_id": 860+index, "source_trainer":source_trainer,
            "trainer_macro": target, "party":party_label,
            "badge_flag":badge_symbol,"tm_flag":tm_symbol,
            "tm":tm, "source_coords":[original["x"],original["y"]],
            "badge_flag_value":free[2*index],
            "tm_flag_value":free[2*index+1],
            "portrait_is_temporary": True
        })
    opponents.write_text(
        limits.replace("#define TRAINERS_COUNT                      860",
                       "".join(declarations)
                       + "#define TRAINERS_COUNT                      864"),
        encoding="utf-8"
    )
    parties = parties_path.read_text(encoding="utf-8")
    parties_path.write_text(parties.rstrip() + "\n\n"
                            + "\n".join(additional_parties),encoding="utf-8")
    trainers = trainers_path.read_text(encoding="utf-8")
    if not trainers.rstrip().endswith("};"):
        raise RuntimeError("Unexpected Emerald trainer array format")
    index = trainers.rfind("};")
    trainers_path.write_text(
        trainers[:index] + "\n" + "\n".join(additional_trainers) + trainers[index:],
        encoding="utf-8"
    )
    footer = "#endif // GUARD_CONSTANTS_FLAGS_H"
    if footer not in flags:
        raise RuntimeError("Flag header end changed unexpectedly")
    flag_definitions = "".join(
        f"#define {key:<40} FLAG_UNUSED_0x{value:03X}\n"
        for key,value in new_flags)
    flags_path.write_text(
        flags.replace(footer,"// Kanto independent gym badges / one-time TMs.\n"
                      +flag_definitions+"\n"+footer),encoding="utf-8"
    )
    return {"count":len(results), "leaders": results}


KANTO_V17_LEADERS = (
    ("Koga", "FuchsiaCity", "SOUL", "ITEM_TM06", "BRAWLY"),
    ("Sabrina", "SaffronCity", "MARSH", "ITEM_TM04", "WINONA"),
    ("Blaine", "CinnabarIsland", "VOLCANO", "ITEM_TM38", "WATTSON"),
    ("Giovanni", "ViridianCity", "EARTH", "ITEM_TM26", "ROXANNE"),
)


def import_remaining_kanto_gym_leaders(source: Path, emerald: Path,
                                      previously_used: list[dict]) -> dict:
    """Use separate saved flags for trainers 864-867; do not grow SaveBlock."""
    opponent_path = emerald / "include/constants/opponents.h"
    party_path = emerald / "src/data/trainer_parties.h"
    trainer_path = emerald / "src/data/trainers.h"
    flag_path = emerald / "include/constants/flags.h"
    old_opponents = opponent_path.read_text(encoding="utf-8")
    if ("#define TRAINERS_COUNT                      864" not in old_opponents
            or "#define MAX_TRAINERS_COUNT                  864" not in old_opponents):
        raise RuntimeError("Expected four first leaders and 864 save-backed trainer bits")
    flags = flag_path.read_text(encoding="utf-8")
    reserved = sorted({int(x,16) for x in re.findall(
        r"(?m)^#define FLAG_UNUSED_0x([0-9A-Fa-f]{3})\s+",flags)
        if 0x264 <= int(x,16) < 0x500})
    occupied = [row["flag_value"] for row in previously_used]
    if len(occupied) != len(set(occupied)) or len(occupied) < 168:
        raise RuntimeError("Original Kanto pickup and badge allocations invalid")
    free = [n for n in reserved if n not in set(occupied)]
    if len(free) < len(KANTO_V17_LEADERS)*3:
        raise RuntimeError("No spare saved flag slots for extended trainers")
    raw_parties = (source/"src/data/trainer_parties.h").read_text(encoding="utf-8")
    raw_trainers = (source/"src/data/trainers.h").read_text(encoding="utf-8")
    trainer_src = trainer_path.read_text(encoding="utf-8")
    party_src = party_path.read_text(encoding="utf-8")
    valid_items = set(re.findall(r"\bITEM_[A-Z0-9_]+\b",
                                 (emerald/"include/constants/items.h").read_text(encoding="utf-8")))
    species = set(re.findall(r"\bSPECIES_[A-Z0-9_]+\b",
                              (emerald/"include/constants/species.h").read_text(encoding="utf-8")))
    moves = set(re.findall(r"\bMOVE_[A-Z0-9_]+\b",
                            (emerald/"include/constants/moves.h").read_text(encoding="utf-8")))
    if not trainer_src.rstrip().endswith("};"):
        raise RuntimeError("Unexpected target trainer table")
    new_trainers = []
    new_parties = []
    new_constants = []
    flag_declarations = []
    rows = []
    for i,(leader,city,badge,tm,pic) in enumerate(KANTO_V17_LEADERS):
        source_id = "TRAINER_LEADER_"+leader.upper()
        target_id = "TRAINER_KANTO_LEADER_"+leader.upper()
        party_label = "sParty_Leader"+leader
        source_party = re.search(
            r"static const struct TrainerMonNoItemCustomMoves\s+"
            +re.escape(party_label)+r"\[\]\s*=\s*\{([\s\S]*?)\n\};",
            raw_parties)
        source_record = re.search(
            r"\["+re.escape(source_id)+r"\]\s*=\s*\{([\s\S]*?)\n\s*\},",
            raw_trainers)
        if not source_party or not source_record:
            raise RuntimeError(f"Missing original gym team for {leader}")
        body=source_party.group(1)
        if (not re.findall(r"\.lvl\s*=\s*\d+",body)
            or any(k not in species for k in re.findall(r"\bSPECIES_[A-Z0-9_]+\b",body))
            or any(k not in moves for k in re.findall(r"\bMOVE_[A-Z0-9_]+\b",body))):
            raise RuntimeError(f"Unsupported original gym leader Pokemon/move: {leader}")
        item_match=re.search(r"\.items\s*=\s*(\{[^\}]*\})",source_record.group(1))
        if not item_match or any(x not in valid_items for x in re.findall(
                r"ITEM_[A-Z0-9_]+",item_match.group(1))):
            raise RuntimeError(f"Unsupported FireRed trainer medicine: {leader}")
        if tm not in valid_items:
            raise RuntimeError(f"Gym TM {tm} missing in Emerald")
        new_party_name="sParty_KantoV17Leader"+leader
        new_parties.append(
            "static const struct TrainerMonNoItemCustomMoves "+new_party_name+"[] = {"
            +body+"\n};\n")
        female=leader=="Sabrina"
        new_trainers.append(f"""    [{target_id}] =
    {{
        .trainerClass = TRAINER_CLASS_LEADER,
        .encounterMusic_gender = {"F_TRAINER_FEMALE | TRAINER_ENCOUNTER_MUSIC_FEMALE" if female else "TRAINER_ENCOUNTER_MUSIC_MALE"},
        .trainerPic = TRAINER_PIC_LEADER_{pic},
        .trainerName = _("{leader.upper()}"),
        .items = {item_match.group(1)},
        .doubleBattle = FALSE,
        .aiFlags = AI_SCRIPT_CHECK_BAD_MOVE | AI_SCRIPT_TRY_TO_FAINT | AI_SCRIPT_CHECK_VIABILITY,
        .party = NO_ITEM_CUSTOM_MOVES({new_party_name}),
    }},
""")
        new_constants.append(f"#define {target_id:<42} {864+i}\n")
        gym=f"Kanto_{city}_Gym"
        dest=emerald/"data/maps"/gym/"map.json"
        target_map=load_json(emerald,f"data/maps/{gym}/map.json")
        original=load_json(source,f"data/maps/{city}_Gym/map.json")
        leader_objects=[obj for obj in original["object_events"]
                        if obj.get("script","").endswith("_EventScript_"+leader)]
        if len(leader_objects)!=1 or target_map["object_events"]:
            raise RuntimeError(f"Invalid gym actor state: {leader}")
        event=leader_objects[0]
        label=gym+"_EventScript_Leader"+leader
        target_map["object_events"].append({
            "graphics_id":"OBJ_EVENT_GFX_"+pic,
            "x":event["x"],"y":event["y"],"elevation":event["elevation"],
            "movement_type":"MOVEMENT_TYPE_FACE_DOWN",
            "movement_range_x":0,"movement_range_y":0,
            "trainer_type":"TRAINER_TYPE_NONE",
            "trainer_sight_or_berry_tree_id":"0",
            "script":label,"flag":"0",
        })
        emit_json(dest,target_map)
        scripts=emerald/"data/maps"/gym/"scripts.inc"
        existing=scripts.read_text(encoding="utf-8")
        badge_flag="FLAG_KANTO_BADGE_"+badge
        tm_flag="FLAG_KANTO_TM_"+badge
        trainer_flag="FLAG_KANTO_V17_TRAINER_"+leader.upper()
        intro=gym+"_Text_"+leader+"_Intro"
        defeat=gym+"_Text_"+leader+"_Defeat"
        after=gym+"_Text_"+leader+"_After"
        won=gym+"_EventScript_"+leader+"Won"
        tm_event=gym+"_EventScript_"+leader+"TM"
        existing+=f"""
{label}::
    lock
    faceplayer
    goto_if_set {badge_flag}, {tm_event}
    trainerbattle_single {target_id}, {intro}, {defeat}, {won}, NO_MUSIC
    msgbox {after}, MSGBOX_DEFAULT
    release
    end

{won}::
    setflag {badge_flag}
    call Common_EventScript_PlayGymBadgeFanfare
    goto {tm_event}
    end

{tm_event}::
    goto_if_set {tm_flag}, {gym}_EventScript_{leader}AfterTM
    giveitem {tm}
    goto_if_eq VAR_RESULT, FALSE, Common_EventScript_ShowBagIsFull
    setflag {tm_flag}
{gym}_EventScript_{leader}AfterTM::
    msgbox {after}, MSGBOX_DEFAULT
    release
    end

{intro}:
    .string "Ready for a KANTO GYM battle?$"

{defeat}:
    .string "You have earned my respect.$"

{after}:
    .string "The {badge} BADGE is yours!$"
"""
        scripts.write_text(existing,encoding="utf-8")
        for symbol,value in ((trainer_flag,free[3*i]),
                             (badge_flag,free[3*i+1]),
                             (tm_flag,free[3*i+2])):
            flag_declarations.append(f"#define {symbol:<43} FLAG_UNUSED_0x{value:03X}\n")
        rows.append({
            "leader":leader,"city":city,"trainer_id":864+i,
            "trainer_symbol":target_id,"party":new_party_name,
            "trainer_flag":trainer_flag,"trainer_flag_value":free[3*i],
            "badge_flag":badge_flag,"badge_flag_value":free[3*i+1],
            "tm_flag":tm_flag,"tm_flag_value":free[3*i+2],
            "tm":tm,"coords":[event["x"],event["y"]],
            "temporary_portrait":True,
        })
    opponent_path.write_text(
        old_opponents.replace("#define TRAINERS_COUNT                      864",
                              "".join(new_constants)
                              +"#define TRAINERS_COUNT                      868"),encoding="utf-8")
    party_path.write_text(party_src.rstrip()+"\n\n"+"\n".join(new_parties),encoding="utf-8")
    idx=trainer_src.rfind("};")
    trainer_path.write_text(
        trainer_src[:idx]+"\n"+"\n".join(new_trainers)+trainer_src[idx:],
        encoding="utf-8")
    footer="#endif // GUARD_CONSTANTS_FLAGS_H"
    if footer not in flags:
        raise RuntimeError("Flag definitions unexpectedly changed")
    flag_path.write_text(
        flags.replace(footer,
            "// V0.17 extra trainer victories, badges and unique TM prizes.\n"
            +"".join(flag_declarations)+"\n"+footer),encoding="utf-8")
    return {"count":len(rows),"leaders":rows}


KANTO_V18_BUG_CATCHERS = (
    ("MtMoon_1F", "Robby"),
    ("MtMoon_1F", "Kent"),
    ("Route3", "James"),
    ("Route3", "Greg"),
    ("Route3", "Colton"),
)


def import_v18_route_moon_trainers(source: Path, emerald: Path,
                                   previously_used: list[dict]) -> dict:
    """Five original FireRed Bug Catchers with independent saved win flags.

    These trainer IDs are intentionally appended after Kanto V0.17's four
    leaders. Never reuse the previous allocations or raise MAX_TRAINERS_COUNT.
    """
    opp_path = emerald/"include/constants/opponents.h"
    part_path = emerald/"src/data/trainer_parties.h"
    trainer_path = emerald/"src/data/trainers.h"
    flag_path = emerald/"include/constants/flags.h"
    opp = opp_path.read_text(encoding="utf-8")
    if ("#define TRAINERS_COUNT                      868" not in opp
            or "#define MAX_TRAINERS_COUNT                  864" not in opp):
        raise RuntimeError("Extended trainer table or save limit changed unexpectedly")
    flags=flag_path.read_text(encoding="utf-8")
    occupied=[r["flag_value"] for r in previously_used]
    if len(occupied)!=len(set(occupied)) or len(occupied)<180:
        raise RuntimeError("Kanto V0.17 saved flags missing or duplicated")
    reserved=sorted({int(v,16) for v in re.findall(
        r"(?m)^#define FLAG_UNUSED_0x([0-9A-Fa-f]{3})\s+",flags
    ) if 0x264<=int(v,16)<0x500})
    free=[v for v in reserved if v not in set(occupied)]
    if len(free)<len(KANTO_V18_BUG_CATCHERS):
        raise RuntimeError("No remaining saved flags for extra Bug Catchers")
    original_parties=(source/"src/data/trainer_parties.h").read_text(encoding="utf-8")
    original_trainers=(source/"src/data/trainers.h").read_text(encoding="utf-8")
    trainers=trainer_path.read_text(encoding="utf-8")
    party_text=part_path.read_text(encoding="utf-8")
    valid_species=set(re.findall(
        r"\bSPECIES_[A-Z0-9_]+\b",
        (emerald/"include/constants/species.h").read_text(encoding="utf-8")))
    defs=[]
    parties=[]
    trainer_rows=[]
    extra_flags=[]
    report=[]
    for idx,(source_map,name) in enumerate(KANTO_V18_BUG_CATCHERS):
        source_name="TRAINER_BUG_CATCHER_"+name.upper()
        source_party="sParty_BugCatcher"+name
        source_record=re.search(
            r"\["+re.escape(source_name)+r"\]\s*=\s*\{([\s\S]*?)\n\s*\},",
            original_trainers)
        source_body=re.search(
            r"static const struct TrainerMonNoItemDefaultMoves\s+"
            + re.escape(source_party) + r"\[\]\s*=\s*\{([\s\S]*?)\n\};",
            original_parties)
        if not source_record or not source_body:
            raise RuntimeError(f"Missing original FireRed Bug Catcher {name}")
        body=source_body.group(1)
        if (not re.findall(r"\.lvl\s*=\s*\d+",body)
                or not re.findall(r"SPECIES_",body)
                or any(s not in valid_species for s in re.findall(
                    r"\bSPECIES_[A-Z0-9_]+\b",body))):
            raise RuntimeError(f"Unsupported original party for {name}")
        old_map=load_json(source,f"data/maps/{source_map}/map.json")
        src_event=f"{source_map}_EventScript_{name}"
        objects=[o for o in old_map["object_events"]
                 if o.get("script")==src_event
                 and o.get("trainer_type")=="TRAINER_TYPE_NORMAL"
                 and o.get("graphics_id")=="OBJ_EVENT_GFX_BUG_CATCHER"]
        if len(objects)!=1:
            raise RuntimeError(f"{source_map}: wrong source actor {name}")
        original=objects[0]
        path=f"data/maps/Kanto_{source_map}/map.json"
        target=load_json(emerald,path)
        if any(o["x"]==original["x"] and o["y"]==original["y"]
               for o in target["object_events"]):
            raise RuntimeError(f"{name}: actor overlaps existing object")
        new_macro="TRAINER_KANTO_V18_BUG_CATCHER_"+name.upper()
        new_party="sParty_KantoV18BugCatcher"+name
        label=f"Kanto_{source_map}_EventScript_BugCatcher{name}"
        target["object_events"].append({
            "graphics_id":"OBJ_EVENT_GFX_BUG_CATCHER",
            "x":original["x"],"y":original["y"],
            "elevation":original["elevation"],
            "movement_type":original["movement_type"],
            "movement_range_x":original["movement_range_x"],
            "movement_range_y":original["movement_range_y"],
            "trainer_type":"TRAINER_TYPE_NORMAL",
            "trainer_sight_or_berry_tree_id":original["trainer_sight_or_berry_tree_id"],
            "script":label,"flag":"0",
        })
        emit_json(emerald/path,target)
        script_file=emerald/"data/maps"/("Kanto_"+source_map)/"scripts.inc"
        existing=script_file.read_text(encoding="utf-8")
        intro=f"Kanto_{source_map}_Text_{name}Intro"
        defeat=f"Kanto_{source_map}_Text_{name}Defeat"
        after=f"Kanto_{source_map}_Text_{name}After"
        existing+=f"""
{label}::
    trainerbattle_single {new_macro}, {intro}, {defeat}
    msgbox {after}, MSGBOX_AUTOCLOSE
    end

{intro}:
    .string "Check out my BUG POKeMON!$"

{defeat}:
    .string "What a strong team!$"

{after}:
    .string "I will study BUG POKeMON more.$"
"""
        script_file.write_text(existing,encoding="utf-8")
        new_flag=f"FLAG_KANTO_V18_TRAINER_{name.upper()}"
        extra_flags.append(f"#define {new_flag:<44} FLAG_UNUSED_0x{free[idx]:03X}\n")
        defs.append(f"#define {new_macro:<44} {868+idx}\n")
        parties.append(
            f"static const struct TrainerMonNoItemDefaultMoves {new_party}[] = {{"
            +body+"\n};\n")
        trainer_rows.append(f"""    [{new_macro}] =
    {{
        .trainerClass = TRAINER_CLASS_BUG_CATCHER,
        .encounterMusic_gender = TRAINER_ENCOUNTER_MUSIC_MALE,
        .trainerPic = TRAINER_PIC_BUG_CATCHER,
        .trainerName = _("{name.upper()}"),
        .items = {{}},
        .doubleBattle = FALSE,
        .aiFlags = AI_SCRIPT_CHECK_BAD_MOVE,
        .party = NO_ITEM_DEFAULT_MOVES({new_party}),
    }},
""")
        report.append({
            "map":"Kanto_"+source_map,"name":name,"trainer_id":868+idx,
            "symbol":new_macro,"flag":new_flag,"flag_value":free[idx],
            "source_trainer":source_name,"party":new_party,
            "position":[original["x"],original["y"]],"event":label
        })
    opp_path.write_text(
        opp.replace("#define TRAINERS_COUNT                      868",
                    "".join(defs)+"#define TRAINERS_COUNT                      873"),
        encoding="utf-8")
    part_path.write_text(party_text.rstrip()+"\n\n"+"\n".join(parties),encoding="utf-8")
    if not trainers.rstrip().endswith("};"):
        raise RuntimeError("Unexpected trainers.h end")
    i=trainers.rfind("};")
    trainer_path.write_text(
        trainers[:i]+"\n"+"\n".join(trainer_rows)+trainers[i:],encoding="utf-8")
    footer="#endif // GUARD_CONSTANTS_FLAGS_H"
    if footer not in flags:
        raise RuntimeError("Unknown flags.h format")
    flag_path.write_text(
        flags.replace(footer,"// V0.18 Kanto Bug Catcher defeated flags.\n"
                      +"".join(extra_flags)+"\n"+footer),encoding="utf-8")
    return {"count":len(report),"trainers":report}


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
    # A faithful center and mart require FireRed's 640/7 indoor Building tileset.
    create_tileset(source, emerald, "gTileset_Building", "primary",
                   dest_behavior, source_behavior, unknown)
    for label in ("gTileset_PokemonCenter", "gTileset_Mart"):
        create_tileset(source, emerald, label, "secondary",
                       dest_behavior, source_behavior, unknown)
    create_tileset(source, emerald, "gTileset_GenericBuilding2", "secondary",
                   dest_behavior, source_behavior, unknown)
    # The first complete traversal-friendly dungeons use three source
    # secondary graphics sets. Reuse an existing converted set if shared.
    dungeon_secondaries = {
        layouts[load_json(source, f"data/maps/{n}/map.json")["layout"]]["secondary_tileset"]
        for n in KANTO_V06_DUNGEONS + KANTO_V07_DUNGEONS + KANTO_V12_DUNGEONS + KANTO_V14_GYMS + KANTO_V15_LEAGUE
    }
    already_converted = set(secondaries) | {
        "gTileset_PokemonCenter", "gTileset_Mart", "gTileset_GenericBuilding2"
    }
    extra_dungeon_secondaries = dungeon_secondaries - already_converted
    for label in sorted(extra_dungeon_secondaries):
        create_tileset(source, emerald, label, "secondary",
                       dest_behavior, source_behavior, unknown)
    report = {"source_commit": PINNED_FIRE_RED_SHA,
              "state": MILESTONE,
              "geometry_maps_created": len(names),
              "graphics_tilesets_created": 5 + len(secondaries) + len(extra_dungeon_secondaries),
              "saffron_gatehouses_ported": 4,
              "original_interiors_ported": 2,
              "original_npcs_ported": 0,
              "interior_warps_ported": 2,
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
        if n == "VermilionCity":
            # The source index is the stable warp position in FireRed.
            # Only original Pokemon Center (#4) and Mart (#7) are unlocked.
            for source_warp_index, target_id in (
                (4, "MAP_KANTO_VERMILIONCITY_POKEMONCENTER_1F"),
                (7, "MAP_KANTO_VERMILIONCITY_MART"),
            ):
                src_warp = m["warp_events"][source_warp_index]
                target_map["warp_events"].append({
                    "x": src_warp["x"], "y": src_warp["y"],
                    "elevation": src_warp["elevation"],
                    "dest_map": target_id, "dest_warp_id": "1",
                })
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
    .string "Return to your HOENN heal location?$"

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
    interiors = add_vermilion_interiors(
        source, emerald, layouts, target_layouts, target_groups,
        source_maps["VermilionCity"])
    new_services = add_regional_service_interiors(
        source, emerald, source_maps, target_groups)
    interiors.extend(new_services)
    saffron_gates = add_saffron_gatehouses(
        source, emerald, source_maps, layouts, target_layouts, target_groups)
    report["saffron_gatehouses"] = saffron_gates
    dungeon_batch = add_kanto_v06_dungeons(
        source, emerald, source_maps, layouts, target_layouts)
    extra_batch = add_kanto_v06_dungeons(
        source, emerald, source_maps, layouts, target_layouts,
        selected=KANTO_V07_DUNGEONS)
    # Source-native self-contained groups: four dungeon complexes and every
    # floor in each; no new route map IDs or Hoenn references.
    major_batch = add_kanto_v06_dungeons(
        source, emerald, source_maps, layouts, target_layouts,
        selected=KANTO_V12_DUNGEONS)
    gym_batch = add_kanto_v06_dungeons(
        source, emerald, source_maps, layouts, target_layouts,
        selected=KANTO_V14_GYMS)
    league_batch = add_kanto_v06_dungeons(
        source, emerald, source_maps, layouts, target_layouts,
        selected=KANTO_V15_LEAGUE,
        omitted_warp_destinations=("MAP_INDIGO_PLATEAU_POKEMON_CENTER_2F",))
    report["v15_league_maps"] = league_batch["names"]
    report["v15_league_warps"] = league_batch["internal_warps"]
    report["v15_league_exterior_warps"] = league_batch["exterior_warps"]
    # Use Emerald's nurse and keep the independent Kanto heal location, with
    # original Indigo Plateau nurse position (13,10).
    indigo="Kanto_IndigoPlateau_PokemonCenter_1F"
    center_path=emerald/"data/maps"/indigo/"map.json"
    center=load_json(emerald,f"data/maps/{indigo}/map.json")
    nurse=make_qa_npc("OBJ_EVENT_GFX_NURSE",
                       "Kanto_Indigo_EventScript_Nurse",(13,10,3))
    nurse["local_id"]="LOCALID_KANTO_INDIGO_NURSE"
    center["object_events"].append(nurse)
    emit_json(center_path,center)
    (emerald/"data/maps"/indigo/"scripts.inc").write_text(
        """Kanto_IndigoPlateau_PokemonCenter_1F_MapScripts::
    map_script MAP_SCRIPT_ON_TRANSITION, Kanto_Indigo_EventScript_RegisterHeal
    .byte 0

Kanto_Indigo_EventScript_RegisterHeal:
    setvar VAR_KANTO_LAST_HEAL_LOCATION, KANTO_HEAL_INDIGO_PLATEAU
    end

Kanto_Indigo_EventScript_Nurse::
    setvar VAR_0x800B, LOCALID_KANTO_INDIGO_NURSE
    call Common_EventScript_PkmnCenterNurse
    waitmessage
    waitbuttonpress
    release
    end
""",encoding="utf-8"
    )
    report["v15_indigo_center_nurse"]=True
    report["v14_gym_maps"] = gym_batch["names"]
    report["v14_gym_warps"] = gym_batch["internal_warps"]
    report["v14_gym_exterior_warps"] = gym_batch["exterior_warps"]
    report["v12_major_dungeon_maps"] = major_batch["names"]
    report["v12_major_dungeon_warps"] = major_batch["internal_warps"]
    report["v12_major_dungeon_exterior_warps"] = major_batch["exterior_warps"]
    report["dungeon_maps"] = dungeon_batch["names"]
    report["dungeon_warps"] = dungeon_batch["internal_warps"]
    report["dungeon_exterior_warps"] = dungeon_batch["exterior_warps"]
    report["v07_underground_and_tower_maps"] = extra_batch["names"]
    report["v07_warps"] = extra_batch["internal_warps"]
    report["v07_exterior_warps"] = extra_batch["exterior_warps"]
    report["wild_encounter_maps_ported"] = add_firered_encounters(
        source, emerald, {**source_to_name,
                          **dungeon_batch["source_ids"], **extra_batch["source_ids"],
                          **major_batch["source_ids"]})
    report["wild_encounters_ported"] = report["wild_encounter_maps_ported"] > 0
    report["interior_maps"] = interiors
    report["original_interiors_ported"] = len(interiors)
    report["interior_warps_ported"] = len(interiors)
    target_groups["gMapGroup_Kanto"].extend("Kanto_" + n for n in names)
    target_groups["gMapGroup_Kanto"].extend(new_services)
    target_groups["gMapGroup_Kanto"].extend(saffron_gates)
    # Append, never insert: saves from V0.2–V0.5 retain every old map ID.
    target_groups["gMapGroup_Kanto"].extend(dungeon_batch["names"])
    target_groups["gMapGroup_Kanto"].extend(extra_batch["names"])
    target_groups["gMapGroup_Kanto"].extend(major_batch["names"])
    target_groups["gMapGroup_Kanto"].extend(gym_batch["names"])
    # Map group numbers are carried as signed 8-bit warp mapNums in C.
    # Beyond 128 entries we must add another map group, never renumber
    # these 107 existing map numbers within the current saved Kanto group.
    capacity = 128
    count_kanto = len(target_groups["gMapGroup_Kanto"])
    if count_kanto > capacity:
        raise RuntimeError(
            f"Kanto group has {count_kanto} maps (max {capacity}); "
            "split new maps into an appended Kanto group before importing")
    report["kanto_map_slots_remaining"] = capacity - count_kanto
    # Keep this original map group immutable for existing save files.
    # Append a NEW Kanto map group rather than risk signed 8-bit mapNums.
    league_group="gMapGroup_Kanto_League"
    if league_group in target_groups["group_order"] or league_group in target_groups:
        raise RuntimeError("League map group is already registered")
    if target_groups["group_order"][-1] != "gMapGroup_Kanto":
        raise RuntimeError("Kanto must remain last before the league group is added")
    target_groups["group_order"].append(league_group)
    target_groups[league_group]=league_batch["names"]
    report["v15_second_group_entries"]=len(league_batch["names"])
    # All 160 persistent pickup flags from V0.13 remain unchanged.
    # Gym layouts are not yet populated with trainer NPCs/leader badges.
    # Preserve the already-shipped 42 visible + 77 hidden item flags.
    # V0.12 must NOT mix newly ported maps into prior pickup allocation.
    # Future item additions need a new stable allocation lane AFTER all 119.
    # Use immutable source map order, before adding any new geography.
    item_maps = list(names) + list(KANTO_V06_DUNGEONS) + list(KANTO_V07_DUNGEONS)
    item_report = import_kanto_visible_items(source, emerald, item_maps)
    report["original_item_balls"] = item_report["total"]
    report["visible_item_flags"] = item_report["items"]
    hidden_report = import_kanto_hidden_items(
        source, emerald, item_maps, item_report["items"])
    report["original_hidden_items"] = hidden_report["total"]
    report["hidden_item_flags"] = hidden_report["items"]
    major_items = import_v13_major_dungeon_items(
        source, emerald, KANTO_V12_DUNGEONS,
        item_report["items"], hidden_report["items"])
    report["v13_visible_items"] = major_items["visible_count"]
    report["v13_hidden_items"] = major_items["hidden_count"]
    report["v13_new_item_flags"] = major_items["items"]
    trainer_report = import_viridian_forest_trainers(source, emerald)
    gym_leaders = import_first_kanto_gym_leaders(
        source, emerald,
        item_report["items"] + hidden_report["items"] + major_items["items"])
    report["v16_gym_leaders"] = gym_leaders["leaders"]
    report["v16_gym_leader_battles"] = gym_leaders["count"]
    later_gym_leaders = import_remaining_kanto_gym_leaders(
        source, emerald,
        item_report["items"] + hidden_report["items"] + major_items["items"]
        + [
            {"flag_value":value}
            for leader in gym_leaders["leaders"]
            for value in (leader["badge_flag_value"], leader["tm_flag_value"])
        ])
    report["v17_remaining_gym_leaders"] = later_gym_leaders["leaders"]
    report["v17_gym_leader_battles"] = later_gym_leaders["count"]
    v18 = import_v18_route_moon_trainers(
        source, emerald,
        item_report["items"] + hidden_report["items"] + major_items["items"]
        + [
            {"flag_value":value}
            for row in gym_leaders["leaders"]
            for value in (row["badge_flag_value"],row["tm_flag_value"])
        ] + [
            {"flag_value":value}
            for row in later_gym_leaders["leaders"]
            for value in (row["trainer_flag_value"],row["badge_flag_value"],row["tm_flag_value"])
        ])
    report["v18_route_and_moon_trainers"] = v18["trainers"]
    report["v18_trainer_battles"] = v18["count"]
    report["viridian_forest_trainers"] = trainer_report["trainers"]
    report["original_npcs_ported"] = trainer_report["count"] + gym_leaders["count"] + later_gym_leaders["count"] + v18["count"]
    report["trainer_battles_ported"] = trainer_report["count"] + gym_leaders["count"] + later_gym_leaders["count"] + v18["count"]
    target_groups["connections_include_order"].extend("Kanto_" + n for n in names)
    emit_json(emerald / "data/maps/map_groups.json", target_groups)
    emit_json(emerald / "data/layouts/layouts.json", target_layouts)
    inc = emerald / "data/event_scripts.s"
    code = inc.read_text(encoding="utf-8")
    anchor = '\t.include "data/maps/Kanto_Harbor/scripts.inc"'
    if anchor not in code:
        raise RuntimeError("Expected original Kanto Harbor script include not found")
    includes = "".join(f'\n\t.include "data/maps/Kanto_{n}/scripts.inc"' for n in names)
    includes += "".join(f'\n\t.include "data/maps/{n}/scripts.inc"' for n in interiors)
    includes += "".join(f'\n\t.include "data/maps/{n}/scripts.inc"' for n in saffron_gates)
    includes += "".join(f'\n\t.include "data/maps/{n}/scripts.inc"'
                        for n in dungeon_batch["names"])
    includes += "".join(f'\n\t.include "data/maps/{n}/scripts.inc"'
                        for n in extra_batch["names"])
    includes += "".join(f'\n\t.include "data/maps/{n}/scripts.inc"'
                        for n in major_batch["names"])
    includes += "".join(f'\n\t.include "data/maps/{n}/scripts.inc"'
                        for n in gym_batch["names"])
    includes += "".join(f'\n\t.include "data/maps/{n}/scripts.inc"'
                        for n in league_batch["names"])
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
    print("CAUTION: 17 original Kanto Center/Mart interiors have service scripts; actual gameplay QA pending.")
    print("More original interiors, gyms, most trainer scripts, and story events remain pending.")
    print("Kanto regional whiteout now has an isolated saved Center index; gameplay QA pending.")
    print("Original Viridian Forest, Mt. Moon and Diglett Cave layouts, wild encounters and doors added.")
    print("Added original Underground Path, Rock Tunnel and Pokemon Tower layouts with exits.")
    print("Added Victory Road, Pokemon Mansion, Cerulean Cave and Seafoam Islands (15 original floors).")
    print("Added eight authentic Kanto Gym interiors and exterior door connections; trainer/badge scripts pending.")
    print("Added Indigo Plateau Center 1F and six Pokemon League rooms in a SECOND save-stable map group.")
    print(f"Ported {result['original_item_balls']} original visible item balls with save-backed flags.")
    print(f"Ported {result['original_hidden_items']} original hidden FireRed items with distinct save flags.")
    print(f"Ported {result['v13_visible_items']} extra visible and {result['v13_hidden_items']} hidden major-dungeon items with new flags.")
    print(f"Ported {result['trainer_battles_ported']} original Viridian Forest trainers.")
    print(f"Ported {result['v17_gym_leader_battles']} additional gym leaders with mapped persistent trainer flags.")
    print(f"Ported {result['v18_trainer_battles']} original trainers on Route 3 and Mt. Moon.")
    print(f"Ported {result['v16_gym_leader_battles']} original FireRed gym leader parties, badges and TMs.")
    print("Dungeon NPCs/items/scripts, special collision behaviors and full gameplay QA still pending.")
    print("Verify collision, palettes, map edges, ferry and save by real gameplay.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
