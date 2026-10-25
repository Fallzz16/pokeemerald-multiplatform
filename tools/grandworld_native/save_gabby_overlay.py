#!/usr/bin/env python3
"""Native-only alignment of World GabbyAndTyData; never modifies GBA ABI.

The measured ARM APCS save layout requires its 16-byte stride, whereas host
GCC i386 places Easy Chat data two bytes too early. Guard exact source
declaration and apply only to a disposable World checkout.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

ANCHOR = """struct GabbyAndTyData
{
    /*2BA4*/ u16 mon1;
    /*2BA6*/ u16 mon2;
    /*2BA8*/ u16 lastMove;
    /*2BAA*/ u16 quote[1];
    /*2BAC*/ mapsec_u8_t mapnum;
    /*2BAD*/ u8 battleNum;
    /*2BAE*/ u8 battleTookMoreThanOneTurn:1;
             u8 playerLostAMon:1;
             u8 playerUsedHealingItem:1;
             u8 playerThrewABall:1;
             u8 onAir:1;
             u8 valA_5:3;
    /*2BAF*/ u8 battleTookMoreThanOneTurn2:1;
             u8 playerLostAMon2:1;
             u8 playerUsedHealingItem2:1;
             u8 playerThrewABall2:1;
             u8 valB_4:4;
};"""

def transform(data):
    if data.count(ANCHOR) != 1:
        raise ValueError("GabbyAndTyData declaration changed or already patched")
    return data.replace(
        ANCHOR,
        ANCHOR[:-2] + "}\n#if defined(PORTABLE)\n"
        "__attribute__((aligned(4)))\n#endif\n;",
        1)

def apply(world, report, edit):
    root = Path(world).resolve()
    file = root / "include/global.tv.h"
    if not file.is_file() or not (root / "src/region_switch.c").is_file():
        raise ValueError("expected a disposable World source checkout")
    original = file.read_text(encoding="utf-8")
    updated = transform(original)
    info = {"schema": 1, "stage": "P2_GabbyAndTyData_native_ABI",
            "applied": bool(edit), "gba_unchanged": True,
            "assertions_removed": False,
            "original_sha256": hashlib.sha256(original.encode()).hexdigest(),
            "patched_sha256": hashlib.sha256(updated.encode()).hexdigest()}
    if edit:
        fd, tmp = tempfile.mkstemp(prefix=".gw-gabby-", suffix=".tmp", dir=file.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                out.write(updated)
            os.replace(tmp, file)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    Path(report).write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    return info

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--output", default="native-gabby-abi.json")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    try:
        print(json.dumps(apply(args.world, args.output, args.apply), indent=2))
    except (OSError, ValueError) as e:
        p.exit(1, "SAVE ABI GABBY ADAPTER REFUSED: %s\n" % e)

if __name__ == "__main__":
    main()
