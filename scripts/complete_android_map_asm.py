#!/usr/bin/env python3
"""Android-only assembler preflight for generated Hoenn map tables.

The portable CMake preprocessor pipeline strips the .include line for
data/maps/groups.inc. Restore that include to the GENERATED assembly only.
This does not edit map JSON, compiled GBA maps, events, or original source.
"""
from pathlib import Path
import sys

def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: complete_android_map_asm.py OUTPUT.asm RELATIVE_SOURCE")
    filename = Path(sys.argv[1])
    source = sys.argv[2].replace("\\", "/")
    if source != "data/maps.s":
        return
    contents = filename.read_text(encoding="utf-8")
    directive = '.include "data/maps/groups.inc"'
    if directive not in contents:
        with filename.open("a", encoding="utf-8") as out:
            out.write("\n" + directive + "\n")
    assert directive in filename.read_text(encoding="utf-8"), "Hoenn map group include missing"
    print("Android map table include restored in generated data/maps.s (original unchanged)")
if __name__ == "__main__":
    main()
