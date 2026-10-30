#!/usr/bin/env python3
"""Parse native GBA TM2/TM3 Groudon LZ10 cycles from genuine mGBA execution."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

LINE=re.compile(
    r"\bGROUDON_CPU samples=(\d+) peak_cycles=(\d+) "
    r"total_cycles=(\d+) avg_cycles=(\d+) timer_conflicts=(\d+)")
VBLANK_CYCLES=68*1232  # 83776 cycles, single 2K frame only


def analyze(log, rom, source, link):
    m=LINE.findall(log)
    if len(m)!=1:
        raise ValueError("FAIL CLOSED: need one real Groudon timer report")
    n,peak,total,avg,busy=map(int,m[0])
    if not 3<=n<=10000 or not 0<peak<=total or avg!=total//n:
        raise ValueError("FAIL CLOSED: invalid timer counters")
    if busy!=0:
        raise ValueError("FAIL CLOSED: hardware Timer2/Timer3 occupied during test")
    if peak>=VBLANK_CYCLES:
        raise ValueError("FAIL CLOSED: one Groudon LZ10 frame exceeded VBlank cycles")
    if link["pilot_rom_sha256"]!=hashlib.sha256(rom).hexdigest():
        raise ValueError("FAIL CLOSED: ROM/report SHA256 mismatch")
    if not link["all_6_frames_unchanged_pixels"] or not source["all_frames_lossless_roundtrip"]:
        raise ValueError("FAIL CLOSED: sprite data not preserved")
    return {
        "kind":"observed_gba_hardware_timer_cycles_per_lz10_2k_frame",
        "rom_sha256":link["pilot_rom_sha256"],
        "source":"pinned World CycleCountStart / End timers 2 and 3 in CI-only build",
        "copies_profiled":n,
        "peak_cycles":peak,
        "mean_cycles_integer":avg,
        "total_decompression_cycles":total,
        "single_frame_budget_cycles":VBLANK_CYCLES,
        "single_frame_peak_share_of_vblank_percent":round(100*peak/VBLANK_CYCLES,2),
        "timer_conflicts":busy,
        "pixels_original_in_final_rom":True,
        "profiling_ewram_static_overhead_bytes":16,
        "overall_vblank_utilization_measured":False,
        "hardware_console_verified":False,
        "multiple_simultaneous_64x64_tested":False,
        "fps_measured":False,
        "release_ready":False,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--log",type=Path,required=True)
    ap.add_argument("--rom",type=Path,required=True)
    ap.add_argument("--source-report",type=Path,required=True)
    ap.add_argument("--link-report",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    try:
        data=analyze(args.log.read_text(),args.rom.read_bytes(),
                     json.loads(args.source_report.read_text()),
                     json.loads(args.link_report.read_text()))
        args.output.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(data,indent=2))
    except (OSError,KeyError,ValueError) as e:
        sys.exit(str(e))


if __name__=="__main__":
    main()
