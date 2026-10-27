#!/usr/bin/env python3
"""Read-only, fail-closed source gate for M9 MASTER VISIBLE GBA builds.

Checks the *pinned World checkout after M8 adapters* but before compilation.
It does NOT turn a game feature on and does NOT certify live gameplay.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

CONFIG = {
    "include/config/wild_encounter.h": {
        "WE_OW_ENCOUNTERS": "TRUE",
        "WE_VANILLA_RANDOM": "TRUE",
        "WE_OWE_RESTRICT_METATILE": "TRUE",
        "WE_OWE_RESTRICT_MAP": "TRUE",
    },
    "include/config/overworld.h": {
        "OW_POKEMON_OBJECT_EVENTS": "TRUE",
        "OW_FOLLOWERS_ENABLED": "TRUE",
        "OW_GFX_COMPRESS": "FALSE",
        "OW_SUBSTITUTE_PLACEHOLDER": "TRUE",
    },
}
SOURCE_HOOKS = {
    "src/wild_encounter.c": [
        "StandardWildEncounter(",
        "MetatileBehavior_IsLandWildEncounter(",
        "MetatileBehavior_IsWaterWildEncounter(",
        "RockSmashWildEncounter(",
        "FishingWildEncounter(",
    ],
    "src/wild_encounter_ow.c": [
        "IsObjectActiveOWE(",
        "CreateEnemyPartyOWE(",
        "TRAINER_TYPE_OW_WILD_ENCOUNTER",
    ],
}
# This marker must not occur in the compiled World C/config sources:
# applying the earlier experimental patch suppresses visible wild and water.
INCOMPATIBLE_MARKER = "GW_GRASS_ONLY_WILD"


def verify(world: Path):
    world = world.resolve()
    if not (world / "Makefile").is_file():
        raise ValueError("not a complete pinned World checkout (Makefile missing)")
    snapshots = {}
    checks = []
    for rel, fields in CONFIG.items():
        path = world / rel
        if not path.is_file():
            raise ValueError("missing source file: " + rel)
        data = path.read_text(encoding="utf-8")
        snapshots[rel] = data
        for key, expected in fields.items():
            hits = re.findall(r"(?m)^[ \t]*#define[ \t]+"
                              + re.escape(key)
                              + r"[ \t]+([A-Za-z_][A-Za-z_0-9]*)\b", data)
            if hits != [expected]:
                raise ValueError(f"{rel}: expected exactly {key}={expected}, saw {hits}")
            checks.append(key + "=" + expected)
    for rel, hooks in SOURCE_HOOKS.items():
        path = world / rel
        if not path.is_file():
            raise ValueError("missing original C source: " + rel)
        data = path.read_text(encoding="utf-8")
        snapshots[rel] = data
        for token in hooks:
            if token not in data:
                raise ValueError(f"{rel}: original encounter hook missing: {token}")
            checks.append("source-hook:" + token)
    for rel, data in snapshots.items():
        if INCOMPATIBLE_MARKER in data:
            raise ValueError(f"{rel}: incompatible strict-grass-only patch detected")
    return {
        "profile": "M9_MASTER_VISIBLE",
        "mode": "read_only_source_preflight",
        "source_checks": len(checks),
        "checks": checks,
        "file_sha256": {
            name: hashlib.sha256(data.encode("utf-8")).hexdigest()
            for name, data in sorted(snapshots.items())
        },
        "generated_overworld_spawns_enabled_by_config": True,
        "step_encounters_enabled_by_config": True,
        "fishing_and_rock_smash_hooks_present": True,
        "habitat_tables_modified": False,
        "saves_modified": False,
        "visible_spawns_observed_in_emulator": False,
        "gameplay_approved": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.world)
    except (ValueError, OSError, UnicodeError) as exc:
        sys.exit("FAIL CLOSED: " + str(exc))
    rendered = json.dumps(result, indent=2) + "\n"
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
