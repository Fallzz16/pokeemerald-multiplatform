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
    .byte 0

@ Do not overwrite Hoenn's last healing position before a dedicated
@ per-region save location exists. Returning from Kanto must remain safe.
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

    .align 2
Kanto_VermilionMart_Items:
    .short ITEM_POKE_BALL
    .short ITEM_GREAT_BALL
    .short ITEM_POTION
    .short ITEM_SUPER_POTION
    .short ITEM_ANTIDOTE
    .short ITEM_PARALYZE_HEAL
    .short ITEM_ESCAPE_ROPE
    .short ITEM_REPEL
    pokemartlistend
"""
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
                scripts = f"""{target_name}_MapScripts::
    .byte 0

@ Hoenn heal warp is intentionally preserved until regional save migration.
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
    pokemart Kanto_GenericMart_Items
    msgbox gText_PleaseComeAgain, MSGBOX_DEFAULT
    release
    end
"""
            out = emerald / "data/maps" / target_name
            emit_json(out / "map.json", map_obj)
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

    # Shared shop inventory for the early functional milestone. Original
    # city-specific FireRed item lists are a separately QA-tracked feature.
    shop_common = """
    .align 2
Kanto_GenericMart_Items:
    .short ITEM_POKE_BALL
    .short ITEM_GREAT_BALL
    .short ITEM_POTION
    .short ITEM_SUPER_POTION
    .short ITEM_ANTIDOTE
    .short ITEM_PARALYZE_HEAL
    .short ITEM_ESCAPE_ROPE
    .short ITEM_REPEL
    pokemartlistend
"""
    # Attach shared inventory to a Mart, not to a Pokemon Center.
    first_mart = next(n for n in created if n.endswith("_Mart"))
    with (emerald / "data/maps" / first_mart / "scripts.inc").open("a", encoding="utf-8") as file:
        file.write(shop_common)
    # Delay registration to preserve V0.2 map indices during version upgrades.
    return created


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
    report = {"source_commit": PINNED_FIRE_RED_SHA,
              "state": MILESTONE,
              "geometry_maps_created": len(names),
              "graphics_tilesets_created": 4 + len(secondaries),
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
    report["wild_encounter_maps_ported"] = add_firered_encounters(
        source, emerald, source_to_name)
    report["wild_encounters_ported"] = report["wild_encounter_maps_ported"] > 0
    interiors = add_vermilion_interiors(
        source, emerald, layouts, target_layouts, target_groups,
        source_maps["VermilionCity"])
    new_services = add_regional_service_interiors(
        source, emerald, source_maps, target_groups)
    interiors.extend(new_services)
    report["interior_maps"] = interiors
    report["original_interiors_ported"] = len(interiors)
    report["interior_warps_ported"] = len(interiors)
    target_groups["gMapGroup_Kanto"].extend("Kanto_" + n for n in names)
    target_groups["gMapGroup_Kanto"].extend(new_services)
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
    print("Other interiors, gym/trainer scripts and local healing respawn remain pending.")
    print("Verify collision, palettes, map edges, ferry and save by real gameplay.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
