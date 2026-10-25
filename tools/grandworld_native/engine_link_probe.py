#!/usr/bin/env python3
"""Audit a partial relocatable 32-bit World engine link.

Combines only successfully compiled genuine World source objects. gcc -m32 -r
keeps unresolved symbols and reveals real remaining engine dependencies.
A partial relocatable object is NEVER a playable executable.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

def inspect(objects, output, compiler="gcc", nm="nm"):
    objects = Path(objects).resolve()
    output = Path(output).resolve()
    cc, symbols_tool = shutil.which(compiler), shutil.which(nm)
    candidates = sorted(objects.glob("*.o"))
    info = {"schema": 1, "stage": "P2_relocatable_real_world_link_probe",
            "objects": [f.name for f in candidates],
            "object_count": len(candidates), "partial_linked": False,
            "full_engine_linked": False, "executable_produced": False,
            "unresolved_count": None, "unresolved_examples": []}
    if not candidates:
        info["error"] = "No native World objects could be compiled"
        return info
    if not cc or not symbols_tool:
        info["error"] = "Missing C linker or nm"
        return info
    target = output.parent / "world-engine-PARTIAL-NOT-EXECUTABLE.o"
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [cc, "-m32", "-r", *map(str, candidates), "-o", str(target)]
    linked = subprocess.run(command, capture_output=True, text=True, timeout=90)
    if linked.returncode:
        info["error"] = "Relocatable link failed"
        info["linker_diagnostics"] = linked.stderr.splitlines()[:50]
        return info
    info["partial_linked"] = True
    info["partial_object_bytes"] = target.stat().st_size
    symbols = subprocess.run([symbols_tool, "-u", str(target)],
                             capture_output=True, text=True, timeout=30)
    unresolved = set()
    for line in symbols.stdout.splitlines():
        parts = line.strip().split()
        if parts and len(parts) >= 2 and parts[-2] in ("U", "w"):
            unresolved.add(parts[-1])
    info["unresolved_count"] = len(unresolved)
    info["unresolved_examples"] = sorted(unresolved)[:90]
    defined = subprocess.run([symbols_tool, "--defined-only", str(target)],
                             capture_output=True, text=True, timeout=30)
    info["World_entry_symbols"] = [
        symbol for symbol in ("AgbMain", "AgbMainLoop", "GwWorldFrame",
                              "GwWorldVBlank", "gMain", "RegionSwitch")
        if any(row.strip().endswith(" " + symbol)
               for row in defined.stdout.splitlines())
    ]
    return info

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--objects", required=True)
    p.add_argument("--report", default="native-engine-link.json")
    args = p.parse_args()
    data = inspect(args.objects, args.report)
    Path(args.report).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in data.items() if k != "unresolved_examples"}, indent=2))
    if data.get("unresolved_examples"):
        print("Unresolved examples:", ", ".join(data["unresolved_examples"][:16]))

if __name__ == "__main__":
    main()
