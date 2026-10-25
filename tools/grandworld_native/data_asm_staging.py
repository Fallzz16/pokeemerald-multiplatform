#!/usr/bin/env python3
"""Compile real World data in TWO phases to protect the original preprocessor.

1. PREPARE original World data/*.s through preproc -s | cpp | preproc -ie.
2. Only AFTER phase 1, patch ARM GAS dialect in a disposable World checkout.
3. ASSEMBLE the saved original-preprocessed streams with x86 GAS, preserving
   original asset bytes, macros and include hierarchy. No fake symbols/assets.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

try:
    from .native_asm import normalize_host_assembly
    from .gba_data_asm_overlay import transform_text
except ImportError:
    from native_asm import normalize_host_assembly
    from gba_data_asm_overlay import transform_text

SCHEMA = 1
MANIFEST = "original-world-preproc-manifest.json"


def _run(args, cwd, data=None):
    return subprocess.run(args, input=data, cwd=cwd, capture_output=True, timeout=120)


def prepare(world, output, compiler="gcc"):
    world, output = Path(world).resolve(), Path(output).resolve()
    preproc = world / "tools/preproc/preproc"
    if not preproc.is_file() or not (world / "charmap.txt").is_file():
        raise ValueError("missing original World preprocessor/charmap")
    if not shutil.which(compiler):
        raise ValueError("native compiler missing")
    sources = sorted((world / "data").glob("*.s"))
    if not sources or len(sources) > 100:
        raise ValueError("unexpected genuine game-data assembly inventory")
    output.mkdir(parents=True, exist_ok=True)
    prepared = output / "_original_preproc"
    prepared.mkdir(exist_ok=True)
    records = []
    for source in sources:
        relative = source.relative_to(world).as_posix()
        row = {"source": relative, "status": "not_started"}
        target = prepared / (source.stem + ".s")
        target.unlink(missing_ok=True)
        stages = [
            [str(preproc), "-s", relative, "charmap.txt"],
            [compiler, "-E", "-x", "assembler-with-cpp", "-iquote", "include",
             "-I", ".", "-Wno-trigraphs", "-DMODERN=1", "-DTESTING=0",
             "-DEMERALD=1", "-DALL_REGIONS=1", "-"],
            [str(preproc), "-ie", relative, "charmap.txt"],
        ]
        payload = None
        for stage_number, args in enumerate(stages, 1):
            try:
                result = _run(args, world, payload)
            except (OSError, subprocess.TimeoutExpired) as exc:
                row.update(status="preprocessor_exception", errors=[str(exc)])
                break
            if result.returncode:
                row.update(status="preprocessor_stage_%d_failed" % stage_number,
                           errors=result.stderr.decode(errors="replace").splitlines()[:25])
                break
            payload = result.stdout
        else:
            target.write_bytes(payload)
            row.update(status="original_preprocessed", artifact=target.name,
                       sha256=hashlib.sha256(payload).hexdigest(),
                       original_bytes=len(payload))
        records.append(row)
    report = {"schema": SCHEMA, "stage": "P2_original_World_preprocessing_before_host_dialect",
              "source_files": len(sources), "prepared": sum(
                  x["status"] == "original_preprocessed" for x in records),
              "inputs_modified": False, "generated_game_data_fabricated": False,
              "records": records}
    (output / MANIFEST).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def assemble(world, output, compiler="gcc"):
    world, output = Path(world).resolve(), Path(output).resolve()
    manifest = json.loads((output / MANIFEST).read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA or manifest.get("inputs_modified") is not False:
        raise ValueError("invalid original World preprocessor manifest")
    if not shutil.which(compiler):
        raise ValueError("native compiler missing")
    records = []
    for original in manifest["records"]:
        source = original["source"]
        if not source.startswith("data/") or "/" in source[5:] or not source.endswith(".s"):
            raise ValueError("invalid or unexpected original game-data source path")
        row = {"source": source, "native_object": False}
        obj = output / (Path(source).stem + ".o")
        obj.unlink(missing_ok=True)
        if original["status"] != "original_preprocessed":
            row.update(status="preprocessing_failed", errors=original.get("errors", [])[:25])
            records.append(row)
            continue
        staged = output / "_original_preproc" / original["artifact"]
        if staged.name != Path(source).stem + ".s":
            raise ValueError("staged data path does not match original source")
        payload = staged.read_bytes()
        if hashlib.sha256(payload).hexdigest() != original["sha256"]:
            raise ValueError("original preprocessed game data changed after preparation")
        asm = payload.decode("utf-8", errors="surrogateescape")
        # This is a GENERATED assembler stream. World macros and assets were
        # already processed from the unmodified original game files.
        # The genuine World preprocessor embeds .include sources into its
        # saved stream. Converting the disposable .inc files AFTER prepare()
        # cannot fix the three Celadon macro operands already snapshotted here.
        # Reformat only those original expressions, never their numeric values.
        is_events = source == "data/event_scripts.s"
        converted, alterations = transform_text(asm, special_celadon=is_events)
        if is_events and alterations["celadon_expression"] != 3:
            raise ValueError("expected exactly three Celadon operands in original preprocessed event_scripts.s")
        converted, comment_changes = normalize_host_assembly(converted)
        native_bytes = converted.encode("utf-8", errors="surrogateescape")
        try:
            result = _run(
                [compiler, "-m32", "-x", "assembler", "-c", "-", "-o", str(obj)],
                world, native_bytes)
            if result.returncode:
                row.update(status="native_assembler_failed",
                           errors=result.stderr.decode(errors="replace").splitlines()[:30])
            elif not obj.is_file() or not obj.stat().st_size:
                row.update(status="missing_native_object", errors=["assembler produced no object"])
            else:
                row.update(status="native_object_compiled", native_object=True,
                           object_bytes=obj.stat().st_size,
                           generated_asm_conversions=alterations,
                           comment_conversions=comment_changes)
        except (OSError, subprocess.TimeoutExpired) as exc:
            row.update(status="native_assembler_exception", errors=[str(exc)])
        records.append(row)
    return {"schema": SCHEMA, "stage": "P2_original_preprocessed_World_data_to_x86_GAS",
            "original_source_files": manifest["source_files"],
            "native_objects": sum(row["native_object"] for row in records),
            "game_data_fabricated": False, "source_files_modified_during_preproc": False,
            "results": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("prepare", "assemble"), required=True)
    parser.add_argument("--world", required=True)
    parser.add_argument("--objects", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    report = (prepare(args.world, args.objects) if args.mode == "prepare"
              else assemble(args.world, args.objects))
    Path(args.report).write_text(json.dumps(report, indent=2) + "\n",
                                 encoding="utf-8")
    print(args.mode, "original game data:", report.get("prepared", report.get("native_objects")),
          "/", report.get("source_files", report.get("original_source_files")))
    for row in report.get("records", report.get("results", [])):
        if row.get("status") not in ("original_preprocessed", "native_object_compiled"):
            print(row["source"], row["status"], row.get("errors", [])[:3])


if __name__ == "__main__":
    main()
