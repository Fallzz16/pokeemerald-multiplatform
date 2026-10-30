#!/usr/bin/env python3
"""Source-only species overworld frame tile cost inventory.

No bitmap decoded, no claim that a family is enabled in this ROM.
The pinned engine's OVERWORLD_DATA macro encodes 512-byte 32x32 frames and
2048-byte 64x64 frames; this inventories declared dimensions only.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

SPECIES = re.compile(r"(?m)^\s*\[(SPECIES_[A-Z0-9_]+)\]\s*=\s*\{")
OVERWORLD = re.compile(
    r"\b(OVERWORLD(?:_FEMALE)?)\s*\(\s*"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*,\s*"
    r"(SIZE_(?:32x32|64x64))\s*,"
)
ALL_OVERWORLD = re.compile(r"\bOVERWORLD(?:_FEMALE)?\s*\(")
SIZES = {"SIZE_32x32": {"pixels": 32, "frame_bytes": 512, "tiles_4bpp": 16},
         "SIZE_64x64": {"pixels": 64, "frame_bytes": 2048, "tiles_4bpp": 64}}


def analyze(root):
    root = Path(root)
    species_root = root / "src/data/pokemon/species_info"
    files = [species_root / f"gen_{g}_families.h" for g in range(1, 10)]
    entries, unknown, seen = [], [], set()
    for generation, path in enumerate(files, 1):
        src = path.read_text(encoding="utf-8")
        matches = list(SPECIES.finditer(src))
        if not matches:
            raise ValueError(f"FAIL CLOSED: no species initializers: {path}")
        for i, m in enumerate(matches):
            name = m.group(1)
            if name in seen:
                raise ValueError("duplicate species in inventory: " + name)
            seen.add(name)
            # Scope ends at next initializer, not next #endif. Conditional
            # compilation is NOT resolved and is explicitly unverified.
            body = src[m.end():matches[i+1].start() if i+1 < len(matches) else len(src)]
            parsed = list(OVERWORLD.finditer(body))
            all_count = len(ALL_OVERWORLD.findall(body))
            if all_count != len(parsed):
                unknown.append({"species": name, "generation": generation,
                                "macro_count": all_count, "parsed": len(parsed)})
                continue
            frames = []
            for call in parsed:
                kind, source, size = call.groups()
                entry = {"kind": kind, "pic_table": source,
                         "size": size, **SIZES[size]}
                frames.append(entry)
            entries.append({"species": name, "generation": generation,
                            "declared_overworld": bool(frames),
                            "frames": frames})
    if len(entries) < 200:
        raise ValueError("FAIL CLOSED: unexpectedly few source species")
    if unknown:
        raise ValueError(f"FAIL CLOSED: {len(unknown)} unexpected overworld syntax "
                         f"(first: {unknown[0]})")
    totals = Counter()
    risky = []
    for item in entries:
        if item["declared_overworld"]:
            totals[f"gen_{item['generation']}_declared"] += 1
        else:
            totals["no_explicit_overworld_macro"] += 1
        for frame in item["frames"]:
            totals[frame["size"]] += 1
            totals[f"gen_{item['generation']}_{frame['size']}"] += 1
            if frame["size"] == "SIZE_64x64":
                risky.append({"species": item["species"],
                              "generation": item["generation"],
                              "variant": frame["kind"],
                              "frame_bytes": frame["frame_bytes"]})
    return {
        "kind": "source_only_pinned_world_overworld_dimension_inventory",
        "meaning": "declared source entries, NOT confirmed enabled / built / rendered",
        "engine_macros": "OVERWORLD_DATA SIZE_32x32=512 bytes; SIZE_64x64=2048 bytes per frame",
        "families_scanned": 9,
        "species_initializers_scanned": len(entries),
        "overview_counts": dict(sorted(totals.items())),
        "large_frame_declarations": sorted(risky, key=lambda d: (d["generation"], d["species"])),
        "all_species": entries,
        "runtime_vram_proved_by_this_inventory": False,
        "assets_validated_or_decoded": False,
        "enabled_pokedex_size_proved": False,
        "rom_bytes_saved": 0,
        "game_sources_modified": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("world", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    try:
        data = analyze(args.world)
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        print(json.dumps({k: v for k, v in data.items()
                          if k not in ("all_species", "large_frame_declarations")},
                         indent=2))
    except (OSError, ValueError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
