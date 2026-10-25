#!/usr/bin/env python3
"""Apply two verified ARM APCS data-type alignments ONLY to disposable native World.

This changes real Pokeblock storage stride from 7 to 8 and ItemSlot alignment
from 2 to 4 on x86 GCC32, as measured against the pinned GBA World compiler.
Original ARM declarations are preserved for non-PORTABLE builds. It does NOT
suppress save checks or write Pokémon save files.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

DECLARATIONS = (
    """struct ItemSlot
{
    enum Item itemId;
    u16 quantity;
};""",
    """struct Pokeblock
{
    u8 color;
    u8 spicy;
    u8 dry;
    u8 sweet;
    u8 bitter;
    u8 sour;
    u8 feel;
};""",
    """struct Pokevial
{
    u8 size : 4;
    u8 dose : 4;
};""",
)

def transform(source):
    for decl in DECLARATIONS:
        if source.count(decl) != 1:
            raise ValueError("World data type drift or adapter applied twice")
        align = (
            decl[:-2] + "}\n#if defined(PORTABLE)\n"
            "__attribute__((aligned(4)))\n#endif\n;"
        )
        source = source.replace(decl, align, 1)
    return source

def stage(root, report, apply):
    root = Path(root).resolve()
    header = root / "include/global.h"
    if not header.exists() or not (root / "src/region_switch.c").exists():
        raise ValueError("not a disposable World source checkout")
    old = header.read_text(encoding="utf-8")
    changed = transform(old)
    info = {
        "schema":1, "stage":"P2_native_save_abi_nested_types",
        "types":["ItemSlot aligned 4", "Pokeblock aligned 4",
                 "Pokevial bitfield-aligned 4"],
        "gba_unchanged":True, "save_assertions_removed":False,
        "applied":apply,
        "before_sha256":hashlib.sha256(old.encode()).hexdigest(),
        "after_sha256":hashlib.sha256(changed.encode()).hexdigest(),
    }
    if apply:
        fd, tmp = tempfile.mkstemp(prefix=".gw-save-nested-", suffix=".tmp", dir=header.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(changed)
            os.replace(tmp, header)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    Path(report).write_text(json.dumps(info, indent=2)+"\n", encoding="utf-8")
    return info

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--output", default="native-save-nested-overlay.json")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    try:
        print(json.dumps(stage(args.world, args.output, args.apply), indent=2))
    except (OSError, ValueError) as e:
        p.exit(1, "NESTED SAVE ABI OVERLAY REFUSED: %s\n" % e)

if __name__ == "__main__":
    main()
