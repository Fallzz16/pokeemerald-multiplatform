#!/usr/bin/env python3
"""Experimental, opt-in LZ10 per-frame GROUDON pilot for disposable World GBA build.

Reads the 6 genuine 2048-byte 4bpp frames from an already linked baseline .gba.
Emits compressed ROM-resident u32 arrays, preserving the original frame count,
frame size, OAM allocation, palette, and animation command table. In the native
sprite copy queue a single high-bit request discriminator dispatches a BIOS
LZ77UnCompVram() *inside the existing sprite-copy processing path*.
No global OW_GFX_COMPRESS toggle, no save modifications, no source assets edited.

CAUTION: each decompression costs CPU during sprite-copy processing, currently
called in VBlank; this is an EXPERIMENT, not release-approved without cycles,
frame pacing and visible target-species testing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from overworld_payload_experiments import lz10_encode, lz10_decode

IMAGE_NAME = "gObjectEventPic_Groudon"
FRAME_COUNT = 6
FRAME_BYTES = 2048
SIZE = FRAME_COUNT * FRAME_BYTES
ROM_BASE = 0x08000000
ROM_BYTES = 32 * 1024 * 1024
FRAME_PREFIX = "sGWGroudonLzFrame"
SPRITE_RELATIVE_MARKER = 2
REQUEST_COMPRESSED_FLAG = 0x8000

ANIM_ORIGINAL = """#if P_FAMILY_GROUDON
static const struct SpriteFrameImage sPicTable_Groudon[] = {
    overworld_ascending_frames(gObjectEventPic_Groudon, 8, 8),
};"""
SPRITE_COPY_ORIGINAL = """            CpuCopy16(sSpriteCopyRequests[i].src, sSpriteCopyRequests[i].dest, sSpriteCopyRequests[i].size);"""
SPRITE_COPY_NEW = """            // Experimental Grand World per-frame LZ10: preserve VBlank queue ordering.
            if (sSpriteCopyRequests[i].size & 0x8000)
                LZ77UnCompVram((const u32 *)sSpriteCopyRequests[i].src, sSpriteCopyRequests[i].dest);
            else
                CpuCopy16(sSpriteCopyRequests[i].src, sSpriteCopyRequests[i].dest, sSpriteCopyRequests[i].size);"""
REQUEST_ORIGINAL = """        if (!images[0].relativeFrames)
        {
            sSpriteCopyRequests[sSpriteCopyRequestCount].src = images[index].data;
            sSpriteCopyRequests[sSpriteCopyRequestCount].size = images[index].size;
        }"""
REQUEST_NEW = """        // 2 is an opt-in marker only for per-frame, BIOS-LZ10 encoded art.
        // .size still means UNCOMPRESSED frame bytes (normal OBJ tile budget).
        if (images[0].relativeFrames == 2)
        {
            sSpriteCopyRequests[sSpriteCopyRequestCount].src = images[index].data;
            sSpriteCopyRequests[sSpriteCopyRequestCount].size = images[index].size | 0x8000;
        }
        else if (!images[0].relativeFrames)
        {
            sSpriteCopyRequests[sSpriteCopyRequestCount].src = images[index].data;
            sSpriteCopyRequests[sSpriteCopyRequestCount].size = images[index].size;
        }"""


def single_replace(src, original, replacement, label):
    if src.count(original) != 1 or original == replacement:
        raise ValueError(f"FAIL CLOSED: unexpected pinned World anchor: {label}")
    return src.replace(original, replacement, 1)


def locate_original(nm_text, rom):
    if len(rom) != ROM_BYTES or rom[0xAC:0xB0] != b"BPEE":
        raise ValueError("FAIL CLOSED: need real 32MiB BPEE World ROM")
    matches = re.findall(
        rf"(?m)^([0-9a-fA-F]{{8}})\s+([0-9a-fA-F]+)\s+[A-Za-z]\s+{IMAGE_NAME}$",
        nm_text,
    )
    if len(matches) != 1:
        raise ValueError(f"FAIL CLOSED: expected exactly one {IMAGE_NAME} in linked ELF")
    addr, size = (int(v, 16) for v in matches[0])
    if size != SIZE or not ROM_BASE <= addr < ROM_BASE+ROM_BYTES-SIZE:
        raise ValueError(f"FAIL CLOSED: Groudon 64x64 x6 graphics changed: {matches[0]}")
    off = addr - ROM_BASE
    return [rom[off+i*FRAME_BYTES:off+(i+1)*FRAME_BYTES] for i in range(FRAME_COUNT)]


def make_header(encoded):
    lines = [
        "/* Auto-generated ONLY for disposable Grand World test build.",
        " * Exactly six 64x64 4bpp Groudon sprite frames, stored as BIOS LZ10.",
        " * Original copyrighted pixel bytes remain unmodified/lossless.",
        " * Not the whole-sheet OW_GFX_COMPRESS mode. */",
    ]
    for i, value in enumerate(encoded):
        padded = value + bytes((-len(value)) % 4)
        words = struct.unpack("<" + "I"*(len(padded)//4), padded)
        lines.append(f"static const u32 {FRAME_PREFIX}{i}[] = {{")
        for offset in range(0, len(words), 8):
            lines.append("    " + ", ".join(f"0x{w:08X}" for w in words[offset:offset+8]) + ",")
        lines.append("};")
    return "\n".join(lines)+"\n"


def prepare(world, nm_text, rom):
    world = Path(world)
    if not (world/"Makefile").is_file():
        raise ValueError("FAIL CLOSED: missing complete pinned World checkout")
    owconf = (world/"include/config/overworld.h").read_text(encoding="utf-8")
    if not re.search(r"(?m)^#define OW_GFX_COMPRESS\s+FALSE\b", owconf):
        raise ValueError("FAIL CLOSED: whole-sheet compression must remain disabled")
    frames = locate_original(nm_text, rom)
    # BIOS LZ77UnCompVram writes halfwords: offset 1 is not VRAM-safe.
    compressed = [lz10_encode(frame, min_distance=2) for frame in frames]
    for raw, coded in zip(frames, compressed):
        if lz10_decode(coded, min_distance=2) != raw:
            raise ValueError("FAIL CLOSED: frame LZ10 roundtrip mismatch")
        if len(coded) >= len(raw):
            raise ValueError("FAIL CLOSED: selected Groudon frame not compressible")

    table_path = world/"src/data/object_events/object_event_pic_tables_followers.h"
    sprite_path = world/"src/sprite.c"
    table = table_path.read_text(encoding="utf-8")
    sprite = sprite_path.read_text(encoding="utf-8")
    source_marker = "\n".join(
        f"    {{.data = {FRAME_PREFIX}{i}, .size = {FRAME_BYTES}, .relativeFrames = {SPRITE_RELATIVE_MARKER}}},"
        for i in range(FRAME_COUNT)
    )
    table_new = single_replace(table, ANIM_ORIGINAL,
        '#if P_FAMILY_GROUDON\n'
        '#include "data/object_events/grandworld_groudon_frame_lz10.h"\n'
        'static const struct SpriteFrameImage sPicTable_Groudon[] = {\n'
        + source_marker + '\n};',
        "Groudon 6-frame 64x64 sprite table")
    sprite_new = single_replace(sprite, '#include "sprite.h"\n',
        '#include "sprite.h"\n#include "gba/syscall.h"\n', "BIOS syscall declarations")
    sprite_new = single_replace(sprite_new, SPRITE_COPY_ORIGINAL,
                                SPRITE_COPY_NEW, "queued sprite copy loop")
    sprite_new = single_replace(sprite_new, REQUEST_ORIGINAL,
                                REQUEST_NEW, "sprite frame request")
    header_path = world/"src/data/object_events/grandworld_groudon_frame_lz10.h"
    if header_path.exists():
        raise ValueError("FAIL CLOSED: generated pilot header already exists")

    report = {
        "candidate": "Groudon normal 64x64 overworld only",
        "input_rom_sha256": hashlib.sha256(rom).hexdigest(),
        "raw_frames": FRAME_COUNT,
        "uncompressed_frame_bytes": FRAME_BYTES,
        "raw_total_bytes": SIZE,
        "compressed_frame_bytes": [len(x) for x in compressed],
        "compressed_padded_total_bytes": sum((len(x)+3)&~3 for x in compressed),
        "candidate_raw_byte_saving_before_code_overhead": SIZE - sum((len(x)+3)&~3 for x in compressed),
        "all_frames_lossless_roundtrip": True,
        "original_frame_sha256": [hashlib.sha256(f).hexdigest() for f in frames],
        "frame_endianness": "little",
        "min_lz10_backref_distance": 2,
        "runtime": "LZ77UnCompVram in existing queued sprite copy process",
        "graphic_frame_dimension": "64x64",
        "whole_sheet_compression": False,
        "save_or_pokemon_stats_changed": False,
        "vblank_cycle_cost_measured": False,
        "target_species_onscreen_tested": False,
        "actual_rom_bytes_saved": None,
        "merge_approved": False,
    }
    updates = [(table_path, table_new), (sprite_path, sprite_new),
               (header_path, make_header(compressed))]
    return report, updates


def apply(world, nm_text, rom, *, write=False):
    report, updates = prepare(world, nm_text, rom)
    if write:
        for path, content in updates:
            path.write_text(content, encoding="utf-8")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("world",type=Path)
    p.add_argument("--rom",type=Path,required=True)
    p.add_argument("--symbols",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--apply", action="store_true")
    args=p.parse_args()
    try:
        d=apply(args.world, args.symbols.read_text(encoding="utf-8"),
                args.rom.read_bytes(),write=args.apply)
        args.output.write_text(json.dumps(d,indent=2)+"\n", encoding="utf-8")
        print(json.dumps(d, indent=2))
    except (OSError,ValueError) as e:
        sys.exit(str(e))


if __name__=="__main__":
    main()
