#!/usr/bin/env python3
"""Complete Android's generated Hoenn maps assembly without editing sources.

The Android CMake preprocessing pipeline drops the expansion of map groups.
The original Make-based GBA/Windows source and all generated map files remain
unchanged. GNU ARM as rejects the decompilation's label:: pseudo-syntax, so
only the generated native assembly receives ordinary label: definitions.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LABEL_PATTERN = re.compile(r"(?m)^([A-Za-z_][A-Za-z_0-9]*):{2}(?=\s*(?:$|@|//))")


def complete(filename: Path, source: str) -> bool:
    if source.replace("\\", "/") != "data/maps.s":
        return False
    contents = filename.read_text(encoding="utf-8")
    # Fail clearly if the generator changes to emit these labels on its own.
    if re.search(r"(?m)^gMapGroups:(?!:)", contents):
        return False
    groups_file = ROOT / "data/maps/groups.inc"
    if not groups_file.is_file():
        raise FileNotFoundError("Generate map groups first: data/maps/groups.inc")
    groups = groups_file.read_text(encoding="utf-8")
    if ".include" in groups:
        raise ValueError("Unexpected nested include in generated map groups")
    groups, count = LABEL_PATTERN.subn(r"\1:", groups)
    if count < 2 or not re.search(r"(?m)^gMapGroups:", groups):
        raise ValueError("Invalid group labels in generated Hoenn map table")
    with filename.open("a", encoding="utf-8") as out:
        out.write("\n.section .rodata\n.globl gMapGroups\n")
        out.write(groups)
        if not groups.endswith("\n"):
            out.write("\n")
    print(f"Android: appended {count} translated map-group labels to generated assembly")
    return True


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: complete_android_map_asm.py OUTPUT.asm RELATIVE_SOURCE")
    complete(Path(sys.argv[1]), sys.argv[2])


if __name__ == "__main__":
    main()
