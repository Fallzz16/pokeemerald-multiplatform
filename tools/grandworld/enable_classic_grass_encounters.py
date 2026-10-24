#!/usr/bin/env python3
"""M8 opt-in classic GRASS-ONLY land encounters for an isolated World checkout.

Generated visible overworld encounters are disabled. Standard grass steps remain
random as in Emerald. Fishing, surfing, Rock Smash, static/scripted encounters and
the Battle Pike/Pyramid remain unchanged. The active per-frame OWE manager gets
a constant-time disabled branch while still cleaning up previously spawned OWEs.

Run AFTER optimize_overworld_budget.py. Fail closed on source drift and never
change SaveBlocks, species, levels, encounter rates, flags or map layouts.
"""
import argparse
import json
import os
from pathlib import Path
import tempfile

OWE_ACTIVE = "#define WE_OW_ENCOUNTERS                        TRUE"
OWE_DISABLED = "#define WE_OW_ENCOUNTERS                        FALSE"
CLASSIC_RANDOM = "#define WE_VANILLA_RANDOM           TRUE"
OWE_ENTRY = "void UpdateOverworldWildEncounter(void)\n{\n    //Check if possible to spawn.\n"
OWE_GUARD = """void UpdateOverworldWildEncounter(void)
{
    // M8: the classic-encounter profile never runs the per-frame OWE scans.
    // Clean up once if a generated OWE is still around after a map/save load.
    if (!WE_OW_ENCOUNTERS)
    {
        if (sOWESpawnCountdown != OWE_NO_ENCOUNTER_SET)
        {
            DespawnAllOverworldWildEncounters(OWE_GENERATED, 0);
            sOWESpawnCountdown = OWE_NO_ENCOUNTER_SET;
        }
        return;
    }
    //Check if possible to spawn.
"""
GRASS_HELPER = """// Grand World M8: land encounters are triggered only by grass metatiles.
static bool8 GrandWorld_IsGrassEncounterTile(u16 behavior)
{
    return MetatileBehavior_IsTallGrass(behavior)
        || MetatileBehavior_IsLongGrass(behavior)
        || MetatileBehavior_IsAshGrass(behavior);
}

bool8 StandardWildEncounter("""
LAND_OLD = "        if (MetatileBehavior_IsLandWildEncounter(curMetatileBehavior) == TRUE)\n"
LAND_NEW = ("        if (MetatileBehavior_IsLandWildEncounter(curMetatileBehavior) == TRUE\n"
            "         && GrandWorld_IsGrassEncounterTile(curMetatileBehavior))\n")
SCENT_OLD = "        if (MetatileBehavior_IsLandWildEncounter(MapGridGetMetatileBehaviorAt(x, y)) == TRUE)\n"
SCENT_NEW = ("        if (MetatileBehavior_IsLandWildEncounter(MapGridGetMetatileBehaviorAt(x, y)) == TRUE\n"
             "         && GrandWorld_IsGrassEncounterTile(MapGridGetMetatileBehaviorAt(x, y)))\n")


def replace_once(source, old, new, label):
    n = source.count(old)
    if n != 1:
        raise ValueError(f"{label}: expected one exact match, found {n}")
    return source.replace(old, new, 1)


def prepare(root):
    config = root / "include/config/wild_encounter.h"
    core = root / "src/wild_encounter.c"
    owe = root / "src/wild_encounter_ow.c"
    if not all(p.is_file() for p in (config, core, owe)):
        raise ValueError("expected full pinned World encounter source tree")
    original = {p: p.read_text(encoding="utf-8") for p in (config, core, owe)}
    if original[config].count(CLASSIC_RANDOM) != 1:
        raise ValueError("classic random encounter policy changed: refusing edit")
    if original[core].count("bool8 StandardWildEncounter(") != 1:
        raise ValueError("standard encounter function anchor changed")
    if original[core].count("bool8 SweetScentWildEncounter(") != 1:
        raise ValueError("Sweet Scent anchor changed")
    if original[owe].count("    if (!WE_OW_ENCOUNTERS\n") != 1:
        raise ValueError("OWE cleanup guard no longer unique")
    changes = {
        config: replace_once(original[config], OWE_ACTIVE, OWE_DISABLED, "generated OWE flag"),
        core: replace_once(original[core], "bool8 StandardWildEncounter(",
                           GRASS_HELPER, "grass checker injection"),
        owe: replace_once(original[owe], OWE_ENTRY, OWE_GUARD, "early OWE fast-path"),
    }
    changes[core] = replace_once(changes[core], LAND_OLD, LAND_NEW, "grass walking trigger")
    changes[core] = replace_once(changes[core], SCENT_OLD, SCENT_NEW, "grass Sweet Scent")
    return original, changes


def apply(root, write=False):
    original, updated = prepare(root)
    if write:
        staged = {}
        installed = []
        try:
            for path, content in updated.items():
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                                 prefix=path.name + ".m8stage-",
                                                 dir=path.parent, delete=False) as temp:
                    temp.write(content)
                    staged[path] = Path(temp.name)
            for path, temp in staged.items():
                os.replace(temp, path)
                installed.append(path)
        except BaseException:
            for path in installed:
                path.write_text(original[path], encoding="utf-8")
            raise
        finally:
            for temp in staged.values():
                temp.unlink(missing_ok=True)
    return {
        "mode": "applied" if write else "preflight",
        "profile": "grass-only classic land encounters, no generated visible overworld wild",
        "modified": [str(p.relative_to(root)) for p in updated],
        "generated_owe": False,
        "classic_random_encounters": True,
        "land_grass_only": True,
        "water_surfing_fishing_unchanged": True,
        "rock_smash_scripted_special_unchanged": True,
        "pokemon_teams_saves_species_levels_rates_unchanged": True,
        "fps_measured": False,
        "scope": "isolated World checkout only, no edits to upstream or main",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("world", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = apply(args.world, write=args.apply)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
