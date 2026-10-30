#!/usr/bin/env python3
"""Audit ROM-resident graphic symbols in an actual linked ARM/GBA ELF.

This is not a projection from PNG source sizes or the padded GBA image.
arm-none-eabi-nm -S gives genuine link-time symbols, with some overlapping
aliases and incomplete coverage of non-symbol-backed data.
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROM_BASE = 0x08000000
ROM_END = ROM_BASE + 32 * 1024 * 1024
SYM = re.compile(r"^\s*([0-9a-fA-F]{8})\s+([0-9a-fA-F]+)\s+([A-Za-z])\s+(\S+)\s*$")
CATEGORIES = {
    "overworld_frames": ("gObjectEventPic_",),
    "overworld_palette": ("gOverworldPalette_",),
    "overworld_shiny_palette": ("gShinyOverworldPalette_",),
    "mon_front_battle": ("gMonFrontPic_",),
    "mon_back_battle": ("gMonBackPic_",),
    "mon_shiny_battle_palette": ("gMonShinyPalette_",),
    "mon_battle_palette": ("gMonPalette_",),
    "mon_icon": ("gMonIcon_",),
}


def classify(name):
    for category, prefixes in CATEGORIES.items():
        if name.startswith(prefixes):
            return category
    return None


def analyze(content):
    records = []
    for line in content.splitlines():
        m = SYM.fullmatch(line)
        if not m:
            continue
        address, size, kind, name = m.groups()
        address, size = int(address, 16), int(size, 16)
        if not (ROM_BASE <= address < ROM_END) or size <= 0 or address + size > ROM_END:
            continue
        category = classify(name)
        if category:
            records.append({"name": name, "category": category,
                            "address": address, "size": size, "kind": kind})
    if not records:
        raise ValueError("FAIL CLOSED: no linked ROM graphic symbols in ELF nm data")
    unique_allocations = {}
    aliases = []
    for item in sorted(records, key=lambda r: r["name"]):
        key = (item["address"], item["size"])
        if key in unique_allocations:
            aliases.append({"name": item["name"],
                            "same_allocation_as": unique_allocations[key]["name"],
                            "size": item["size"]})
        else:
            unique_allocations[key] = item
    unique = list(unique_allocations.values())
    size_by_category = {}
    count_by_category = {}
    for row in unique:
        key = row["category"]
        size_by_category[key] = size_by_category.get(key, 0) + row["size"]
        count_by_category[key] = count_by_category.get(key, 0) + 1
    return {
        "kind": "linked_arm_gba_graphic_symbols_source_of_truth_nm_size",
        "scope": "measured linker-visible ROM graphic symbols, NOT every graphic asset",
        "category_bytes": dict(sorted(size_by_category.items())),
        "category_symbol_counts": dict(sorted(count_by_category.items())),
        "total_unique_classified_symbol_bytes": sum(x["size"] for x in unique),
        "classified_symbols_seen": len(records),
        "unique_allocations": len(unique),
        "alias_symbols_excluded": aliases[:80],
        "all_aliases_included": len(aliases) <= 80,
        "largest_rom_graphic_symbols": sorted(unique, key=lambda x: (-x["size"], x["name"]))[:100],
        "actual_rom_bytes_saved": 0,
        "complete_rom_asset_coverage": False,
        "gameplay_performance_measured": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    try:
        d = analyze(args.symbols.read_text(encoding="utf-8", errors="replace"))
        args.output.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in d.items()
                          if k not in ("largest_rom_graphic_symbols", "alias_symbols_excluded")},
                         indent=2))
    except (OSError, ValueError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
