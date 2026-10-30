#!/usr/bin/env python3
"""Move the proven Groudon 2KiB per-frame LZ10 decode OUT of VBlank.

Patch only a disposable PKMN-World checkout after apply_groudon_frame_lz10.py.
Four distinct EWRAM 2KiB slots back requests queued for one VBlank. Each
request owns its slot until ProcessSpriteCopyRequests / ClearSpriteCopyRequests
ends. This deliberately avoids reusing a single scratch buffer for multiple
simultaneous sprite copies. If no slot remains (or request is from VBlank),
fall back to the previously proven BIOS VRAM decode, preserving every frame.

NOT a global compression change or permission to ship before runtime QA.
"""
import argparse
import json
from pathlib import Path
import sys
from apply_groudon_frame_lz10 import REQUEST_NEW, SPRITE_COPY_NEW

SLOTS = 4
FRAME_SIZE = 2048
EW_STATIC_ALLOWANCE = SLOTS * FRAME_SIZE + 64

DECLARE_ORIGINAL = "EWRAM_DATA static u8 sSpriteCopyRequestCount = 0;"
DECLARE_NEW = DECLARE_ORIGINAL + """
// Experimental Grand World LZ10 outside-VBlank staging: four independent
// 2KiB slots, preserved until copy queue consumed or cancelled.
#define GW_GROUDON_STAGING_SLOTS 4
EWRAM_DATA static u32 sGWGroudonStaging[GW_GROUDON_STAGING_SLOTS][512] = {0};
EWRAM_DATA static u8 sGWGroudonStagedSlots = 0;
EWRAM_DATA u32 gGWGroudonStagedRequests = 0;
EWRAM_DATA u32 gGWGroudonStagingFallbacks = 0;
EWRAM_DATA u32 gGWGroudonRequestsInVBlank = 0;
"""
REQUEST_STAGED = """        // Original relativeFrames=2 marks exactly the tested per-frame LZ10.
        // Each queued transfer owns a different EWRAM source until VBlank.
        if (images[0].relativeFrames == 2)
        {
            if (images[index].size == 2048
             && sGWGroudonStagedSlots < GW_GROUDON_STAGING_SLOTS
             && REG_VCOUNT < DISPLAY_HEIGHT)
            {
                u8 slot = sGWGroudonStagedSlots++;
                LZ77UnCompWram((const u32 *)images[index].data, sGWGroudonStaging[slot]);
                sSpriteCopyRequests[sSpriteCopyRequestCount].src = (const u8 *)sGWGroudonStaging[slot];
                sSpriteCopyRequests[sSpriteCopyRequestCount].size = images[index].size;
                gGWGroudonStagedRequests++;
            }
            else
            {
                // No overwrite/no dropped animation: use the original,
                // proven VRAM BIOS path if all four buffers are occupied.
                if (REG_VCOUNT >= DISPLAY_HEIGHT)
                    gGWGroudonRequestsInVBlank++;
                gGWGroudonStagingFallbacks++;
                sSpriteCopyRequests[sSpriteCopyRequestCount].src = images[index].data;
                sSpriteCopyRequests[sSpriteCopyRequestCount].size = images[index].size | 0x8000;
            }
        }
        else if (!images[0].relativeFrames)
        {
            sSpriteCopyRequests[sSpriteCopyRequestCount].src = images[index].data;
            sSpriteCopyRequests[sSpriteCopyRequestCount].size = images[index].size;
        }"""
CLEAR_ORIGINAL = """    sShouldProcessSpriteCopyRequests = FALSE;
    sSpriteCopyRequestCount = 0;"""
CLEAR_STAGED = """    sShouldProcessSpriteCopyRequests = FALSE;
    sSpriteCopyRequestCount = 0;
    // Cancelled transfers must release their queued EWRAM sources.
    sGWGroudonStagedSlots = 0;"""
