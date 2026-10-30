#!/usr/bin/env python3
"""CI-only ARM/GBA stress test: real repeated 2KiB LZ10 calls in one VBlank.

Starting point is PR112's *tested* fast ARM decoder and timer profiler.
This instruments the native ProcessSpriteCopyRequests queue. In stress mode
one actual Groudon follower frame is decoded 2, 3 or 4 times to the SAME
owned OBJ tiles in the SAME queue invocation: this is real GBA CPU traffic,
not a simulation, but it is NOT multiple simultaneously visible Groudon.

All writes are confined to a disposable World checkout. Does not modify M8,
ROM save formats, graphics resources, maps, or the PR112 source branch.
"""
import argparse
import json
from pathlib import Path
import sys

from groudon_cycle_probe_overlay import SRC_NEW as PROFILE_BODY
from groudon_fast_lz77_arm_overlay import INVOKE, REPLACEMENT

OLD_BODY=PROFILE_BODY.replace(INVOKE,REPLACEMENT)
OLD_QUEUE_START="""        u8 i = 0;

        while (sSpriteCopyRequestCount > 0)"""
NEW_QUEUE_START="""        u8 i = 0;
        u32 batchCycles = 0;
        u32 compressedInBatch = 0;
        u32 normalInBatch = 0;
        u8 stressMode = gGWStressExtraCopies > 3 ? 3 : gGWStressExtraCopies;
        u16 startLine = REG_VCOUNT;

        while (sSpriteCopyRequestCount > 0)"""
OLD_QUEUE_END="""        sShouldProcessSpriteCopyRequests = FALSE;
    }
}

void RequestSpriteFrameImageCopy"""
NEW_QUEUE_END="""        // Sums of REAL GBA Timer2+3 timed CPU-copy and ARM LZ10 calls.
        // Excludes other VBlank handlers (OAM/DMA/audio), so NOT full VBlank.
        if (compressedInBatch != 0)
        {
            gGWStressSamples[stressMode]++;
            if (batchCycles > gGWStressPeakBatchCycles[stressMode])
                gGWStressPeakBatchCycles[stressMode] = batchCycles;
            if (batchCycles >= 83776)
                gGWStressOverBudgetBatches[stressMode]++;
            if (REG_VCOUNT < DISPLAY_HEIGHT && startLine >= DISPLAY_HEIGHT)
                gGWStressVblankCrossings[stressMode]++;
        }
        if (compressedInBatch > gGWPeakCompressedInOneBatch)
            gGWPeakCompressedInOneBatch = compressedInBatch;
        if (normalInBatch > gGWPeakNormalInOneBatch)
            gGWPeakNormalInOneBatch = normalInBatch;
        if (batchCycles > gGWPeakMeasuredBatchCycles)
            gGWPeakMeasuredBatchCycles = batchCycles;
        sShouldProcessSpriteCopyRequests = FALSE;
    }
}

void RequestSpriteFrameImageCopy"""
OLD_GLOBAL="#define MAX_SPRITE_COPY_REQUESTS 64\n"
NEW_GLOBAL=OLD_GLOBAL+"""
// CI-only GBA VBlank workload probes; not included in release candidates.
EWRAM_DATA u8 gGWStressExtraCopies = 0;
EWRAM_DATA u32 gGWStressSamples[4] = {0};
EWRAM_DATA u32 gGWStressPeakBatchCycles[4] = {0};
EWRAM_DATA u32 gGWStressOverBudgetBatches[4] = {0};
EWRAM_DATA u32 gGWStressVblankCrossings[4] = {0};
EWRAM_DATA u32 gGWPeakMeasuredBatchCycles = 0;
EWRAM_DATA u32 gGWPeakCompressedInOneBatch = 0;
EWRAM_DATA u32 gGWPeakNormalInOneBatch = 0;
EWRAM_DATA u32 gGWRawTimerSkips = 0; // Do not confuse busy timer with LZ10 contention.
"""
OLD_SYMBOL='    "gGWLZCopyCount", "gGWLZTotalCycles", "gGWLZPeakCycles", "gGWLZTimerConflicts",\n'
NEW_SYMBOL=OLD_SYMBOL+'''    "gGWStressExtraCopies", "gGWStressSamples", "gGWStressPeakBatchCycles",\n    "gGWStressOverBudgetBatches", "gGWStressVblankCrossings",\n    "gGWPeakMeasuredBatchCycles", "gGWPeakCompressedInOneBatch", "gGWPeakNormalInOneBatch", "gGWRawTimerSkips",\n'''

