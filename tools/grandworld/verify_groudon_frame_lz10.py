#!/usr/bin/env python3
"""Fail-closed proof that a real final ARM/GBA ROM contains exact LZ10 frames.

Companion to apply_groudon_frame_lz10.py; does not test frame pacing,
screen pixels, DMA/VBlank duration, or actual Groudon object appearance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from overworld_payload_experiments import lz10_decode
from apply_groudon_frame_lz10 import (FRAME_COUNT, FRAME_BYTES,
                                       ROM_BASE, ROM_BYTES, FRAME_PREFIX)


def prove(nm, rom, original, before, after, max_profile_ewram_increase=0, max_asm_iwram_increase=0):
    if len(rom)!=ROM_BYTES or rom[0xAC:0xB0]!=b"BPEE":
        raise ValueError("not a valid GBA ROM image")
    matches={}
    for line in nm.splitlines():
        m=re.fullmatch(r"\s*([0-9a-fA-F]{8})\s+([0-9a-fA-F]+)\s+([a-zA-Z])\s+(\S+)\s*",line)
        if m:
            matches[m[4]]=(int(m[1],16),int(m[2],16))
    if not original.get("all_frames_lossless_roundtrip"):
        raise ValueError("baseline frame report is not lossless")
    if original["raw_frames"]!=FRAME_COUNT or original["uncompressed_frame_bytes"]!=FRAME_BYTES:
        raise ValueError("unexpected source frame geometry")
    verified=[]
    for i in range(FRAME_COUNT):
        name=f"{FRAME_PREFIX}{i}"
        if name not in matches:
            raise ValueError("compressed ROM symbol not linked: "+name)
        address,size=matches[name]
        offset=address-ROM_BASE
        byte_count=original["compressed_frame_bytes"][i]
        if offset<0 or size<byte_count or size>byte_count+3 or offset+size>len(rom):
            raise ValueError("compressed ROM frame has incorrect size: "+name)
        data=rom[offset:offset+byte_count]
        raw=lz10_decode(data, min_distance=2)
        if len(raw)!=FRAME_BYTES:
            raise ValueError("decompressed frame dimension mismatch: "+name)
        digest=hashlib.sha256(raw).hexdigest()
        if digest!=original["original_frame_sha256"][i]:
            raise ValueError("frame differs from original pixels: "+name)
        verified.append({"name":name,"linked_size":size,"encoded_bytes":byte_count,
                         "decoded_size":len(raw),"original_sha256":digest})
    if before.get("rom_sha256")!=original.get("input_rom_sha256"):
        raise ValueError("baseline build and encoded source ROM do not match")
    if after.get("rom_sha256")!=hashlib.sha256(rom).hexdigest():
        raise ValueError("final ARM/GBA memory report not tied to final ROM")
    base=before["linker_memory_bytes"]
    final=after["linker_memory_bytes"]
    delta={key:base[key]-final[key] for key in ("ROM","EWRAM","IWRAM")}
    if delta["ROM"]<=0:
        raise ValueError("pilot has no real linker ROM payload saving")
    if delta["EWRAM"] < -max_profile_ewram_increase or delta["IWRAM"] < -max_asm_iwram_increase:
        raise ValueError("pilot increased static EWRAM or IWRAM")
    if before["rom_sha256"]==after["rom_sha256"]:
        raise ValueError("candidate did not change actual ROM image")
    return {
        "kind":"real_arm_gba_groudon_lz10_frame_runtime_pilot",
        "baseline_rom_sha256":before["rom_sha256"],
        "pilot_rom_sha256":after["rom_sha256"],
        "frame_symbols_extracted_from_final_rom":verified,
        "all_6_frames_unchanged_pixels":True,
        "raw_groudon_symbol_remains_in_linked_elf":"gObjectEventPic_Groudon" in matches,
        "linked_rom_payload_saved_bytes":delta["ROM"],
        "linked_ewram_delta_bytes":delta["EWRAM"],
        "linked_iwram_delta_bytes":delta["IWRAM"],
        "profiling_instrumentation_ewram_allowance_bytes":max_profile_ewram_increase,
        "optimized_asm_iwram_allowance_bytes":max_asm_iwram_increase,
        "sprite_frame_dimension_changed":False,
        "obj_frame_tile_allocation_changed":False,
        "palettes_or_saves_changed":False,
        "mGBA_groudon_visible_tested":False,
        "vblank_cpu_cycles_measured":False,
        "hardware_verified":False,
        "ready_to_merge":False,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--symbols",type=Path,required=True)
    ap.add_argument("--rom",type=Path,required=True)
    ap.add_argument("--source-report",type=Path,required=True)
    ap.add_argument("--baseline-budget",type=Path,required=True)
    ap.add_argument("--final-budget",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--max-profile-ewram-increase",type=int,default=0)
    ap.add_argument("--max-asm-iwram-increase",type=int,default=0)
    args=ap.parse_args()
    if not 0<=args.max_profile_ewram_increase<=16:
        ap.error("maximum profiler allowance is 16 B")
    if not 0<=args.max_asm_iwram_increase<=1536:
        ap.error("maximum optimized decoder allowance is 1536 B")
    try:
        res=prove(args.symbols.read_text(),args.rom.read_bytes(),
                  json.loads(args.source_report.read_text()),
                  json.loads(args.baseline_budget.read_text()),
                  json.loads(args.final_budget.read_text()),args.max_profile_ewram_increase,args.max_asm_iwram_increase)
        args.output.write_text(json.dumps(res,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({k:v for k,v in res.items()
                          if k!="frame_symbols_extracted_from_final_rom"},indent=2))
    except (OSError,ValueError,KeyError) as exc:
        sys.exit("FAIL CLOSED: "+str(exc))


if __name__=="__main__":
    main()
