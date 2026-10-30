#!/usr/bin/env python3
"""Replace only diagnostic Groudon BIOS calls with pinned MIT ARM LZ10 decoder.

Apply to disposable World source AFTER apply_groudon_frame_lz10.py and
groudon_cycle_probe_overlay.py. Source assembly is fetched separately from the
MIT-licensed upstream GBA-demo-framework at a pinned full commit SHA; it is
never vendored into Grand World, and upstream copyright headers are retained.
The original compressed data, sprite table, save format, palette, and fallback
of other sprite-copy requests are unchanged.
"""
import argparse
import json
from pathlib import Path
import sys

SYMBOL = "LZ77UnCompWrite16bit"
UPSTREAM_REPO = "HorstBaerbel/GBA-demo-framework"
UPSTREAM_COMMIT = "7f5410055d7fafb002ed7536b9cc45274f3a471b"
UPSTREAM_PATH = "src/compression/lz77_asm.s"
INVOKE = "LZ77UnCompVram((const u32 *)sSpriteCopyRequests[i].src, sSpriteCopyRequests[i].dest);"
REPLACEMENT = SYMBOL + "((const u32 *)sSpriteCopyRequests[i].src, sSpriteCopyRequests[i].dest);"
PROTOTYPE_ANCHOR = '#include "sprite.h"\n'
PROTOTYPE = PROTOTYPE_ANCHOR + (
    "extern void LZ77UnCompWrite16bit(const void *src, void *dst);\n"
)


def patch(world, *, write=False):
    world=Path(world)
    src=world/"src/sprite.c"
    opt=world/"src/gw_fast_lz77.s"
    if not (world/"Makefile").exists() or not opt.is_file():
        raise ValueError("FAIL CLOSED: complete World checkout and optimized MIT assembly required")
    assembly=opt.read_text(encoding="utf-8",errors="replace")
    if (SYMBOL+":" not in assembly or "MIT License" not in assembly):
        raise ValueError("FAIL CLOSED: missing optimized ARM export or MIT license provenance")
    if "swi_LZ77UnCompWrite16bit:" in assembly:
        raise ValueError("FAIL CLOSED: wrong upstream function ABI")
    source=src.read_text(encoding="utf-8")
    if source.count(INVOKE)!=2 or source.count(PROTOTYPE_ANCHOR)!=1:
        raise ValueError("FAIL CLOSED: native Groudon cycle profiler source changed")
    if "CycleCountStart();" not in source or "CycleCountEnd();" not in source:
        raise ValueError("FAIL CLOSED: must preserve real GBA hardware timing")
    changed=source.replace(PROTOTYPE_ANCHOR,PROTOTYPE,1).replace(INVOKE,REPLACEMENT)
    if changed.count(REPLACEMENT)!=2:
        raise ValueError("FAIL CLOSED: unexpected instrumented call count")
    if write:
        src.write_text(changed,encoding="utf-8")
    return {
        "kind":"fast_arm_lz10_alternative_vram_test",
        "codec":"same exact LZ10 bytes as PR109, decoder only changed",
        "upstream_repo":UPSTREAM_REPO,
        "upstream_commit":UPSTREAM_COMMIT,
        "upstream_source":UPSTREAM_PATH,
        "copyright":"MIT original by fleroviux, optimized by Lorenzooone",
        "replacement_call_sites":2,
        "temporary_world_source_only":True,
        "sprites_palettes_save_unchanged":True,
        "speed_win_proved":False,
        "ready_for_master":False,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("world",type=Path)
    p.add_argument("--apply",action="store_true")
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    try:
        d=patch(args.world,write=args.apply)
        text=json.dumps(d,indent=2)+"\n"
        if args.output:
            args.output.write_text(text,encoding="utf-8")
        print(text,end="")
    except (OSError,ValueError) as e:
        sys.exit(str(e))


if __name__=="__main__":
    main()
