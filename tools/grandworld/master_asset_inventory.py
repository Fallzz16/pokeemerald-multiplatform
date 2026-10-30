#!/usr/bin/env python3
"""Read-only sprite/audio duplicate inventory for a reusable GBA master ROM.

Only byte-for-byte matching SOURCE files are reported. They are candidates
for investigation, not measured ROM savings: compiled assets may use distinct
tags, palettes, references, formats or may not be linked at all. Never delete.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOTS = ("graphics", "sound")
EXTENSIONS = {
    ".png", ".pal", ".mid", ".wav", ".bin", ".aif", ".aiff", ".pcm",
    ".4bpp", ".8bpp", ".1bpp", ".gbapal", ".lz", ".smol", ".rl",
}


def inventory(world):
    world = Path(world).resolve()
    if not (world / "Makefile").is_file():
        raise ValueError("expected pinned GBA engine checkout (Makefile missing)")
    digest_groups = defaultdict(list)
    bytes_by_ext = Counter()
    files_by_ext = Counter()
    scanned = 0
    for folder in ROOTS:
        directory = world / folder
        if not directory.is_dir():
            raise ValueError("missing required source folder: " + folder)
        for file in sorted(directory.rglob("*")):
            if not file.is_file() or file.is_symlink():
                continue
            if file.suffix.lower() not in EXTENSIONS:
                continue
            size = file.stat().st_size
            if size == 0:
                continue
            relative = file.relative_to(world).as_posix()
            digest = hashlib.sha256(file.read_bytes()).hexdigest()
            digest_groups[(digest, size)].append(relative)
            bytes_by_ext[file.suffix.lower()] += size
            files_by_ext[file.suffix.lower()] += 1
            scanned += 1
    duplicates = []
    for (digest, size), paths in digest_groups.items():
        if len(paths) > 1:
            duplicates.append({
                "sha256": digest,
                "size_bytes_each": size,
                "copy_count": len(paths),
                "raw_source_duplicate_bytes": size * (len(paths) - 1),
                "paths": sorted(paths),
            })
    duplicates.sort(key=lambda e: (-e["raw_source_duplicate_bytes"], e["paths"]))
    return {
        "kind": "read_only_exact_source_asset_inventory",
        "source_roots": ROOTS,
        "files_scanned": scanned,
        "raw_source_bytes": sum(bytes_by_ext.values()),
        "files_by_extension": dict(sorted(files_by_ext.items())),
        "bytes_by_extension": dict(sorted(bytes_by_ext.items())),
        "exact_duplicate_sets": len(duplicates),
        "raw_source_duplicate_bytes_upper_bound": sum(x["raw_source_duplicate_bytes"] for x in duplicates),
        "duplicate_groups": duplicates[:80],
        "all_duplicate_groups_included": len(duplicates) <= 80,
        "actual_rom_bytes_saved": 0,
        "modifications_applied": False,
        "warning": "Source-level duplicates do not prove linker savings. Review references/palettes and test before deduplicating.",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("world", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    try:
        report = inventory(args.world)
    except (OSError, ValueError) as error:
        sys.exit("FAIL CLOSED: " + str(error))
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "duplicate_groups"}, indent=2))


if __name__ == "__main__":
    main()
