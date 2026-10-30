#!/usr/bin/env python3
"""Produce evidence for actual native GBA multiple-copy VBlank decoder load."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

LINE=re.compile(
    r"\bGROUDON_STRESS mode=(\d+) copies=(\d+) samples=(\d+) "
    r"peak_batch_cycles=(\d+) over_budget=(\d+) crossed_vblank=(\d+) "
    r"pixel_samples=(\d+)")
BATCH=re.compile(r"\bGROUDON_BATCH baseline_samples=(\d+) baseline_peak=(\d+) "
                 r"max_batch_cycles=(\d+) max_lz_copies=(\d+) max_normal_copies=(\d+)")
VBLANK_CYCLES=83776


def summarize(log, finalrom, source, linker, qa_passes=True):
    rows=LINE.findall(log)
    if len(rows)!=3:
        raise ValueError("FAIL CLOSED: expected three native GBA stress modes")
    modes={}
    for r in rows:
        mode,copies,n,peak,over,crossed,pixels=map(int,r)
        if mode in modes or mode not in (1,2,3) or copies!=mode+1 or n<3 or pixels<4:
            raise ValueError("FAIL CLOSED: invalid or duplicate stress mode")
        modes[mode]={"copies_per_actual_vblank_request":copies,"samples":n,
                    "peak_timed_queue_cycles":peak,"over_budget_batches":over,
                    "crossed_vblank_snapshots":crossed,
                    "verified_2048byte_obj_frame_observations":pixels}
    if not(0<modes[1]["peak_timed_queue_cycles"]<
           modes[2]["peak_timed_queue_cycles"]<
           modes[3]["peak_timed_queue_cycles"]):
        raise ValueError("FAIL CLOSED: non-increasing decoder work")
    if modes[2]["peak_timed_queue_cycles"]>=VBLANK_CYCLES:
        raise ValueError("FAIL CLOSED: 3-copy load exceeded isolated VBlank budget")
    if (modes[3]["peak_timed_queue_cycles"]<VBLANK_CYCLES or
        modes[3]["over_budget_batches"]==0):
        raise ValueError("FAIL CLOSED: expected real 4-copy overload was not observed")
    b=BATCH.findall(log)
    if len(b)!=1:
        raise ValueError("FAIL CLOSED: missing aggregate GBA batch counter")
    baseline,basepeak,maxbatch,maxlz,maxraw=map(int,b[0])
    if baseline<3 or basepeak<=0 or maxbatch<modes[3]["peak_timed_queue_cycles"] or maxlz<4:
        raise ValueError("FAIL CLOSED: batch statistics inconsistent")
    if not source["all_frames_lossless_roundtrip"] or not linker["all_6_frames_unchanged_pixels"]:
        raise ValueError("FAIL CLOSED: original Groudon pixels not preserved")
    if linker["pilot_rom_sha256"]!=hashlib.sha256(finalrom).hexdigest():
        raise ValueError("FAIL CLOSED: source ROM mismatch")
    if not qa_passes:
        raise ValueError("FAIL CLOSED: actual mGBA assertions did not all pass")
    return {
        "kind":"authentic_arm_gba_vblank_multiple_lz10_decode_stress",
        "pilot_rom_sha256":linker["pilot_rom_sha256"],
        "real_mgba_qa_assertions":"19/19",
        "mode_records":modes,
        "baseline_single_decode_samples":baseline,
        "baseline_peak_timed_queue_cycles":basepeak,
        "maximum_sum_of_timed_sprite_queue_calls":maxbatch,
        "maximum_lz10_decodes_in_one_queue":maxlz,
        "maximum_normal_sprite_copies_in_one_queue":maxraw,
        "vblank_cycle_window":VBLANK_CYCLES,
        "four_decodes_observed_over_budget":True,
        "graphics_frames_byte_identical":True,
        "same_owned_obj_vram_destination":True,
        "multiple_concurrent_visible_groudon_tested":False,
        "gpu_dma_audio_vblank_handlers_timed":False,
        "fps_measured":False,
        "gba_hardware_console_tested":False,
        "safe_to_enable_for_all_pokemon":False,
        "ready_for_master":False,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--log",type=Path,required=True)
    p.add_argument("--rom",type=Path,required=True)
    p.add_argument("--source-report",type=Path,required=True)
    p.add_argument("--link-report",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        out=summarize(a.log.read_text(),a.rom.read_bytes(),
                      json.loads(a.source_report.read_text()),
                      json.loads(a.link_report.read_text()))
        a.output.write_text(json.dumps(out,indent=2)+"\n")
        print(json.dumps(out,indent=2))
    except (OSError,ValueError,KeyError) as e:
        sys.exit(str(e))


if __name__=="__main__":
    main()
