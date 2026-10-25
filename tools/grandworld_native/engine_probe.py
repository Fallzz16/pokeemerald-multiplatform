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

def _native_compile(command, world, src, obj, flags, use_preproc):
    includes = ["-iquote" + str(world / "include"),
                "-iquote" + str(world / "src")]
    if not use_preproc:
        return subprocess.run([command, *flags, *includes, "-c", str(src),
                               "-o", str(obj)], cwd=world, capture_output=True,
                              text=True, timeout=100)
    # World build uses: cpp | preproc -i -g build/assets <source> charmap.txt
    # then compiles the transformed C stream. Do not substitute placeholders
    # for the game's text or artwork; use real generated resource files.
    tool = world / "tools/preproc/preproc"
    if not tool.is_file():
        raise FileNotFoundError("World preproc executable missing; run make -f make_tools.mk")
    rel = src.relative_to(world)
    cpp = subprocess.run([command, *flags, *includes, "-E", str(rel)],
                         cwd=world, capture_output=True, timeout=100)
    if cpp.returncode:
        return subprocess.CompletedProcess(cpp.args, cpp.returncode, b"",
                                          cpp.stderr.decode(errors="replace"))
    processed = subprocess.run([str(tool), "-i", "-g", "build/assets",
                               str(rel), "charmap.txt"], cwd=world,
                              input=cpp.stdout, capture_output=True, timeout=100)
    if processed.returncode:
        return subprocess.CompletedProcess(processed.args, processed.returncode,
                                          b"", processed.stderr.decode(errors="replace"))
    # Input was already CPP-expanded, exactly as required by World preproc.
    return subprocess.run([command, *flags, "-x", "c", "-c", "-", "-o",
                           str(obj)], input=processed.stdout, cwd=world,
                          capture_output=True, timeout=120)

def compile_engine(world, out, compiler="gcc", use_preproc=False):
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
            try:
                run = _native_compile(command, world, src, obj, FLAGS, use_preproc)
                errors = run.stderr
                if isinstance(errors, bytes):
                    errors = errors.decode(errors="replace")
                entry.update(status="object_compiled" if run.returncode == 0 else "failed",
                             return_code=run.returncode,
                             errors=errors.splitlines()[:90],
                             bytes=obj.stat().st_size if obj.exists() else 0)
            except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
                entry.update(status="toolchain_error", errors=[str(exc)])
        results.append(entry)
    return {"schema": 1, "stage": "P2_real_World_M8_source_object_probe",
            "compiler": command, "real_world_preprocessor": use_preproc,
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
    p.add_argument("--use-world-preproc", action="store_true",
                   help="Use World charmap and asset pipeline for real resources")
    args = p.parse_args()
    result = compile_engine(args.world, args.objects, args.compiler, args.use_world_preproc)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for entry in result["objects"]:
        print(entry["source"], entry["status"], entry.get("bytes", 0), "bytes")
        for error in entry.get("errors", [])[:4]:
            print("  ", error)
    print("Not a fully linked World executable.")

if __name__ == "__main__":
    main()
