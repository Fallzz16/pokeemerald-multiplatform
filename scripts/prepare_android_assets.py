#!/usr/bin/env python3
"""Build referenced binary graphics/sound assets for a clean Android NDK build.

Portable CMake directly preprocesses every game translation unit. Unlike the
native Makefile, it does not infer `INCBIN_*` graphics prerequisites.
This script asks the *existing* Emerald Make rules to generate those assets.
No copyrighted resources are downloaded or regenerated from other games.
"""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
INPUT_FOLDERS = ("src", "gflib", "data", "sound", "include")
EXTENSIONS = {".c", ".h", ".s", ".inc"}
PATTERNS = (
    re.compile(r'INCBIN(?:_[A-Z0-9]+)?\s*\(\s*"([^"]+)"'),
    re.compile(r'\.incbin\s+"([^"]+)"', re.I),
)
SUPPORTED = (".4bpp", ".8bpp", ".1bpp", ".gbapal", ".lz", ".rl",
             ".bin", ".latfont", ".hwjpnfont", ".fwjpnfont", ".pcm")
missing = set()

for folder in INPUT_FOLDERS:
    for path in (ROOT / folder).rglob("*"):
        if not path.is_file() or path.suffix not in EXTENSIONS:
            continue
        contents = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in PATTERNS:
            for raw in pattern.findall(contents):
                if not raw.startswith(("graphics/", "data/", "sound/")):
                    continue
                target = ROOT / raw
                # Paths in the source should not traverse outside this repo.
                if ".." in Path(raw).parts:
                    raise SystemExit(f"Invalid asset path in {path}: {raw}")
                if not target.exists() and raw.endswith(SUPPORTED):
                    missing.add(raw)

print(f"Android asset preparation: {len(missing)} generated assets requested", flush=True)
if missing:
    command = ["make", "-f", "Makefile_pc", "-j6", *sorted(missing)]
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode:
        raise SystemExit(f"Asset make failed (exit {result.returncode})")
    still_missing = [str(p) for p in sorted(missing) if not (ROOT / p).is_file()]
    if still_missing:
        raise SystemExit(f"Asset generation incomplete: {still_missing[:20]}")
print("Android source asset preflight: PASS", flush=True)
