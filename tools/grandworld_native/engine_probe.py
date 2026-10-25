#!/usr/bin/env python3
"""Compile REAL, pinned World engine translation units (not a fake SDL demo).

Always run on a disposable World checkout after generated headers and native
memory/save/DMA overlays. The .o files are host-machine compiled C source from
the actual game, but this does NOT establish a linked playable executable.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

# Deliberately covers the actual World boot, regions, titles and gameplay.
SOURCES = (
    "main.c",
    "main_menu.c",
    "region_switch.c",
    "overworld.c",
    "battle_main.c",
)
FLAGS = (
    "-m32", "-std=gnu17", "-O0", "-g",
    "-fno-strict-aliasing", "-fno-common",
    "-ffunction-sections", "-fdata-sections",
    "-Werror=implicit-function-declaration",
    "-DPORTABLE=1", "-DGW_WORLD_NATIVE=1",
    "-DMODERN=1", "-DNONMATCHING=1",
    "-DPLATFORM_SDL2=1", "-DEMERALD=1",
    "-DALL_REGIONS=1", "-DTESTING=0",
)

def compile_engine(world, out, compiler="gcc"):
    world = Path(world).resolve()
    out = Path(out).resolve()
    command = shutil.which(compiler)
    results = []
    out.mkdir(parents=True, exist_ok=True)
    for name in SOURCES:
        src = world / "src" / name
        obj = out / name.replace(".c", ".o")
        entry = {"source": "src/" + name, "object": str(obj.name)}
        if not command:
            entry.update(status="compiler_missing", errors=["No host GCC"])
        elif not src.is_file():
            entry.update(status="source_missing", errors=[str(src)])
        else:
            argv = [command, *FLAGS, "-iquote" + str(world / "include"),
                    "-iquote" + str(world / "src"), "-c", str(src), "-o", str(obj)]
            run = subprocess.run(argv, cwd=world, capture_output=True,
                                 text=True, timeout=100)
            entry.update(status="object_compiled" if run.returncode == 0 else "failed",
                         return_code=run.returncode,
                         errors=run.stderr.splitlines()[:90],
                         bytes=obj.stat().st_size if obj.exists() else 0)
        results.append(entry)
    return {"schema": 1, "stage": "P2_real_World_M8_source_object_probe",
            "compiler": command,
            "objects": results,
            "compiled": sum(x["status"] == "object_compiled" for x in results),
            "requested": len(SOURCES),
            "main_object_ok": results[0]["status"] == "object_compiled",
            "world_engine_linked": False, "world_gameplay_booted": False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--output", default="native-engine-objects.json")
    p.add_argument("--objects", default="native-world-objects")
    p.add_argument("--compiler", default="gcc")
    args = p.parse_args()
    result = compile_engine(args.world, args.objects, args.compiler)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for entry in result["objects"]:
        print(entry["source"], entry["status"], entry.get("bytes", 0), "bytes")
        for error in entry.get("errors", [])[:4]:
            print("  ", error)
    print("Not a fully linked World executable.")

if __name__ == "__main__":
    main()
