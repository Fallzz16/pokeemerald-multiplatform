#!/usr/bin/env python3
"""Non-destructive GBA ROM / referenced LZ77 audit for M8.

Only reports plausible *four-byte-aligned and pointer-referenced* GBA BIOS
LZ77 streams. This is not an exhaustive asset extractor, nor an FPS benchmark.
No ROM bytes or decompressed assets are included in output.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

ROM_BASE = 0x08000000
ALLOWED_SIZES = {1 << n for n in range(20, 26)}  # 1–32 MiB
MAX_UNCOMPRESSED = 4 * 1024 * 1024
MIN_UNCOMPRESSED = 32


def validate_gba_rom(data):
    if len(data) not in ALLOWED_SIZES:
        raise ValueError("Expected a complete 1/2/4/8/16/32 MiB GBA ROM")
    if data[0xB2] != 0x96:
        raise ValueError("Invalid GBA fixed header byte")
    if (sum(data[0xA0:0xBD]) + data[0xBD] + 0x19) % 256:
        raise ValueError("Invalid GBA header checksum")


def lz77_span(data, start):
    """Return stream byte count if its full LZ77 control stream is valid.

    This validates back-references/declared length without materializing assets.
    """
    end = len(data)
    if start + 4 > end or data[start] != 0x10:
        return None
    out_len = int.from_bytes(data[start + 1:start + 4], "little")
    if not MIN_UNCOMPRESSED <= out_len <= MAX_UNCOMPRESSED:
        return None
    produced, pos = 0, start + 4
    while produced < out_len:
        if pos >= end:
            return None
        flags = data[pos]
        pos += 1
        for shift in range(7, -1, -1):
            if produced == out_len:
                break
            if flags & (1 << shift):
                if pos + 2 > end:
                    return None
                b1, b2 = data[pos], data[pos + 1]
                pos += 2
                count = (b1 >> 4) + 3
                distance = ((b1 & 0x0F) << 8) + b2 + 1
                if distance > produced or produced + count > out_len:
                    return None
                produced += count
            else:
                if pos >= end:
                    return None
                pos += 1
                produced += 1
    return pos - start


def audit(data):
    validate_gba_rom(data)
    # Count aligned pointer fields; exclude Thumb function addresses.
    counts = Counter()
    for offset in range(0, len(data) - 3, 4):
        addr = struct.unpack_from("<I", data, offset)[0]
        # The GBA ROM is mirrored at 0x08000000, 0x0A000000 and 0x0C000000.
        # Masking 25 bits preserves addresses across the full 32 MiB window.
        if addr & 0xFE000000 not in (0x08000000, 0x0A000000, 0x0C000000):
            continue
        target = addr & 0x01FFFFFF
        if 0 <= target < len(data) - 4 and target % 4 == 0 and data[target] == 0x10:
            counts[target] += 1
    records = []
    for start, refs in counts.items():
        used = lz77_span(data, start)
        if used is None:
            continue
        expanded = int.from_bytes(data[start + 1:start + 4], "little")
        records.append((start, used, expanded, refs))
    records.sort()
    stored = sum(rec[1] for rec in records)
    expanded = sum(rec[2] for rec in records)
    biggest = sorted(records, key=lambda rec: rec[2], reverse=True)[:8]
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "rom_bytes": len(data),
        "game_code": data[0xAC:0xB0].decode("ascii", errors="replace"),
        "method": "4-byte-aligned ROM pointers to fully validated GBA LZ77 type 0x10 streams",
        "referenced_lz77_streams": len(records),
        "referencing_pointer_fields": sum(rec[3] for rec in records),
        "referenced_stream_stored_bytes": stored,
        "referenced_stream_expanded_bytes": expanded,
        "expansion_ratio": round(expanded / stored, 3) if stored else None,
        "largest_streams": [
            {"rom_offset": f"0x{start:08X}", "stored_bytes": used,
             "expanded_bytes": out_size, "pointer_references": refs}
            for start, used, out_size, refs in biggest
        ],
        "fps_or_cycles_measured": False,
        "exhaustive_resource_inventory": False,
        "warnings": [
            "Does not include unreferenced or non-aligned LZ77 streams, RLE, Huffman, tiles or uncompressed resources.",
            "Pointers and plausible compressed streams do not prove a stream is rendered during gameplay.",
            "Compression can save ROM while increasing CPU/VRAM pressure; do not enable globally from this metric.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path, help="Existing GBA ROM; read only")
    parser.add_argument("--output", type=Path, help="Save metrics only, never ROM data")
    parser.add_argument("--compare", type=Path, help="Optional second GBA ROM to compare; read-only")
    args = parser.parse_args()
    result = audit(args.rom.read_bytes())
    if args.compare:
        other = audit(args.compare.read_bytes())
        if result["game_code"] != other["game_code"]:
            raise ValueError("Cannot compare different GBA game codes")
        fields = ("referenced_lz77_streams", "referencing_pointer_fields",
                  "referenced_stream_stored_bytes", "referenced_stream_expanded_bytes")
        result["comparison"] = {
            "second_rom_sha256": other["sha256"],
            "second_rom_bytes": other["rom_bytes"],
            "second_rom_summary": {key: other[key] for key in fields},
            "second_minus_first": {key: other[key] - result[key] for key in fields},
            "not_an_fps_measurement": True,
        }
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
