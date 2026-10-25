#!/usr/bin/env python3
"""Preprocess real World/M8 data assembly BEFORE converting GBA syntax to x86.

The authentic World GBA pipeline is:
    preproc -s -> C preprocessor -> preproc -ie -> ARM assembler.

Changing @ comments to # or GBA macro files BEFORE preproc destroys the
original source grammar. This tool stores the actual preprocessor output in
a temporary, private directory; after that step, the native build may adapt
the original assembly macros to host GAS for the final assembler.
No text, sprite, script or binary content is invented or replaced.
"""
import argparse
import json
from pathlib import Path
import subprocess


def _run(argv, world, input_bytes=None):
    return subprocess.run(argv, input=input_bytes, capture_output=True,
                          cwd=world, timeout=120)


def prepare(world, output):
    world, output = Path(world).resolve(), Path(output).resolve()
    preproc = world / "tools/preproc/preproc"
    if not preproc.is_file() or not (world / "charmap.txt").is_file():
        raise ValueError("authentic World preprocessor and charmap are required")
    sources = sorted((world / "data").glob("*.s"))
    if not sources:
        raise ValueError("no original World data assembly files found")
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for source in sources:
        name = source.relative_to(world).as_posix()
        target = output / source.name
        target.unlink(missing_ok=True)
        row = {"source": name, "prepared": False}
        steps = [
            [str(preproc), "-s", name, "charmap.txt"],
            ["gcc", "-E", "-x", "assembler-with-cpp", "-iquote", "include",
             "-I", ".", "-Wno-trigraphs", "-DMODERN=1", "-DTESTING=0",
             "-DEMERALD=1", "-DALL_REGIONS=1", "-"],
            [str(preproc), "-ie", name, "charmap.txt"],
        ]
        buffer = None
        for index, argv in enumerate(steps):
            try:
                run = _run(argv, world, buffer)
            except (OSError, subprocess.TimeoutExpired) as exc:
                row.update(status="preproc_runtime_error", stage=index,
                           errors=[str(exc)])
                break
            if run.returncode:
                row.update(status="preproc_failed", stage=index,
                           errors=run.stderr.decode(errors="replace").splitlines()[:30])
                break
            buffer = run.stdout
        else:
            target.write_bytes(buffer)
            row.update(status="prepared_original_world_data",
                       prepared=True, bytes=len(buffer))
        records.append(row)
    return {"schema": 1, "stage": "P2_original_GBA_script_preprocessing_before_native_asm",
            "requested": len(sources),
            "prepared": sum(r["prepared"] for r in records),
            "source_data_fabricated": False,
            "GBA_source_modified": False,
            "results": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", default="native-prepared-gba-scripts.json")
    args = parser.parse_args()
    report = prepare(args.world, args.output)
    Path(args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Authentic World ASM prepared:", report["prepared"], "/", report["requested"])
    for item in report["results"]:
        if not item["prepared"]:
            print(item["source"], item["status"], item.get("errors", [])[:3])
    if report["prepared"] != report["requested"]:
        parser.exit(1, "World source preprocessor stage is incomplete; refusing partial native ASM build\n")


if __name__ == "__main__":
    main()
