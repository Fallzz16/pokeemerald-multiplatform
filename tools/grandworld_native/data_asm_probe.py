#!/usr/bin/env python3
"""Classify actual World data/*.s native-assembly portability.

World's original build uses: preproc -s | cpp | preproc -ie | ARM assembler.
This diagnostic runs the same source/charmap stages, then host GAS.
Failures are evidence of remaining native-port work, never fake assets.
No source file or original compressed graphic is overwritten.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

try:
    from .native_asm import normalize_host_assembly
except ImportError:
    from native_asm import normalize_host_assembly


def _run(argv, cwd, input_bytes=None, seconds=100):
    return subprocess.run(argv, cwd=cwd, input=input_bytes,
                          capture_output=True, timeout=seconds)


def inspect(world, objects, limit=25, compiler="gcc"):
    world = Path(world).resolve()
    objects = Path(objects).resolve()
    if limit < 1 or limit > 100:
        raise ValueError("maximum of 100 real data ASM sources per audit")
    preproc = world / "tools/preproc/preproc"
    if not (world / "charmap.txt").is_file() or not preproc.is_file():
        raise ValueError("World charmap / built original preprocessor missing")
    cc = shutil.which(compiler)
    if not cc:
        raise ValueError("host GCC not found")
    sources = sorted((world / "data").glob("*.s"))[:limit]
    objects.mkdir(parents=True, exist_ok=True)
    found = []
    for source in sources:
        relative = source.relative_to(world).as_posix()
        result = {"source": relative, "status": "not_started", "native_object": False}
        # Failed preproc/CPP/assembler must not silently reuse an old object.
        object_file = objects / (source.stem + ".o")
        object_file.unlink(missing_ok=True)
        try:
            a = _run([str(preproc), "-s", relative, "charmap.txt"], world)
            if a.returncode:
                result["status"] = "charmap_stage1_failed"
                result["errors"] = a.stderr.decode(errors="replace").splitlines()[:12]
                found.append(result)
                continue
            b = _run([cc, "-E", "-x", "assembler-with-cpp", "-iquote", "include",
                      "-I", ".", "-Wno-trigraphs", "-DMODERN=1", "-DTESTING=0",
                      "-DEMERALD=1", "-DALL_REGIONS=1", "-"], world, a.stdout)
            if b.returncode:
                result["status"] = "cpp_failed"
                result["errors"] = b.stderr.decode(errors="replace").splitlines()[:12]
                found.append(result)
                continue
            c = _run([str(preproc), "-ie", relative, "charmap.txt"], world, b.stdout)
            if c.returncode:
                result["status"] = "charmap_stage2_failed"
                result["errors"] = c.stderr.decode(errors="replace").splitlines()[:12]
                found.append(result)
                continue
            original_asm = c.stdout.decode("utf-8", errors="surrogateescape")
            normalized, count = normalize_host_assembly(original_asm)
            object_file = objects / (source.stem + ".o")
            text = normalized.encode("utf-8", errors="surrogateescape")
            built = _run([cc, "-m32", "-x", "assembler", "-c", "-", "-o",
                          str(object_file)], world, text)
            result["changes_to_arm_comments"] = count
            if built.returncode:
                result["status"] = "native_assembler_failed"
                result["errors"] = built.stderr.decode(errors="replace").splitlines()[:20]
            else:
                result["status"] = "native_object_compiled"
                result["native_object"] = True
                result["object_bytes"] = object_file.stat().st_size
        except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
            result["status"] = "probe_exception"
            result["errors"] = [str(exc)]
        found.append(result)
    return {"schema": 1, "stage": "P2_real_World_data_assembly_portability",
            "original_source_files": len(sources),
            "native_objects": sum(x["native_object"] for x in found),
            "source_material_fabricated": False,
            "actual_game_engine_linked": False,
            "results": found}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--objects", default="native-world-data-objects")
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--report", default="native-world-data-asm.json")
    args = p.parse_args()
    data = inspect(args.world, args.objects, args.limit)
    Path(args.report).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("World original data assembly:", data["native_objects"], "/",
          data["original_source_files"], "compiled for i386.")
    for entry in data["results"]:
        print(entry["source"], entry["status"])
        if entry.get("errors"):
            print("\n".join(entry["errors"][:5]))


if __name__ == "__main__":
    main()
