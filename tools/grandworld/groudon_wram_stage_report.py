#!/usr/bin/env python3
"""Evidence parser for safe, VBlank-free Groudon stage requests in real mGBA."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

LINE = re.compile(r"\bGROUDON_STAGE staged=(\d+) fallbacks=(\d+) requests_in_vblank=(\d+)")


def analyze(text, rom, evidence, budget):
    rows=LINE.findall(text)
    if len(rows)!=1:
        raise ValueError("FAIL CLOSED: expected one actual mGBA stage report")
    staged, fallback, vblank=map(int,rows[0])
    if staged<3 or fallback!=0 or vblank!=0:
        raise ValueError("FAIL CLOSED: staging unavailable or fallback in observed Groudon QA")
    romhash=hashlib.sha256(rom).hexdigest()
    if romhash!=evidence.get("pilot_rom_sha256") or romhash!=budget.get("rom_sha256"):
        raise ValueError("FAIL CLOSED: ROM hashes differ from real ARM build")
    if not evidence.get("all_6_frames_unchanged_pixels"):
        raise ValueError("FAIL CLOSED: frames not byte-identical")
    if not budget.get("memory_budget_passed"):
        raise ValueError("FAIL CLOSED: ARM memory budget not passed")
    return {
        "kind":"real_gba_groudon_staging_wram_runtime_qa",
        "rom_sha256":romhash,
        "groudon_frame_requests_staged_in_ewram":staged,
        "groudon_fallbacks_to_bios_vram":fallback,
        "requests_arriving_during_vblank":vblank,
        "linked_rom_payload_bytes_saved":evidence["linked_rom_payload_saved_bytes"],
        "static_ewram_bytes_added":-evidence["linked_ewram_delta_bytes"],
        "static_iwram_bytes_added":-evidence["linked_iwram_delta_bytes"],
        "remaining_ewram_bytes":budget["free_bytes"]["EWRAM"],
        "mGBA_gpu_vram_frame_checks_passed":True,
        "vblank_cpu_cost_measured":False,
        "fps_measured":False,
        "multiple_simultaneous_groudon_tested":False,
        "staging_overflow_stress_tested":False,
        "ready_for_master":False,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--log",type=Path,required=True)
    p.add_argument("--rom",type=Path,required=True)
    p.add_argument("--link-report",type=Path,required=True)
    p.add_argument("--budget",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    try:
        r=analyze(a.log.read_text(),a.rom.read_bytes(),
                  json.loads(a.link_report.read_text()),
                  json.loads(a.budget.read_text()))
        a.output.write_text(json.dumps(r,indent=2)+"\n")
        print(json.dumps(r,indent=2))
    except (OSError,ValueError,KeyError) as e:
        sys.exit(str(e))


if __name__=="__main__":
    main()
