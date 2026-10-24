#!/usr/bin/env python3
"""Post-M8 grass-only random encounters for an isolated pinned PKMN-World checkout.

Keeps the existing world/maps, manual story encounters, and save data intact.
Runs AFTER optimize_overworld_budget.py (which audits the original OWE config).
All edits are anchored and validated before anything is written.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

CONFIG_OLD = "#define WE_OW_ENCOUNTERS                        TRUE"
CONFIG_NEW = "#define WE_OW_ENCOUNTERS                        FALSE"
VANILLA = ("#define WE_VANILLA_RANDOM           TRUE    // If TRUE, Pokémon can randomly spawn "
           "on tiles that can trigger wild encounters, as in vanilla.")
GRASS_SETTING = "#define GW_GRASS_ONLY_WILD          TRUE    // Grand World: nonscripted wild encounters only in grass."

ANCHORS = {
    "step": (
        "    if (sWildEncountersDisabled == TRUE)\n        return FALSE;\n",
        "    if (sWildEncountersDisabled == TRUE)\n        return FALSE;\n"
        "\n    // Grand World: only natural grass tiles may trigger random wild battles.\n"
        "    if (GW_GRASS_ONLY_WILD && !MetatileBehavior_IsPokeGrass(curMetatileBehavior)\n"
        "        && !MetatileBehavior_IsAshGrass(curMetatileBehavior))\n"
        "        return FALSE;\n"
    ),
    "rock_smash": (
        "void RockSmashWildEncounter(void)\n{\n"
        "    u32 headerId = GetCurrentMapWildMonHeaderId();\n"
        "    enum TimeOfDay timeOfDay;\n",
        "void RockSmashWildEncounter(void)\n{\n"
        "    u32 headerId = GetCurrentMapWildMonHeaderId();\n"
        "    enum TimeOfDay timeOfDay;\n"
        "\n    // Breaking a rock must not generate a wild Pokemon outside grass.\n"
        "    if (GW_GRASS_ONLY_WILD)\n"
        "    {\n"
        "        gSpecialVar_Result = FALSE;\n"
        "        return;\n"
        "    }\n"
    ),
    "sweet_scent": (
        "    PlayerGetDestCoords(&x, &y);\n"
        "    headerId = GetCurrentMapWildMonHeaderId();\n",
        "    PlayerGetDestCoords(&x, &y);\n"
        "    if (GW_GRASS_ONLY_WILD\n"
        "        && !MetatileBehavior_IsPokeGrass(MapGridGetMetatileBehaviorAt(x, y))\n"
        "        && !MetatileBehavior_IsAshGrass(MapGridGetMetatileBehaviorAt(x, y)))\n"
        "        return FALSE;\n"
        "    headerId = GetCurrentMapWildMonHeaderId();\n"
    ),
    "fishing_availability": (
        "bool8 DoesCurrentMapHaveFishingMons(void)\n{\n"
        "    u32 headerId = GetCurrentMapWildMonHeaderId();\n"
        "    enum TimeOfDay timeOfDay;\n",
        "bool8 DoesCurrentMapHaveFishingMons(void)\n{\n"
        "    u32 headerId = GetCurrentMapWildMonHeaderId();\n"
        "    enum TimeOfDay timeOfDay;\n"
        "\n    // Rods must never start a wild battle in the grass-only ruleset.\n"
        "    if (GW_GRASS_ONLY_WILD)\n"
        "        return FALSE;\n"
    ),
    "fishing_fallback": (
        "void FishingWildEncounter(u8 rod)\n{\n"
        "    enum Species species;\n"
        "    u32 headerId;\n"
        "    s16 x, y;\n"
        "    enum TimeOfDay timeOfDay;\n",
        "void FishingWildEncounter(u8 rod)\n{\n"
        "    enum Species species;\n"
        "    u32 headerId;\n"
        "    s16 x, y;\n"
        "    enum TimeOfDay timeOfDay;\n"
        "\n    // Defensive guard if another script invokes this hook directly.\n"
        "    if (GW_GRASS_ONLY_WILD)\n"
        "        return;\n"
    ),
    "debug": (
        "bool8 StandardWildEncounter_Debug(void)\n{\n"
        "    u32 headerId = GetCurrentMapWildMonHeaderId();\n"
        "    enum TimeOfDay timeOfDay;\n",
        "bool8 StandardWildEncounter_Debug(void)\n{\n"
        "    u32 headerId = GetCurrentMapWildMonHeaderId();\n"
        "    enum TimeOfDay timeOfDay;\n"
        "\n    if (GW_GRASS_ONLY_WILD)\n"
        "        return FALSE;\n"
    ),
}


def replace_exact(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one exact original anchor, found {count}")
    return source.replace(old, new, 1)


def prepare(world):
    config_path = world / "include/config/wild_encounter.h"
    source_path = world / "src/wild_encounter.c"
    if not (config_path.is_file() and source_path.is_file() and (world / "Makefile").is_file()):
        raise ValueError("expected complete pinned World checkout")
    config = config_path.read_text(encoding="utf-8")
    source = source_path.read_text(encoding="utf-8")
    if "GW_GRASS_ONLY_WILD" in config or "GW_GRASS_ONLY_WILD" in source:
        raise ValueError("grass-only patch already applied or conflicting")

    config_new = replace_exact(config, CONFIG_OLD, CONFIG_NEW, "generated overworld spawns")
    config_new = replace_exact(config_new, VANILLA, VANILLA + "\n" + GRASS_SETTING, "vanilla encounter toggle")
    if "#define WE_VANILLA_RANDOM           TRUE" not in config_new:
        raise ValueError("random step encounter configuration unexpectedly changed")
    source_new = source
    for name, (old, new) in ANCHORS.items():
        source_new = replace_exact(source_new, old, new, name)

    return {config_path: (config, config_new), source_path: (source, source_new)}


def apply(world, write=False):
    changes = prepare(world)
    if not write:
        return {"mode": "preflight", "files": [str(p.relative_to(world)) for p in changes],
                "scripted_encounters_unchanged": True, "save_layout_unchanged": True}

    backups = {p: p.with_name(p.name + ".gw-grass-original") for p in changes}
    if any(p.exists() for p in backups.values()):
        raise ValueError("backup collision: grass-only patch already attempted")
    staged = {}
    committed = []
    try:
        for p, (_, new) in changes.items():
            fd, tmp = tempfile.mkstemp(prefix=p.name + ".gw-grass-stage-", dir=p.parent)
            staged[p] = Path(tmp)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as out:
                out.write(new)
        for p, backup in backups.items():
            shutil.copy2(p, backup)
        for p, tmp in staged.items():
            os.replace(tmp, p)
            committed.append(p)
    except Exception:
        for p in committed:
            shutil.copy2(backups[p], p)
        raise
    finally:
        for tmp in staged.values():
            if tmp.exists():
                tmp.unlink()
    return {"mode": "applied", "files": [str(p.relative_to(world)) for p in changes],
            "generated_overworld_encounters": False, "random_steps": "grass and ash grass only",
            "fishing_rock_smash": "no wild encounters", "sweet_scent": "grass and ash grass only",
            "scripted_encounters_unchanged": True, "save_layout_unchanged": True,
            "runtime_gameplay_verified": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = apply(args.world.resolve(), args.apply)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
