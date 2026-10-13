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
    # With every mapjson output present the original preprocessor usually
    # expands all maps by itself. Do not append a second copy of that data.
    present_headers = existing & header_labels
    present_groups = existing & group_labels
    if present_headers and present_headers != header_labels:
        raise ValueError(f"Partially expanded Hoenn map headers: {len(present_headers)} of {len(header_labels)}")
    if present_groups and present_groups != group_labels:
        raise ValueError(f"Partially expanded Hoenn map groups: {len(present_groups)} of {len(group_labels)}")
    result = to_gnu_as(current)
    missing_headers = not present_headers
    missing_groups = not present_groups
    if missing_headers or missing_groups:
        result += "\n.section .rodata\n"
        if missing_headers:
            result += to_gnu_as(headers) + "\n"
        if missing_groups:
            result += to_gnu_as(groups) + "\n"
    filename.write_text(result, encoding="utf-8")
    print(f"Android map symbols: {len(header_labels)} headers, {len(group_labels)} groups, generated missing components: headers={missing_headers}, groups={missing_groups}", flush=True)
    return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: complete_android_map_asm.py OUTPUT.asm RELATIVE_SOURCE")
    complete(Path(sys.argv[1]), sys.argv[2])
