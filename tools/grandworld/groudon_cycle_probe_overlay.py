#!/usr/bin/env python3
"""Optional GBA hardware cycle profiler for Groudon LZ10 sprite frames.

Only applies in a throwaway pinned World checkout AFTER the tested PR109 LZ10
patch. Uses World global.h CycleCountStart/End (TM2+TM3 hardware cascade).
This is a TEST BUILD, not release code: the original timer values are not
restored, so never execute the benchmark during link/eReader/timer-sensitive play.
If TM2/3 are active, leave them untouched and decompress normally without a
sample. No save, graphic bytes, or palette is edited.
"""
import argparse
from pathlib import Path
import sys

SRC_ANCHOR = """            if (sSpriteCopyRequests[i].size & 0x8000)
                LZ77UnCompVram((const u32 *)sSpriteCopyRequests[i].src, sSpriteCopyRequests[i].dest);
            else
                CpuCopy16(sSpriteCopyRequests[i].src, sSpriteCopyRequests[i].dest, sSpriteCopyRequests[i].size);"""
SRC_NEW = """            if (sSpriteCopyRequests[i].size & 0x8000)
            {
                // TEST-ONLY profiling: never interrupt a timer owned by link/eReader.
                if ((REG_TM2CNT_H | REG_TM3CNT_H) & TIMER_ENABLE)
                {
                    gGWLZTimerConflicts++;
                    LZ77UnCompVram((const u32 *)sSpriteCopyRequests[i].src, sSpriteCopyRequests[i].dest);
                }
                else
                {
                    u32 cycles;
                    CycleCountStart();
                    LZ77UnCompVram((const u32 *)sSpriteCopyRequests[i].src, sSpriteCopyRequests[i].dest);
                    cycles = CycleCountEnd();
                    gGWLZCopyCount++;
                    gGWLZTotalCycles += cycles;
                    if (cycles > gGWLZPeakCycles)
                        gGWLZPeakCycles = cycles;
                }
            }
            else
                CpuCopy16(sSpriteCopyRequests[i].src, sSpriteCopyRequests[i].dest, sSpriteCopyRequests[i].size);"""
GLOBALS_ANCHOR = "#define MAX_SPRITE_COPY_REQUESTS 64\n"
GLOBALS_NEW = GLOBALS_ANCHOR + """
// Only in CI diagnostic World copy; 16 B EWRAM, NOT in release candidate.
EWRAM_DATA u32 gGWLZCopyCount = 0;
EWRAM_DATA u32 gGWLZTotalCycles = 0;
EWRAM_DATA u32 gGWLZPeakCycles = 0;
EWRAM_DATA u32 gGWLZTimerConflicts = 0;
"""
SYMBOL_ANCHOR = '    "sSpriteTileAllocBitmap", "gReservedSpriteTileCount",\n'
SYMBOL_NEW = SYMBOL_ANCHOR + '    "gGWLZCopyCount", "gGWLZTotalCycles", "gGWLZPeakCycles", "gGWLZTimerConflicts",\n'
QA_MARKER = '  F.finish()\n'
QA_PATCH = """  -- mGBA diagnostic only: hardware Timer2/3 measures BIOS 2KiB LZ10 calls.
  local n=F.r32(S.gGWLZCopyCount)
  local peak=F.r32(S.gGWLZPeakCycles)
  local total=F.r32(S.gGWLZTotalCycles)
  local conflicts=F.r32(S.gGWLZTimerConflicts)
  F.L(string.format("GROUDON_CPU samples=%d peak_cycles=%d total_cycles=%d avg_cycles=%d timer_conflicts=%d",
    n,peak,total,n>0 and total//n or 0,conflicts))
  F.check("Groudon BIOS LZ10 had real hardware cycle samples",n>=3,
    "samples="..n)
  F.check("Groudon LZ10 profiling did not overwrite active game timers",
    conflicts==0,"timer conflicts="..conflicts)
  -- 68 GBA VBlank lines * 1232 cycles/line = 83776 (single decode only).
  -- This is NOT proof of aggregate frame pacing or DMA budget.
  F.check("individual Groudon LZ10 decode fits isolated VBlank window",
    peak>0 and peak<83776,"peak cycles="..peak)
""" + QA_MARKER


def single(src, old, new, label):
    if src.count(old)!=1:
        raise ValueError("FAIL CLOSED: missing/duplicate pinned anchor "+label)
    return src.replace(old,new,1)


def instrument(world, qa_source, *, write=False):
    world=Path(world)
    sprite=world/"src/sprite.c"
    symbols=world/"test/overworld/GenLuaSymbols.py"
    target=world/"test/overworld/lua/GrandWorldGroudonFollowerLZ10.lua"
    source=sprite.read_text(encoding="utf-8")
    gen=symbols.read_text(encoding="utf-8")
    if not "#include \"global.h\"" in source and not '#include "sprite.h"' in source:
        raise ValueError("FAIL CLOSED: expected pinned World C includes")
    src=single(source,SRC_ANCHOR,SRC_NEW,"Groudon LZ10 decode call")
    src=single(src,GLOBALS_ANCHOR,GLOBALS_NEW,"hardware profiling globals")
    gen=single(gen,SYMBOL_ANCHOR,SYMBOL_NEW,"native World Lua symbols")
    qa=single(qa_source,QA_MARKER,QA_PATCH,"Groudon runtime QA finish")
    if target.exists():
        raise ValueError("FAIL CLOSED: target runtime QA already exists")
    updates=[(sprite,src),(symbols,gen),(target,qa)]
    if write:
        for path,content in updates:
            path.write_text(content,encoding="utf-8")
    return {"test_only":True,
            "frame_bytes":2048,
            "hardware":"World CycleCountStart/End Timer2+Timer3",
            "extra_static_ewram_bytes":16,
            "source_files_staged":len(updates),
            "counter_symbols":4,
            "runtime_assertions_added":3,
            "modified_immutable_world_repository":False,
            "ready_for_release":False}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("world",type=Path)
    ap.add_argument("--qa-source",type=Path,required=True)
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()
    try:
        print(instrument(args.world,args.qa_source.read_text(encoding="utf-8"),
                         write=args.apply))
    except (OSError,ValueError) as e:
        sys.exit(str(e))


if __name__=="__main__":
    main()
