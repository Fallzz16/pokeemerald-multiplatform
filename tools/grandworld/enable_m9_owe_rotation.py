#!/usr/bin/env python3
"""Opt-in M9 generated OWE rotation, using pinned World's existing native code.

Keeps the native 4-spawn cap, 240-frame replacement countdown, normal battles
and followers. Protects naturally rolled shiny encounters from routine eviction.
Preflight is read-only; --apply edits the disposable World checkout only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

CONFIG = "include/config/wild_encounter.h"
SOURCE = "src/wild_encounter_ow.c"
REQUIRED = {
    "WE_OW_ENCOUNTERS": "TRUE",
    "WE_VANILLA_RANDOM": "TRUE",
    "WE_OWE_RESTRICT_METATILE": "TRUE",
    "WE_OWE_RESTRICT_MAP": "TRUE",
    "WE_OWE_SPAWN_REPLACEMENT": "FALSE",
    "WE_OWE_PREVENT_SHINY_DESPAWN": "FALSE",
}
CHANGES = {
    "WE_OWE_SPAWN_REPLACEMENT": "TRUE",
    "WE_OWE_PREVENT_SHINY_DESPAWN": "TRUE",
}
SOURCE_TOKENS = (
    "OWE_SPAWN_TIME_REPLACEMENT      240",
    "GetOldestActiveOWESlot(FALSE)",
    "ShouldDespawnGeneratedForNewOWE(owe)",
    "if (WE_OWE_PREVENT_SHINY_DESPAWN && info->isShiny)",
    "if (OW_SPECIES(slotMon) != SPECIES_NONE && (!HasOWENoDespawnFlag(slotMon) || forceRemove == TRUE))",
)


def compose(world):
    world = Path(world)
    if not (world / "Makefile").is_file():
        raise ValueError("expected complete pinned World checkout (Makefile missing)")
    before = (world / CONFIG).read_text(encoding="utf-8")
    source = (world / SOURCE).read_text(encoding="utf-8")
    for key, value in REQUIRED.items():
        pattern = r"(?m)^([ \\t]*#define[ \\t]+" + re.escape(key) + r"[ \\t]+)([A-Za-z_][A-Za-z_0-9]*)([^\\n]*)$"
        matches = list(re.finditer(pattern, before))
        if len(matches) != 1 or matches[0].group(2) != value:
            raise ValueError(f"{CONFIG}: expected exactly {key}={value}")
    for token in SOURCE_TOKENS:
        if token not in source:
            raise ValueError(f"{SOURCE}: original replacement/shiny safeguard changed: {token}")
    after = before
    for key, value in CHANGES.items():
        pattern = r"(?m)^([ \\t]*#define[ \\t]+" + re.escape(key) + r"[ \\t]+)(FALSE)([^\\n]*)$"
        after, count = re.subn(pattern, lambda m: m.group(1) + value + m.group(3), after)
        if count != 1:
            raise ValueError(f"{CONFIG}: failed to patch unique {key}")
    return before, after


def run(world, apply=False):
    world = Path(world).resolve()
    before, after = compose(world)
    if apply:
        (world / CONFIG).write_text(after, encoding="utf-8")
    return {
        "patch": "M9_NATIVE_OWE_ROTATION",
        "mode": "applied" if apply else "read_only_preflight",
        "before_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "after_sha256": hashlib.sha256(after.encode()).hexdigest(),
        "native_slots": 4,
        "native_full_pool_replacement_frames": 240,
        "protect_shiny_from_replacement": True,
        "interactions_or_distance_modified": False,
        "gameplay_approved": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = run(args.world, args.apply)
    except (OSError, UnicodeError, ValueError) as error:
        sys.exit("FAIL CLOSED: " + str(error))
    rendered = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
