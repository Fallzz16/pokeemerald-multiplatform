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
SHADOW_MODES = ("auto", "lean", "full")
GUARD_OLD = """     || FlagGet(WE_FLAG_NO_ENCOUNTER)
     || FlagGet(DN_FLAG_SEARCHING)
     || (gMapHeader.mapLayoutId == LAYOUT_BATTLE_FRONTIER_BATTLE_PIKE_ROOM_WILD_MONS && !WE_OWE_BATTLE_PIKE)"""
GUARD_NEW = """     || FlagGet(WE_FLAG_NO_ENCOUNTER)
     || (gMapHeader.mapLayoutId == LAYOUT_BATTLE_FRONTIER_BATTLE_PIKE_ROOM_WILD_MONS && !WE_OWE_BATTLE_PIKE)"""
PRIOR_GUARD = "if (ArePlayerFieldControlsLocked() || FlagGet(DN_FLAG_SEARCHING) || !CheckCurrentWildMonHeaderForOWE(shouldSpawnWaterMons))"
EARLY_OLD = ("    bool32 shouldSpawnWaterMons = ShouldSpawnWaterOWE();\n"
             "    \n"
             "    " + PRIOR_GUARD + "\n")
EARLY_NEW = ("    bool32 shouldSpawnWaterMons;\n"
             "    if (ArePlayerFieldControlsLocked() || FlagGet(DN_FLAG_SEARCHING))\n"
             "        return;\n"
             "    shouldSpawnWaterMons = ShouldSpawnWaterOWE();\n"
             "    if (!CheckCurrentWildMonHeaderForOWE(shouldSpawnWaterMons))\n"
             "        return;\n")


def replace_once(source, before, after, label):
    count = source.count(before)
    if count != 1:
        raise ValueError(f"{label}: expected one exact anchor, found {count}")
    return source.replace(before, after, 1)


def select_shadow_policy(requested, config, encounter_cfg):
    """Configuration is a build-time profile, not a save or in-game setting.

    Auto sacrifices extra universal shadows if both visible encounters and
    followers are enabled. An explicit 'full' mode restores aesthetics, but
    the OAM trade-off must pass the same runtime QA as 'lean'.
    """
    if requested not in SHADOW_MODES:
        raise ValueError(f"unsupported shadow mode: {requested}")
    if requested != "auto":
        return requested
    return ("lean" if ("#define WE_OW_ENCOUNTERS                        TRUE" in encounter_cfg
                       and "#define OW_FOLLOWERS_ENABLED           TRUE" in config)
            else "full")


def prepare(root, shadows="auto"):
    config = root / "include/config/overworld.h"
    encounters = root / "src/wild_encounter_ow.c"
    old_config = config.read_text(encoding="utf-8")
    old_encounters = encounters.read_text(encoding="utf-8")
    if old_encounters.count(PRIOR_GUARD) != 1 or old_encounters.count(EARLY_OLD) != 1:
        raise ValueError("the prior DexNav/early OWE guard was changed: refusing optimization")
    if "#define OW_GFX_COMPRESS                FALSE" not in old_config:
        raise ValueError("expected dynamic sprite VRAM policy is missing")
    encounter_cfg = (root / "include/config/wild_encounter.h").read_text(encoding="utf-8")
    if "#define WE_OW_ENCOUNTERS                        TRUE" not in encounter_cfg:
        raise ValueError("overworld encounters no longer enabled: refusing optimization")
    selected = select_shadow_policy(shadows, old_config, encounter_cfg)
    if old_config.count(SHADOW_OLD) != 1:
        raise ValueError("shadow budget: expected one original FALSE anchor")
    new_config = (replace_once(old_config, SHADOW_OLD, SHADOW_NEW, "shadow budget")
                  if selected == "lean" else old_config)
    new_encounters = replace_once(old_encounters, GUARD_OLD, GUARD_NEW, "duplicate DexNav check")
    new_encounters = replace_once(new_encounters, EARLY_OLD, EARLY_NEW, "early OWE guard")
    return [(config, old_config, new_config), (encounters, old_encounters, new_encounters)]


def apply(root, write=False, shadows="auto"):
    edits = prepare(root, shadows)
    config_text = (root / "include/config/overworld.h").read_text(encoding="utf-8")
    encounter_cfg = (root / "include/config/wild_encounter.h").read_text(encoding="utf-8")
    selected = select_shadow_policy(shadows, config_text, encounter_cfg)
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
        "changes": [str(path.relative_to(root)) for path, old, new in edits if old != new],
        "object_shadow_policy": ("vanilla (jump-only)" if selected == "lean" else "universal"),
        "requested_shadow_mode": shadows,
        "resolved_shadow_mode": selected,
        "early_spawn_guard": "short-circuit locked and DexNav frames before water flag read",
        "shadow_setting_kind": "build-time; not an in-game runtime toggle",
        "preserved": ["Pokémon followers", "overworld wild encounters",
                      "per-map tables", "day/night", "save blocks", "graphics decompression policy"],
        "resource_claim": ("up to one sprite shadow per ordinary overworld object saved"
                            if selected == "lean" else "full shadows; extra sprite per object"),
        "measured_fps_gain": None,
        "measured_ram_change": None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--apply", action="store_true", help="Apply changes to isolated World checkout")
    parser.add_argument("--shadows", choices=SHADOW_MODES, default="auto",
                        help="Compile-time OAM profile: auto chooses lean with followers + OWE")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = apply(args.world, args.apply, args.shadows)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
