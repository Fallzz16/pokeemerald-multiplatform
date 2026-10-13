#!/usr/bin/env python3
"""Generate every map's native header/events/connections using Emerald mapjson.

The normal game Make rules generate per-map .inc files as prerequisites of the
GBA map object. CMake needs them pre-generated for Android. We use those exact
rules and refuse missing results rather than introducing blank fallback maps.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
maps = sorted((ROOT / "data/maps").glob("*/map.json"))
if not maps:
    raise SystemExit("No map JSON files present")
headers = [str(p.parent.relative_to(ROOT) / "header.inc") for p in maps]
print(f"Preparing {len(headers)} Hoenn map headers using the original Make rules", flush=True)
subprocess.run(["make", "-f", "Makefile_pc", "-j4", *headers], cwd=ROOT, check=True)
for source in maps:
    for suffix in ("header.inc", "events.inc", "connections.inc"):
        target = source.parent / suffix
        if not target.is_file():
            raise SystemExit(f"mapjson output missing: {target}")
print("Hoenn mapjson Android asset preflight: PASS", flush=True)
