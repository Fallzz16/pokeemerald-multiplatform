#!/usr/bin/env python3
"""Expand generated Emerald map/layout includes for the Android ARM assembler.

The original C/GBA sources, map JSON, PC objects and generated mapjson files
are never modified. Only the temporary CMake assembly copy is normalized.
This does NOT append a second map table: it replaces each existing .include
with that file's content, recursively, exactly once.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LABEL = re.compile(r"(?m)^([A-Za-z_][A-Za-z_0-9]*):{1,2}(?=\s*(?:$|@|//))")
INCLUDE = re.compile(r'^\s*\.include\s+"((?:data/maps|data/layouts)/[^"]+)"\s*$')
MAX_DEPTH = 12


def expand(text: str, stack: tuple[Path, ...] = ()) -> tuple[str, int]:
    if len(stack) >= MAX_DEPTH:
        raise ValueError("Map include depth exceeded; refusing cyclic expansion")
    result = []
    count = 0
    for line in text.splitlines(keepends=True):
        found = INCLUDE.fullmatch(line.strip())
        if found is None:
            result.append(line)
            continue
        rel = Path(found.group(1))
        if ".." in rel.parts or rel.is_absolute():
            raise ValueError(f"Unsafe generated map include: {rel}")
        absolute = ROOT / rel
        if absolute in stack:
            raise ValueError(f"Cyclic generated map include: {absolute}")
        if not absolute.is_file():
            raise FileNotFoundError(f"Missing mapjson output: {absolute}")
        nested, n = expand(absolute.read_text(encoding="utf-8"), stack + (absolute,))
        result.append(f"\n@ Android expanded generated map include: {rel}\n")
        result.append(nested)
        result.append("\n")
        count += n + 1
    return "".join(result), count


def complete(filename: Path, source: str) -> bool:
    normalized_source = source.replace("\\", "/")
    if normalized_source not in ("data/maps.s", "data/map_events.s"):
        return False
    current = filename.read_text(encoding="utf-8")
    expanded, count = expand(current)
    # mapjson outputs may already have been expanded by the upstream preproc.
    # Zero pending includes is valid when the expected map definitions exist.
    if normalized_source == "data/maps.s":
        if not re.search(r"(?m)^gMapGroups:{1,2}\s*$", expanded):
            raise ValueError("mapjson groups not present after expanding original include")
        if not re.search(r"(?m)^PetalburgCity:{1,2}\s*$", expanded):
            raise ValueError("mapjson headers not present after expanding original include")
    elif not re.search(r"(?m)^PetalburgCity_MapEvents:{1,2}\\s*$", expanded):
        raise ValueError("mapjson event definitions absent from generated event assembly")
    if count == 0:
        print(f"Android: original preproc expanded {source}; normalizing labels only", flush=True)
    converted = LABEL.sub(
        lambda match: ".globl " + match.group(1) + "\n" + match.group(1) + ":",
        expanded,
    )
    # Match the already-established Emerald portable compiler pseudo-op policy.
    converted = converted.replace(".4byte", ".word").replace(".2byte", ".short")
    filename.write_text(converted, encoding="utf-8")
    print(f"Android: expanded {count} generated map/layout includes into {source}", flush=True)
    return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: complete_android_map_asm.py OUTPUT.asm RELATIVE_SOURCE")
    complete(Path(sys.argv[1]), sys.argv[2])
