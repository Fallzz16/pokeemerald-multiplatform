#!/usr/bin/env python3
"""Apply isolated *portable-only* World save ABI alignments.

Do not run in the GBA reference checkout before regression compilation.
This script modifies exactly two declarations in a disposable World tree;
without -DPORTABLE the declarations retain their original ABI and syntax.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

TIME = """struct Time
{
    /*0x00*/ s16 days;
    /*0x02*/ s8 hours;
    /*0x03*/ s8 minutes;
    /*0x04*/ s8 seconds;
};"""
DOME = """struct BattleDomeTrainer
{
    u16 trainerId:10;
    u16 isEliminated:1;
    u16 eliminatedAt:2;
    u16 forfeited:3;
};"""
ASSERTION = "STATIC_ASSERT(sizeof(struct SaveBlock2) == 0xF2C, SaveBlock2SizeUnchanged);"


def align_portable(declaration):
    if not declaration.endswith("};"):
        raise ValueError("expected terminating '};'")
    # Portable host GCC only. For GBA the original declaration remains intact.
    return declaration[:-2] + (
        "}\n#if defined(PORTABLE)\n"
        "__attribute__((aligned(4)))\n#endif\n;"
    )


def transform(source):
    if source.count(ASSERTION) != 1:
        raise ValueError("World save ABI guard missing")
    for name, original in (("Time", TIME), ("BattleDomeTrainer", DOME)):
        if source.count(original) != 1:
            raise ValueError("World " + name + " changed; refusing silent ABI patch")
        source = source.replace(original, align_portable(original))
    return source


def stage(world, output, apply):
    world = Path(world).resolve()
    header = world / "include/global.h"
    if not header.is_file() or not (world / "src/region_switch.c").is_file():
        raise ValueError("not a World source checkout")
    before = header.read_text(encoding="utf-8")
    after = transform(before)
    info = {
        "schema": 1,
        "stage": "P1_native_save_abi_overlay",
        "header": "include/global.h",
        "changes": ["Time aligned to 4 (PORTABLE only)",
                    "BattleDomeTrainer aligned to 4 (PORTABLE only)"],
        "gba_reference_changed": False,
        "save_assert_removed": False,
        "apply_requested": bool(apply),
        "source_before_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "source_after_sha256": hashlib.sha256(after.encode()).hexdigest(),
    }
    if apply:
        fd, temp = tempfile.mkstemp(prefix=".gw-saveabi-", suffix=".tmp", dir=header.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(after)
            os.replace(temp, header)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
    Path(output).write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    return info


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--report", default="native-save-abi-overlay.json")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    try:
        print(json.dumps(stage(args.world, args.report, args.apply), indent=2))
    except (ValueError, OSError) as exc:
        p.exit(1, "SAVE ABI OVERLAY REFUSED: %s\n" % exc)


if __name__ == "__main__":
    main()
