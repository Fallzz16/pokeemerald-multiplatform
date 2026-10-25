#!/usr/bin/env python3
"""Non-destructive P1 experiment: compile portable platform sources against World.

32-bit host compilation matches the World save pointer layout.
Failures are recorded, not hidden. A successful syntax probe is NOT a native
game build: only complete linking and runtime tests can establish P1-P5.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

SOURCES = ("bios.c", "dma.c", "gba_easy_draw.c", "cgb_audio.c")
FLAGS = ("-std=gnu99", "-fsyntax-only", "-Wno-attributes", "-DPORTABLE",
         "-DNONMATCHING", "-DMODERN=1", "-DPLATFORM_SDL2", "-DRENDERER_EASY_DRAW",
         "-DGW_WORLD_NATIVE=1", "-Werror=implicit-function-declaration")

def probe(world, grandworld, compiler):
    world = Path(world).resolve()
    grandworld = Path(grandworld).resolve()
    cc = shutil.which(compiler)
    results = []
    for name in SOURCES:
        path = grandworld / "src" / "platform" / name
        cmd = [cc or compiler, "-m32", *FLAGS,
               "-iquote" + str(world / "include"),
               "-iquote" + str(world / "src"),
               "-iquote" + str(grandworld / "include"),
               "-iquote" + str(grandworld / "src"), str(path)]
        if cc is None:
            result = {"source": name, "status": "compiler_unavailable", "errors": ["Compiler not found"]}
        elif not path.is_file():
            result = {"source": name, "status": "source_missing", "errors": [str(path)]}
        else:
            run = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            result = {"source": name, "status": "syntax_pass" if run.returncode == 0 else "syntax_failed",
                      "return_code": run.returncode,
                      "errors": run.stderr.splitlines()[:65]}
        results.append(result)
    return {"schema": 1, "stage": "P1_portability_probe",
            "compiler": cc, "results": results,
            "all_syntax_passed": all(r["status"] == "syntax_pass" for r in results),
            "native_linked": False, "native_boot_verified": False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", required=True)
    parser.add_argument("--grandworld", default=".")
    parser.add_argument("--compiler", default="gcc")
    parser.add_argument("--output", default="native-probe.json")
    args = parser.parse_args()
    result = probe(args.world, args.grandworld, args.compiler)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for item in result["results"]:
        print(item["source"], item["status"])
        for error in item["errors"][:3]:
            print("  ", error)
    print("P1 native link and P2-P5 gameplay are NOT validated.")

if __name__ == "__main__":
    main()
