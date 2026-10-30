#!/usr/bin/env python3
"""Fail-closed read-only report for actual mGBA sprite allocation snapshots.

Do not confuse native allocator tile occupancy with ROM size, FPS, VRAM DMA
bandwidth or pixels truly visible. This script makes no source modifications.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

FIELDS = ("used", "free", "largest_free", "free_runs", "reserved",
          "sprites", "palettes", "owe", "follower",
          "palette_duplicate_slots", "palette_duplicate_pairs")
RECORD = re.compile(
    r"\bGRAPHICS_BUDGET stage=([a-z0-9-]+) "
    + r" ".join(rf"{key}=(\d+)" for key in FIELDS)
    + r"(?:\s|$)")
REQUIRED = ("field-before-spawn", "field-after-2400-frames",
            "field-after-real-battle-flee")


def analyze(log):
    entries = []
    for match in RECORD.finditer(log):
        stage, *numbers = match.groups()
        entry = {"stage": stage, **dict(zip(FIELDS, map(int, numbers)))}
        if not 0 <= entry["used"] <= 1024:
            raise ValueError(f"bad allocated tile count: {stage}")
        if entry["used"] + entry["free"] != 1024:
            raise ValueError(f"bad OBJ bitmap size: {stage}")
        if not 0 <= entry["reserved"] <= entry["used"]:
            raise ValueError(f"bad reserved tile count: {stage}")
        if not 0 <= entry["largest_free"] <= entry["free"]:
            raise ValueError(f"bad largest free run: {stage}")
        if not 0 <= entry["free_runs"] <= entry["free"]:
            raise ValueError(f"bad fragmentation count: {stage}")
        if not 0 <= entry["sprites"] <= 64:
            raise ValueError(f"bad active sprite count: {stage}")
        if not 0 <= entry["palettes"] <= 16:
            raise ValueError(f"bad OBJ palette count: {stage}")
        if not 0 <= entry["owe"] <= 4 or entry["follower"] not in (0, 1):
            raise ValueError(f"bad wild/follower count: {stage}")
        max_pairs = entry["palettes"] * (entry["palettes"] - 1) // 2
        if not 0 <= entry["palette_duplicate_slots"] <= max(0, entry["palettes"]-1):
            raise ValueError(f"bad palette duplicate slot count: {stage}")
        if not 0 <= entry["palette_duplicate_pairs"] <= max_pairs:
            raise ValueError(f"bad palette duplicate pair count: {stage}")
        if (entry["palette_duplicate_slots"] == 0) != (entry["palette_duplicate_pairs"] == 0):
            raise ValueError(f"inconsistent palette duplicates: {stage}")
        entries.append(entry)
    if not entries:
        raise ValueError("no native OBJ bitmap snapshots in real mGBA log")
    by_stage = {}
    for e in entries:
        if e["stage"] in by_stage:
            raise ValueError("duplicate budget snapshot: " + e["stage"])
        by_stage[e["stage"]] = e
    missing = set(REQUIRED) - set(by_stage)
    if missing:
        raise ValueError("missing required snapshots: " + ", ".join(sorted(missing)))
    samples = [e for e in entries if e["stage"].startswith("sample-")]
    if not samples:
        raise ValueError("no field-period allocation samples")
    if not any(e["owe"] > 0 for e in samples):
        raise ValueError("no live wild OBJ measured in field allocation samples")
    if not any(e["follower"] for e in entries if e["stage"] != "field-after-real-battle-flee"):
        raise ValueError("no active follower observed in graphics samples")
    return {
        "kind": "real_mgba_obj_vram_allocator_observation",
        "safety": "read_only_ephemeral_build; no graphics or save edits",
        "scope": "Route29 18/18 runtime; cannot infer every map or all GBA graphics",
        "tiles_total": 1024,
        "tile_bytes_4bpp": 32,
        "obj_vram_bytes": 32768,
        "observations": entries,
        "peak_allocated_tiles": max(e["used"] for e in entries),
        "peak_allocated_obj_bytes": max(e["used"] for e in entries) * 32,
        "minimum_free_tiles": min(e["free"] for e in entries),
        "smallest_largest_free_run": min(e["largest_free"] for e in entries),
        "peak_active_sprites": max(e["sprites"] for e in entries),
        "peak_palettes": max(e["palettes"] for e in entries),
        "peak_exact_color_duplicate_palette_slots": max(e["palette_duplicate_slots"] for e in entries),
        "potential_palette_merging_safe": False,
        "measured_fps": False,
        "rom_bytes_saved": 0,
        "ready_for_release": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--rom", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    try:
        result = analyze(args.log.read_text(encoding="utf-8", errors="replace"))
        rom = args.rom.read_bytes()
        if len(rom) != 32 * 1024 * 1024 or rom[0xAC:0xB0] != b"BPEE":
            raise ValueError("not a padded authentic GBA cart image")
        result["rom_sha256"] = hashlib.sha256(rom).hexdigest()
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items()
                          if k != "observations"}, indent=2))
    except (ValueError, OSError) as error:
        sys.exit("FAIL CLOSED: " + str(error))


if __name__ == "__main__":
    main()
