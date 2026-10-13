#!/usr/bin/env python3
"""Complete *generated* ARM map assembly using Emerald's mapjson outputs.

No tracked GBA maps, map JSON, scripts or native Windows sources are changed.
The original ARM assembly preprocessing skips generated Hoenn map headers.
Expand them into an Android-only assembly file and translate exported :: labels
to GNU-as-compatible .global + : labels.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LABEL = re.compile(r"(?m)^([A-Za-z_][A-Za-z_0-9]*):{1,2}(?=\s*(?:$|@|//))")
INCLUDE = re.compile(r'^\s*\.include\s+"(data/maps/[^"]+)"\s*$')


def map_headers(path: Path, stack: frozenset[Path] = frozenset()) -> str:
    if path in stack:
        raise ValueError(f"Cyclic Hoenn include: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"Generated map header missing: {path}; run mapjson first")
    expanded = []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        match = INCLUDE.match(line.strip())
        if match:
            rel = Path(match.group(1))
            if ".." in rel.parts:
                raise ValueError(f"Unsafe map include: {rel}")
            expanded.append(map_headers(ROOT / rel, stack | {path}))
        else:
            expanded.append(line)
    return "".join(expanded)


def to_gnu_as(data: str) -> str:
    return LABEL.sub(lambda match: ".globl " + match.group(1) + "\n" + match.group(1) + ":", data)


def complete(filename: Path, source: str) -> bool:
    if source.replace("\\", "/") != "data/maps.s":
        return False
    current = filename.read_text(encoding="utf-8")
    existing = set(re.findall(r"(?m)^([A-Za-z_][A-Za-z_0-9]*):{1,2}\s*$", current))
    # Map headers define PetalburgCity, Route101 etc.; groups point to them.
    headers = map_headers(ROOT / "data/maps/headers.inc")
    groups = (ROOT / "data/maps/groups.inc").read_text(encoding="utf-8")
    header_labels = set(LABEL.findall(headers))
    group_labels = set(LABEL.findall(groups))
    if "PetalburgCity" not in header_labels or "gMapGroups" not in group_labels:
        raise ValueError("mapjson headers/groups do not contain the expected Hoenn symbols")
    if existing & (header_labels | group_labels):
        raise ValueError("Hoenn header/group symbol already present; refusing duplicate labels")
    with filename.open("a", encoding="utf-8") as out:
        out.write("\n.section .rodata\n")
        out.write(to_gnu_as(headers))
        out.write("\n")
        out.write(to_gnu_as(groups))
        out.write("\n")
    print(f"Android: restored {len(header_labels)} map headers and {len(group_labels)} map groups in temporary assembly", flush=True)
    return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: complete_android_map_asm.py OUTPUT.asm RELATIVE_SOURCE")
    complete(Path(sys.argv[1]), sys.argv[2])
