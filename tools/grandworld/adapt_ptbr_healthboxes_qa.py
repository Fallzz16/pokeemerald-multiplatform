#!/usr/bin/env python3
"""Keep the World healthbox gameplay assertions after translating the battle prompt.

The pinned upstream mGBA test waits for gText_WhatWillPkmnDo, recognized by
the English-only substring WHAT WILL. Brazilian Portuguese says "O que".
This adapter changes ONLY the text-matching expression in the ephemeral
Lua test. The 24 checks for live battle state/HP/sprites remain untouched.
"""
import argparse
from pathlib import Path

SCRIPT = "test/overworld/lua/ExpansionHealthboxes.lua"
BATTLE = "src/battle_message.c"
ORIGINAL = 'battleText():find("WHAT WILL", 1, true)'
BILINGUAL = '(battleText():find("WHAT WILL", 1, true) or battleText():find("O QUE", 1, true))'
EXPECTED_COUNT = 3
LOCALIZED = 'O que\\n{B_BUFF1} vai fazer?'


def apply(world, write=False):
    world = Path(world)
    path = world / SCRIPT
    lua = path.read_text(encoding="utf-8")
    battles = (world / BATTLE).read_text(encoding="utf-8")
    if LOCALIZED not in battles:
        raise ValueError("actual localized battle action prompt missing")
    if lua.count(ORIGINAL) != EXPECTED_COUNT or BILINGUAL in lua:
        raise ValueError("pinned World healthbox prompt anchors changed or adapter rerun")
    # Fail if the healthbox test itself drifted and the critical assertions
    # (Safari count, singles HP change, doubles state) disappeared.
    invariants = (
        'F.check("gNumSafariBalls is 29 after one throw"',
        'F.check("an HP word changed (not the bar alone)"',
        'F.check("doubles_healthbox_reached"',
        'F.check("a doubles healthbox sprite is live"',
        'F.check("field control returns after doubles"',
    )
    if any(token not in lua for token in invariants):
        raise ValueError("an original healthbox gameplay assertion is missing")
    changed = lua.replace(ORIGINAL, BILINGUAL)
    if write:
        path.write_text(changed, encoding="utf-8")
    return {"status": "applied" if write else "preflight",
            "changes": EXPECTED_COUNT, "gameplay_files_changed": 0,
            "assertions_preserved": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(apply(args.world, args.apply))


if __name__ == "__main__":
    main()
