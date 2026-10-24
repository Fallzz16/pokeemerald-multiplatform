#!/usr/bin/env python3
"""M8 opt-in sprite-budget optimization for the pinned World checkout.

Does not change ROM/save layouts, gameplay encounters or PKMN-World upstream.
Always validate both source anchors before any files are written.
"""
import argparse
import json
from pathlib import Path

SHADOW_OLD = "#define OW_OBJECT_VANILLA_SHADOWS      FALSE"
SHADOW_NEW = "#define OW_OBJECT_VANILLA_SHADOWS      TRUE"
GUARD_OLD = """     || FlagGet(WE_FLAG_NO_ENCOUNTER)
     || FlagGet(DN_FLAG_SEARCHING)
     || (gMapHeader.mapLayoutId == LAYOUT_BATTLE_FRONTIER_BATTLE_PIKE_ROOM_WILD_MONS && !WE_OWE_BATTLE_PIKE)"""
GUARD_NEW = """     || FlagGet(WE_FLAG_NO_ENCOUNTER)
     || (gMapHeader.mapLayoutId == LAYOUT_BATTLE_FRONTIER_BATTLE_PIKE_ROOM_WILD_MONS && !WE_OWE_BATTLE_PIKE)"""
PRIOR_GUARD = "if (ArePlayerFieldControlsLocked() || FlagGet(DN_FLAG_SEARCHING) || !CheckCurrentWildMonHeaderForOWE(shouldSpawnWaterMons))"


def replace_once(source, before, after, label):
    count = source.count(before)
    if count != 1:
        raise ValueError(f"{label}: expected one exact anchor, found {count}")
    return source.replace(before, after, 1)


def prepare(root):
    config = root / "include/config/overworld.h"
    encounters = root / "src/wild_encounter_ow.c"
    old_config = config.read_text(encoding="utf-8")
    old_encounters = encounters.read_text(encoding="utf-8")
    if old_encounters.count(PRIOR_GUARD) != 1:
        raise ValueError("the prior DexNav flag guard was changed: refusing optimization")
    if "#define OW_GFX_COMPRESS                FALSE" not in old_config:
        raise ValueError("expected dynamic sprite VRAM policy is missing")
    if "#define WE_OW_ENCOUNTERS                        TRUE" not in (
        root / "include/config/wild_encounter.h").read_text(encoding="utf-8"):
        raise ValueError("overworld encounters no longer enabled: refusing optimization")
    new_config = replace_once(old_config, SHADOW_OLD, SHADOW_NEW, "shadow budget")
    new_encounters = replace_once(old_encounters, GUARD_OLD, GUARD_NEW, "duplicate DexNav check")
    return [(config, old_config, new_config), (encounters, old_encounters, new_encounters)]


def apply(root, write=False):
    edits = prepare(root)
    changed = []
    if write:
        try:
            for path, old, new in edits:
                path.write_text(new, encoding="utf-8")
                changed.append((path, old))
        except OSError:
            for path, old in reversed(changed):
                path.write_text(old, encoding="utf-8")
            raise
    return {
        "mode": "applied" if write else "preflight",
        "changes": [str(path.relative_to(root)) for path, _, _ in edits],
        "object_shadow_policy": "vanilla (jump-only)",
        "preserved": ["Pokémon followers", "overworld wild encounters",
                      "per-map tables", "day/night", "save blocks", "graphics decompression policy"],
        "resource_claim": "up to one sprite shadow per ordinary overworld object saved",
        "measured_fps_gain": None,
        "measured_ram_change": None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--apply", action="store_true", help="Apply changes to isolated World checkout")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = apply(args.world, args.apply)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
