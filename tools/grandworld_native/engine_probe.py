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

from native_asm import normalize_host_assembly

# Deliberately covers the actual World boot, regions, titles and gameplay.
SOURCES = (
    "main.c",
    "main_menu.c",
    "region_switch.c",
    "overworld.c",
    "battle_main.c",
    "gpu_regs.c",
    "task.c",
    "sprite.c",
    "bg.c",
    "palette.c",
    "fieldmap.c",
    "field_camera.c",
    "event_data.c",
    "field_control_avatar.c",
    "field_player_avatar.c",
    "follower_npc.c",
    "battle_setup.c",
    "sound.c",
    "rtc.c",
    "scanline_effect.c",
    "malloc.c",
    "script.c",
    "field_tasks.c",
    "load_save.c",
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
    # The output is World-C plus real charmap and incbin resources.
    # First emit host assembler then convert only GNU ARM '@' comments to
    # x86 '#' comments; preserve the original binary data directives.
    assembly = obj.with_suffix(".s")
    generated = subprocess.run(
        [command, *flags, "-x", "c", "-S", "-", "-o", str(assembly)],
        input=processed.stdout, cwd=world, capture_output=True, timeout=120)
    if generated.returncode:
        return generated
    data = assembly.read_text(encoding="utf-8")
    normalized, changed = normalize_host_assembly(data)
    if changed:
        assembly.write_text(normalized, encoding="utf-8")
    assembled = subprocess.run(
        [command, "-m32", "-x", "assembler", "-c", str(assembly), "-o", str(obj)],
        cwd=world, capture_output=True, timeout=120)
    # Keep assembler output for reproducibility and artifact debugging.
    return subprocess.CompletedProcess(
        assembled.args, assembled.returncode, assembled.stdout,
        generated.stderr + assembled.stderr)

def compile_engine(world, out, compiler="gcc", use_preproc=False, all_sources=False):
    world = Path(world).resolve()
    out = Path(out).resolve()
    command = shutil.which(compiler)
    results = []
    out.mkdir(parents=True, exist_ok=True)
    sources = (sorted(path.name for path in (world / "src").glob("*.c"))
               if all_sources else SOURCES)
    for name in sources:
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
                if run.returncode and obj.with_suffix(".s").is_file():
                    entry["assembly_head"] = obj.with_suffix(".s").read_text(
                        encoding="utf-8", errors="replace").splitlines()[:45]
            except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
                entry.update(status="toolchain_error", errors=[str(exc)])
        results.append(entry)
    return {"schema": 1, "stage": "P2_real_World_M8_source_object_probe",
            "compiler": command, "real_world_preprocessor": use_preproc,
            "all_sources_requested": all_sources,
            "objects": results,
            "compiled": sum(x["status"] == "object_compiled" for x in results),
            "requested": len(SOURCES),
            "main_object_ok": any(x["source"] == "src/main.c" and
                                  x["status"] == "object_compiled" for x in results),
            "world_engine_linked": False, "world_gameplay_booted": False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--output", default="native-engine-objects.json")
    p.add_argument("--objects", default="native-world-objects")
    p.add_argument("--compiler", default="gcc")
    p.add_argument("--use-world-preproc", action="store_true",
                   help="Use World charmap and asset pipeline for real resources")
    p.add_argument("--all-sources", action="store_true",
                   help="Inventory every real World src/*.c instead of just 24 core modules")
    args = p.parse_args()
    result = compile_engine(args.world, args.objects, args.compiler, args.use_world_preproc, args.all_sources)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for entry in result["objects"]:
        print(entry["source"], entry["status"], entry.get("bytes", 0), "bytes")
        for error in entry.get("errors", [])[:4]:
            print("  ", error)
    print("Not a fully linked World executable.")

if __name__ == "__main__":
    main()
