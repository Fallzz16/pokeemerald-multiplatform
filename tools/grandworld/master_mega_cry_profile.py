#!/usr/bin/env python3
"""Optional compact audio profile for pinned World; never alters standard Megas.

This reuses World's own P_MODIFIED_MEGA_CRIES=FALSE pathway, which
still plays the original species cry with its supported high-pitch mode.
Only apply to a disposable checkout, NEVER to the original World upstream.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

CONF = "include/config/pokemon.h"
SOUND = "src/sound.c"
CRIES = "sound/cry_tables.inc"
SOUNDS = "sound/direct_sound_data.inc"
REQUIRED = {
    CONF: (
        "#define P_MODIFIED_MEGA_CRIES            P_MEGA_EVOLUTIONS",
        "#define P_MODIFIED_MEGA_CRY_MODE         CRY_MODE_HIGH_PITCH",
        "#define P_CRIES_ENABLED                  TRUE",
    ),
    SOUND: (
        "if (!P_MODIFIED_MEGA_CRIES && gSpeciesInfo[species].isMegaEvolution)",
        "mode = P_MODIFIED_MEGA_CRY_MODE;",
    ),
    CRIES: (".if P_MODIFIED_MEGA_CRIES == TRUE",),
    SOUNDS: (".if P_MODIFIED_MEGA_CRIES == TRUE",),
}


def prepare(world):
    world = Path(world)
    if not (world / "Makefile").is_file():
        raise ValueError("missing pinned GBA World Makefile")
    for rel, tokens in REQUIRED.items():
        data = (world / rel).read_text(encoding="utf-8")
        for token in tokens:
            if token not in data:
                raise ValueError(f"{rel}: upstream cry configuration/behavior drift: {token}")
    before = (world / CONF).read_text(encoding="utf-8")
    pattern = r"(?m)^(#define P_MODIFIED_MEGA_CRIES\s+)P_MEGA_EVOLUTIONS(\s*//[^\n]*)$"
    after, replacements = re.subn(pattern, r"\g<1>FALSE\g<2>", before)
    if replacements != 1 or "#define P_MODIFIED_MEGA_CRIES" not in after:
        raise ValueError("mega cry configuration not patchable exactly once")
    return before, after


def run(world, apply=False):
    world = Path(world).resolve()
    before, after = prepare(world)
    if apply:
        (world / CONF).write_text(after, encoding="utf-8")
    return {
        "profile": "MASTER_OPTIONAL_MEGA_CRY_SHARED_HIGH_PITCH",
        "mode": "applied" if apply else "read_only_preflight",
        "before_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "after_sha256": hashlib.sha256(after.encode()).hexdigest(),
        "distinct_mega_cry_audio_kept": False,
        "regular_pokemon_cries_enabled": True,
        "mega_cries_remain_audible_via_native_pitched_mode": True,
        "species_or_forms_removed": 0,
        "saves_modified": False,
        "gameplay_approved": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("world", type=Path)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    try:
        result = run(args.world, apply=args.apply)
    except (OSError, ValueError, UnicodeError) as error:
        sys.exit("FAIL CLOSED: " + str(error))
    rendered = json.dumps(result, indent=2) + "\n"
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
