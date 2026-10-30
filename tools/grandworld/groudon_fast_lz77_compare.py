#!/usr/bin/env python3
"""Compare optimized ARM LZ10 Groudon against actual pinned BIOS benchmark.

Baseline PR110: https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/41060393430
Only the decoder differs, same 6 frames / same LZ10 bytes / same CI scene.
"""
import argparse
import json
from pathlib import Path
import sys

BASELINE_RUN=41060393430
BIOS_PEAK=39136
BIOS_AVG=38626


def compare(probe, link):
    if not probe.get("pixels_original_in_final_rom"):
        raise ValueError("FAIL CLOSED: runtime pixel proof absent")
    if not link.get("all_6_frames_unchanged_pixels"):
        raise ValueError("FAIL CLOSED: final ROM frame hashes invalid")
    if probe.get("copies_profiled",0)<20 or probe.get("timer_conflicts",-1)!=0:
        raise ValueError("FAIL CLOSED: inadequate clean mGBA cycle samples")
    peak=probe["peak_cycles"]
    avg=probe["mean_cycles_integer"]
    if peak>=BIOS_PEAK or avg>=BIOS_AVG:
        raise ValueError(f"FAIL CLOSED: optimized decoder slower/equal to BIOS peak={peak} mean={avg}")
    if link["linked_rom_payload_saved_bytes"]<=0:
        raise ValueError("FAIL CLOSED: no actual ROM economy")
    if link["pilot_rom_sha256"]!=probe["rom_sha256"]:
        raise ValueError("FAIL CLOSED: runtime ROM hash differs from linked ROM")
    return {
        "kind":"GBA_optimized_ARM_LZ10_vs_BIOS_Groudon_2KiB",
        "bios_baseline_run_id":BASELINE_RUN,
        "bios_peak_cycles":BIOS_PEAK,
        "bios_mean_cycles":BIOS_AVG,
        "optimized_peak_cycles":peak,
        "optimized_mean_cycles":avg,
        "peak_cycle_saving":BIOS_PEAK-peak,
        "mean_cycle_saving":BIOS_AVG-avg,
        "mean_cycle_reduction_percent":round(100*(BIOS_AVG-avg)/BIOS_AVG,2),
        "proven_real_rom_saving_bytes":link["linked_rom_payload_saved_bytes"],
        "ewram_static_extra_bytes":-link["linked_ewram_delta_bytes"],
        "iwram_static_extra_bytes":-link["linked_iwram_delta_bytes"],
        "runtime_ROM_sha256":probe["rom_sha256"],
        "real_Groudon_sprite_pixels_passed":True,
        "complete_VBlank_load_tested":False,
        "multiple_simultaneous_Groudon_tested":False,
        "hardware_console_tested":False,
        "ready_for_master":False,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--timer-report",type=Path,required=True)
    ap.add_argument("--link-report",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    try:
        p=json.loads(args.timer_report.read_text())
        link=json.loads(args.link_report.read_text())
        result=compare(p,link)
        args.output.write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps(result,indent=2))
    except (OSError,KeyError,ValueError) as e:
        sys.exit(str(e))


if __name__=="__main__":
    main()
