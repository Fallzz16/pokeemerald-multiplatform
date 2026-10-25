#!/usr/bin/env python3
"""P2: link genuine World/M8 C with real preprocessed ASM and generated MIDI.

Never substitutes fake symbols, graphics, text, or executable stubs. A
relocatable .o still has unresolved game dependencies and IS NOT PLAYABLE.
The diagnostic measures which dependencies actual game data resolves.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

def _invoke(argv, seconds=100):
    return subprocess.run(argv, capture_output=True, text=True, timeout=seconds)

def _undefined(nm, target):
    run = _invoke([nm, "-u", str(target)])
    if run.returncode:
        raise RuntimeError("nm -u failed: " + run.stderr[:1200])
    values = set()
    for line in run.stdout.splitlines():
        bits = line.strip().split()
        if len(bits) >= 2 and bits[-2] in ("U", "w"):
            values.add(bits[-1])
    return values

def analyze(code_objects, data_objects, output, compiler="gcc", nm="nm", music_objects=None):
    code_dir = Path(code_objects).resolve()
    data_dir = Path(data_objects).resolve()
    report = Path(output).resolve()
    code = sorted(code_dir.glob("*.o"))
    data = sorted(data_dir.glob("*.o"))
    music = (sorted(Path(music_objects).resolve().glob("*.o"))
             if music_objects is not None else [])
    info = {
        "schema": 1, "stage": "P2_real_C_plus_original_data_relocatable_link",
        "code_object_count": len(code), "data_object_count": len(data),
        "music_object_count": len(music),
        "original_music_objects_supplied": music_objects is not None,
        "all_objects_from_real_source": True, "dummy_symbols_inserted": False,
        "partial_linked": False, "game_executable_linked": False,
        "gameplay_verified": False,
        "unresolved_before": None, "unresolved_after": None,
        "resolved_by_original_data": [], "introduced_by_data": [],
    }
    cc, symbol_tool = shutil.which(compiler), shutil.which(nm)
    if not cc or not symbol_tool:
        info["error"] = "No gcc/nm available"
        return info
    if not code:
        info["error"] = "No native engine code objects"
        return info
    if not data:
        info["error"] = "No original data objects successfully assembled"
        return info
    if music_objects is not None and not music:
        info["error"] = "No original MIDI objects successfully assembled"
        return info
    report.parent.mkdir(parents=True, exist_ok=True)
    baseline = report.parent / "gw-engine-code-only-NOT-EXECUTABLE.o"
    combined = report.parent / "gw-engine-with-real-data-NOT-EXECUTABLE.o"
    core = _invoke([cc, "-m32", "-r", *map(str, code), "-o", str(baseline)])
    if core.returncode:
        info["error"] = "Code relocatable link failed"
        info["diagnostics"] = core.stderr.splitlines()[:35]
        return info
    before = _undefined(symbol_tool, baseline)
    linked = _invoke([cc, "-m32", "-r", *map(str, code),
                      *map(str, data), *map(str, music), "-o", str(combined)])
    if linked.returncode:
        info["error"] = "Code+real data relocatable link failed"
        info["diagnostics"] = linked.stderr.splitlines()[:55]
        return info
    after = _undefined(symbol_tool, combined)
    info["partial_linked"] = True
    info["partial_object_bytes"] = combined.stat().st_size
    info["unresolved_before"] = len(before)
    info["unresolved_after"] = len(after)
    info["resolved_by_original_data_count"] = len(before - after)
    info["resolved_by_original_data"] = sorted(before - after)[:80]
    info["introduced_by_data_count"] = len(after - before)
    info["introduced_by_data"] = sorted(after - before)[:80]
    info["still_unresolved_examples"] = sorted(after)[:80]
    return info

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--code", required=True, help="native World/M8 C .o folder")
    p.add_argument("--data", required=True, help="original World/M8 data ASM .o folder")
    p.add_argument("--music", help="genuine GBA-generated MIDI song .o folder")
    p.add_argument("--report", default="native-real-data-link.json")
    args = p.parse_args()
    result = analyze(args.code, args.data, args.report, music_objects=args.music)
    Path(args.report).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items()
                      if not isinstance(value, list)}, indent=2))
    if result.get("error"):
        print("Link blocked:", result["error"])
        for line in result.get("diagnostics", [])[:12]:
            print(line)
    elif result["partial_linked"]:
        print("Original game data resolved:",
              result["resolved_by_original_data_count"], "unresolved C dependencies")
        print("Remaining unresolved:", result["unresolved_after"])
        print("This is NOT an executable or booted game.")

if __name__ == "__main__":
    main()