PROCESS_ORIGINAL = """        sShouldProcessSpriteCopyRequests = FALSE;
    }
}

void RequestSpriteFrameImageCopy"""
PROCESS_STAGED = """        sShouldProcessSpriteCopyRequests = FALSE;
        // All EWRAM staging pointers have been consumed, including compacted
        // or discarded entries. Safe to allocate from slot zero next frame.
        sGWGroudonStagedSlots = 0;
    }
}

void RequestSpriteFrameImageCopy"""
COMPACT_ORIGINAL = """            if (request->dest >= last || request->dest + request->size <= first)
                sSpriteCopyRequests[kept++] = *request;"""
COMPACT_STAGED = """            // The high bit marks the original BIOS VRAM fallback, not length.
            // Mask it before checking whether sprite tiles were reclaimed.
            u16 actualBytes = request->size & 0x7FFF;
            if (request->dest >= last || request->dest + actualBytes <= first)
                sSpriteCopyRequests[kept++] = *request;"""
SYMBOL_ORIGINAL = '    "sSpriteTileAllocBitmap", "gReservedSpriteTileCount",\n'
SYMBOL_STAGED = SYMBOL_ORIGINAL + '    "gGWGroudonStagedRequests", "gGWGroudonStagingFallbacks", "gGWGroudonRequestsInVBlank",\n'


def only_once(source, old, new, name):
    if source.count(old) != 1:
        raise ValueError("FAIL CLOSED: unexpected pinned World patch anchor: " + name)
    return source.replace(old, new, 1)


def stage(world, *, write=False):
    world = Path(world)
    sprite = world / "src/sprite.c"
    generator = world / "test/overworld/GenLuaSymbols.py"
    if not (world/"Makefile").is_file():
        raise ValueError("FAIL CLOSED: incomplete disposable World checkout")
    src = sprite.read_text(encoding="utf-8")
    symbols = generator.read_text(encoding="utf-8")
    # All anchors checked before writing, with no attempt to mutate original art.
    src = only_once(src, DECLARE_ORIGINAL, DECLARE_NEW, "stage declarations")
    src = only_once(src, REQUEST_NEW, REQUEST_STAGED, "compressed request path")
    src = only_once(src, CLEAR_ORIGINAL, CLEAR_STAGED, "clear cancelled queue")
    src = only_once(src, PROCESS_ORIGINAL, PROCESS_STAGED, "reset after VBlank")
    src = only_once(src, COMPACT_ORIGINAL, COMPACT_STAGED, "reclaimed sprites queue")
    symbols = only_once(symbols, SYMBOL_ORIGINAL, SYMBOL_STAGED,
                        "only CI exported counters")
    if src.count(SPRITE_COPY_NEW) != 1:
        raise ValueError("FAIL CLOSED: must retain proven fallback VRAM decoder")
    if "LZ77UnCompWram" not in src or "LZ77UnCompVram" not in src:
        raise ValueError("FAIL CLOSED: missing BIOS WRAM or fallback decode")
    if write:
        sprite.write_text(src, encoding="utf-8")
        generator.write_text(symbols, encoding="utf-8")
    return {
        "kind": "experimental_groudon_wram_staging_queue",
        "slots": SLOTS,
        "bytes_per_slot": FRAME_SIZE,
        "staged_total_bytes": SLOTS*FRAME_SIZE,
        "maximum_static_EWRAM_increase_allowed": EW_STATIC_ALLOWANCE,
        "queue_sources_lifetime": "until native copy queue consumed/cancelled",
        "overflow": "original BIOS LZ77UnCompVram fallback, never reuse source slot",
        "supports_other_pokemon": False,
        "gba_rom_modified": False,
        "save_format_modified": False,
        "release_ready": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("world", type=Path)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        report = stage(args.world, write=args.apply)
        payload = json.dumps(report, indent=2) + "\n"
        if args.output:
            args.output.write_text(payload, encoding="utf-8")
        print(payload, end="")
    except (OSError, ValueError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
