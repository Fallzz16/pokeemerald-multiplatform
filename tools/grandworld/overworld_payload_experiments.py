#!/usr/bin/env python3
"""Read-only exact byte scan of linked GBA overworld art and reversible LZ10 pilot.

Input is the actual linked ARM/GBA .gba and the same ELF's nm -S listing.
GBA ROM addresses begin at 0x08000000, not at filesystem PNG offsets.
This script NEVER modifies the ROM, art, save files or native sprite loader.
Compression estimates EXCLUDE any prospective decoder/copy/CPU/VRAM costs.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

ROM_BASE = 0x08000000
ROM_SIZE = 32 * 1024 * 1024
PATTERN = re.compile(
    r"^\s*([0-9a-fA-F]{8})\s+([0-9a-fA-F]+)\s+([A-Za-z])\s+(gObjectEventPic_[A-Za-z0-9_]+)\s*$"
)
# LZ10 encodes 3..18-byte matches up to 4096 bytes backward; flags 8/token.
WINDOW = 4096
MAX_MATCH = 18


def lz10_encode(data):
    """Greedy BIOS LZ10 packetizer; not claimed optimal for production."""
    data = bytes(data)  # robust for mutable ROM buffers in instrumentation
    if len(data) > 0xFFFFFF:
        raise ValueError("LZ10 header only allows 24-bit uncompressed length")
    result = bytearray(bytes((0x10, len(data) & 255,
                              len(data) >> 8 & 255, len(data) >> 16 & 255)))
    # Keep a short newest-first chain per 3-byte prefix (bounded CPU cost).
    positions = defaultdict(list)
    at = 0
    while at < len(data):
        flag_position = len(result)
        result.append(0)
        flags = 0
        for bit in range(8):
            if at >= len(data):
                break
            best_len = 0
            best_distance = 0
            if at + 2 < len(data):
                key = data[at:at+3]
                candidates = positions.get(key, ())
                for position in reversed(candidates[-12:]):
                    distance = at - position
                    if not 1 <= distance <= WINDOW:
                        continue
                    length = 3
                    limit = min(MAX_MATCH, len(data) - at)
                    while length < limit and data[position+length] == data[at+length]:
                        length += 1
                    if length > best_len:
                        best_len, best_distance = length, distance
                        if length == limit:
                            break
            if best_len >= 3:
                flags |= 1 << (7 - bit)
                offset = best_distance - 1
                result.extend(((best_len-3) << 4 | (offset >> 8), offset & 255))
                step = best_len
            else:
                result.append(data[at])
                step = 1
            for i in range(step):
                p = at + i
                if p + 2 < len(data):
                    key = data[p:p+3]
                    positions[key].append(p)
                    # Bound cache / avoid stale dictionary growth.
                    if len(positions[key]) > 28:
                        del positions[key][:-16]
            at += step
        result[flag_position] = flags
    return bytes(result)


def lz10_decode(encoded):
    if len(encoded) < 4 or encoded[0] != 0x10:
        raise ValueError("invalid LZ10 header")
    size = int.from_bytes(encoded[1:4], "little")
    out = bytearray()
    pos = 4
    while len(out) < size:
        if pos >= len(encoded):
            raise ValueError("truncated LZ10 flag byte")
        flags = encoded[pos]
        pos += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if flags & (1 << (7 - bit)):
                if pos + 2 > len(encoded):
                    raise ValueError("truncated LZ10 back-reference")
                n, low = encoded[pos], encoded[pos+1]
                pos += 2
                length = (n >> 4) + 3
                distance = (((n & 15) << 8) | low) + 1
                if distance > len(out) or len(out) + length > size:
                    raise ValueError("invalid LZ10 back-reference")
                for _ in range(length):
                    out.append(out[-distance])
            else:
                if pos >= len(encoded):
                    raise ValueError("truncated LZ10 literal")
                out.append(encoded[pos])
                pos += 1
    if pos != len(encoded):
        raise ValueError("trailing LZ10 bytes")
    return bytes(out)


def symbols(nm_text, rom):
    found = []
    known = set()
    for line in nm_text.splitlines():
        match = PATTERN.fullmatch(line)
        if not match:
            continue
        address = int(match[1], 16)
        size = int(match[2], 16)
        kind, name = match[3], match[4]
        # Ignore similarly named RAM/BSS/debug symbols; this tool only
        # inspects actual ROM-resident read-only sprite arrays.
        if kind.upper() not in ("R", "D"):
            continue
        offset = address - ROM_BASE
        if not 0 <= offset < len(rom) or not 0 < size <= len(rom)-offset:
            raise ValueError(f"ELF graphic symbol outside GBA image: {name}")
        if name in known:
            raise ValueError(f"duplicate symbol name: {name}")
        known.add(name)
        found.append({"name": name, "address": address,
                      "size": size, "kind": kind,
                      "sha256": hashlib.sha256(rom[offset:offset+size]).hexdigest()})
    if not found:
        raise ValueError("no linked gObjectEventPic symbols found in ARM nm")
    return found


def scan(nm_text, rom, *, pilot_limit=24):
    if len(rom) != ROM_SIZE or rom[0xAC:0xB0] != b"BPEE":
        raise ValueError("expected authentic 32MiB GBA cart with BPEE game code")
    records = symbols(nm_text, rom)
    by_addr = defaultdict(list)
    for record in records:
        by_addr[(record["address"], record["size"])].append(record)
    unique = [v[0] for v in by_addr.values()]
    # SHA alone is never equality proof: double-check actual bytes.
    by_digest = defaultdict(list)
    for record in unique:
        by_digest[(record["size"], record["sha256"])].append(record)
    duplicates = []
    for group in by_digest.values():
        if len(group) < 2:
            continue
        first = group[0]
        start = first["address"] - ROM_BASE
        original = rom[start:start+first["size"]]
        if all(rom[r["address"]-ROM_BASE:r["address"]-ROM_BASE+r["size"]]
               == original for r in group[1:]):
            duplicates.append({
                "symbol_names": sorted(r["name"] for r in group),
                "bytes_per_symbol": first["size"],
                "max_potential_rom_saving": first["size"] * (len(group)-1),
                "validated_equal_bytes": True,
            })
    duplicates.sort(key=lambda x: (-x["max_potential_rom_saving"], x["symbol_names"]))
    total_potential = sum(x["max_potential_rom_saving"] for x in duplicates)
    # Select a fixed set of largest unique arrays. No extrapolation to others.
    pilot = sorted(unique, key=lambda x: (-x["size"], x["name"]))[:pilot_limit]
    measured = []
    for record in pilot:
        offset = record["address"] - ROM_BASE
        original = rom[offset:offset+record["size"]]
        enc = lz10_encode(original)
        if lz10_decode(enc) != original:
            raise ValueError("LZ10 round-trip failed for " + record["name"])
        measured.append({
            "symbol": record["name"],
            "raw_bytes": len(original),
            "lz10_bytes": len(enc),
            "candidate_difference_bytes": len(original) - len(enc),
            "sha256_original": record["sha256"],
            "round_trip_exact": True,
        })
    return {
        "kind": "read_only_linked_gba_exact_overworld_payload_investigation",
        "rom_sha256": hashlib.sha256(rom).hexdigest(),
        "symbols_scanned": len(records),
        "unique_linked_addresses": len(unique),
        "linked_bytes_in_unique_sprite_symbols": sum(x["size"] for x in unique),
        "exact_duplicate_groups": len(duplicates),
        "exact_duplicate_potential_upper_bound_bytes": total_potential,
        "exact_duplicate_groups_detail": duplicates[:100],
        "duplicate_detail_truncated": len(duplicates) > 100,
        "lz10_pilot_largest_symbols": measured,
        "lz10_pilot_symbol_count": len(measured),
        "lz10_pilot_raw_bytes": sum(x["raw_bytes"] for x in measured),
        "lz10_pilot_candidate_encoded_bytes": sum(x["lz10_bytes"] for x in measured),
        "lz10_pilot_roundtrip_verified": True,
        "notes": [
            "Only whole-array exact matches; a potential upper bound is not linker savings",
            "LZ10 pilot is reversible, but runtime loader not modified or validated",
            "LZ10 pilot works on linked image array bytes, not guaranteed animation-frame boundaries",
            "Any runtime compressor must preserve original per-frame OBJ allocation and palette semantics",
            "No benchmarks of FPS/cycles/DMA, audio or save compatibility by this script",
        ],
        "actual_rom_bytes_saved": 0,
        "gameplay_changed": False,
        "ready_for_merge": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--symbols", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pilot-limit", type=int, default=24)
    args = parser.parse_args()
    if not 0 <= args.pilot_limit <= 64:
        parser.error("--pilot-limit out of safe bounds 0..64")
    try:
        result = scan(args.symbols.read_text(encoding="utf-8"),
                      args.rom.read_bytes(), pilot_limit=args.pilot_limit)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items()
                          if k not in ("exact_duplicate_groups_detail",
                                      "lz10_pilot_largest_symbols")}, indent=2))
        for group in result["exact_duplicate_groups_detail"][:10]:
            print("EXACT_DUP", group["max_potential_rom_saving"], group["symbol_names"])
        for pilot in result["lz10_pilot_largest_symbols"][:10]:
            print("LZ10_PILOT", pilot["symbol"], pilot["raw_bytes"],
                  pilot["lz10_bytes"], pilot["candidate_difference_bytes"])
    except (OSError, ValueError) as exc:
        sys.exit("FAIL CLOSED: " + str(exc))


if __name__ == "__main__":
    main()
