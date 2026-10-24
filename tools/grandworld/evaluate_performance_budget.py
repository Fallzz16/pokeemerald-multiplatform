#!/usr/bin/env python3
"""Strict GBA cartridge + linker RAM budget validation (not an FPS benchmark).

Use with the *same* produced ROM and log. Reports numeric headroom in ROM,
EWRAM and IWRAM while refusing a stale/incomplete build transcript.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

LIMITS = {"ROM": 32 * 1024 * 1024, "EWRAM": 256 * 1024, "IWRAM": 32 * 1024}
RESERVES = {"ROM": 1 * 1024 * 1024, "EWRAM": 8 * 1024, "IWRAM": 2 * 1024}
MEMORY_ROW = re.compile(r"^\s*(ROM|EWRAM|IWRAM):\s+(\d+)\s+B(?:\s|$)", re.MULTILINE)


def read_linker_usage(log):
    rows = MEMORY_ROW.findall(log)
    if len(rows) < 3:
        raise ValueError("incomplete GBA linker memory usage output")
    # The last full trio is the final build's report; reject repeated or missing
    # keys so a stray earlier phase cannot forge plausible numbers.
    last = rows[-3:]
    usage = {key: int(value) for key, value in last}
    if set(usage) != set(LIMITS) or len(last) != len(usage):
        raise ValueError("last three linker rows must uniquely cover ROM/EWRAM/IWRAM")
    return usage


def validate_rom(data):
    if len(data) != LIMITS["ROM"]:
        raise ValueError("expected complete 32 MiB padded GBA ROM")
    if data[0xAC:0xB0] != b"BPEE":
        raise ValueError("unexpected game code; not pinned Emerald/World lineage")
    if data[0xB2] != 0x96:
        raise ValueError("invalid fixed byte in GBA header")
    if (sum(data[0xA0:0xBD]) + data[0xBD] + 0x19) % 256:
        raise ValueError("invalid GBA header checksum")
    return hashlib.sha256(data).hexdigest()


def report(rom, log, min_headroom=None):
    min_headroom = dict(RESERVES if min_headroom is None else min_headroom)
    if set(min_headroom) != set(LIMITS):
        raise ValueError("headroom keys must be ROM/EWRAM/IWRAM")
    sha = validate_rom(rom)
    used = read_linker_usage(log)
    free = {key: LIMITS[key] - used[key] for key in LIMITS}
    if any(used[key] <= 0 or used[key] > LIMITS[key] for key in LIMITS):
        raise ValueError(f"linker memory overflow or invalid usage: {used}")
    for key, reserve in min_headroom.items():
        if reserve < 0:
            raise ValueError("negative memory reserve")
        if free[key] < reserve:
            raise ValueError(f"{key} headroom {free[key]} < reserve {reserve}")
    return {
        "rom_sha256": sha,
        "rom_bytes": len(rom),
        "game_code": "BPEE",
        "linker_memory_bytes": used,
        "free_bytes": free,
        "minimum_reserved_bytes": min_headroom,
        "memory_budget_passed": True,
        "fps_measured": False,
        "cpu_cycles_measured": False,
        "gameplay_homologated": False,
        "caveat": "Static memory budget only; OAM occupancy, VRAM pressure and frame time require real mGBA/hardware QA.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("build_log", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = report(args.rom.read_bytes(), args.build_log.read_text(encoding="utf-8"))
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