NEW_BODY="""            if (sSpriteCopyRequests[i].size & 0x8000)
            {
                // CI-only repeat the same 2KiB decode into the SAME legal
                // allocated tiles. Last pixels remain byte-identical.
                // This measures N copies in one REAL VBlank, not N sprites.
                if ((REG_TM2CNT_H | REG_TM3CNT_H) & TIMER_ENABLE)
                {
                    gGWLZTimerConflicts++;
                    LZ77UnCompWrite16bit((const u32 *)sSpriteCopyRequests[i].src, sSpriteCopyRequests[i].dest);
                }
                else
                {
                    u8 repeat;
                    for (repeat = 0; repeat <= stressMode; repeat++)
                    {
                        u32 cycles;
                        CycleCountStart();
                        LZ77UnCompWrite16bit((const u32 *)sSpriteCopyRequests[i].src, sSpriteCopyRequests[i].dest);
                        cycles = CycleCountEnd();
                        gGWLZCopyCount++;
                        gGWLZTotalCycles += cycles;
                        batchCycles += cycles;
                        compressedInBatch++;
                        if (cycles > gGWLZPeakCycles)
                            gGWLZPeakCycles = cycles;
                    }
                }
            }
            else
            {
                // Include native raw sprite copies in the CPU queue budget.
                // Timers remain untouched if another game system owns them.
                if ((REG_TM2CNT_H | REG_TM3CNT_H) & TIMER_ENABLE)
                {
                    // Native owners (link/eReader/audio) retain timers.
                    // A skipped raw-copy SAMPLE is not a decoder conflict.
                    gGWRawTimerSkips++;
                    CpuCopy16(sSpriteCopyRequests[i].src, sSpriteCopyRequests[i].dest, sSpriteCopyRequests[i].size);
                }
                else
                {
                    u32 cycles;
                    CycleCountStart();
                    CpuCopy16(sSpriteCopyRequests[i].src, sSpriteCopyRequests[i].dest, sSpriteCopyRequests[i].size);
                    cycles = CycleCountEnd();
                    batchCycles += cycles;
                    normalInBatch++;
                }
            }"""


def replace_once(src, old, new, label):
    if src.count(old)!=1:
        raise ValueError("FAIL CLOSED: pinned World anchor mismatch: "+label)
    return src.replace(old,new,1)


def instrument(world, *, write=False):
    world=Path(world)
    path=world/"src/sprite.c"
    symbols=world/"test/overworld/GenLuaSymbols.py"
    if not (world/"Makefile").is_file():
        raise ValueError("FAIL CLOSED: not a pinned World checkout")
    source=path.read_text(encoding="utf-8")
    gen=symbols.read_text(encoding="utf-8")
    # Validate every source and export anchor prior to modifying anything.
    source=replace_once(source,OLD_BODY,NEW_BODY,"existing timed ARM LZ10 decoder")
    source=replace_once(source,OLD_QUEUE_START,NEW_QUEUE_START,"native sprite copy queue")
    source=replace_once(source,OLD_QUEUE_END,NEW_QUEUE_END,"sprite queue completion")
    source=replace_once(source,OLD_GLOBAL,NEW_GLOBAL,"MAX_SPRITE_COPY_REQUESTS")
    gen=replace_once(gen,OLD_SYMBOL,NEW_SYMBOL,"Lua debug symbol export")
    if "LZ77UnCompWrite16bit" not in source or "LZ77UnCompVram" in NEW_BODY:
        raise ValueError("FAIL CLOSED: fast decoder source unexpectedly changed")
    if write:
        path.write_text(source,encoding="utf-8")
        symbols.write_text(gen,encoding="utf-8")
    return {
        "kind":"test_only_same_destination_arm_lz10_vblank_stress",
        "actual_native_gba_queue":True,
        "stress_frame_copies_per_one_queue": [1,2,3,4],
        "frame_bytes":2048,
        "same_owned_obj_vram_destination":True,
        "different_simultaneously_visible_sprites_tested":False,
        "includes_timed_regular_sprite_copies":True,
        "full_VBlank_cycle_load_measured":False,
        "static_EWRAM_additional_budget_bytes":100,
        "changes_to_saved_games":False,
        "ready_for_master":False,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("world",type=Path)
    p.add_argument("--apply",action="store_true")
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    try:
        result=instrument(a.world,write=a.apply)
        data=json.dumps(result,indent=2)+"\n"
        if a.output:a.output.write_text(data)
        print(data,end="")
    except (OSError,ValueError) as exc:
        sys.exit(str(exc))


if __name__=="__main__":
    main()
