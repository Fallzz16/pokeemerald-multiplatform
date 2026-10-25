#!/usr/bin/env python3
"""Audit native compilation of genuine World/M8 generated MIDI song assembly.

The World GBA build first runs mid2agb on sound/songs/midi/*.mid, producing
matching .s files. This audit only uses those authentic generated sources,
never invents or substitutes music, and records which host objects compile.
No produced object is automatically treated as a playable game asset.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

try:
    from .gba_data_asm_overlay import transform_text
except ImportError:
    from gba_data_asm_overlay import transform_text


def inspect(world, objects, limit=24, compiler="gcc"):
    world, objects = Path(world).resolve(), Path(objects).resolve()
    if not 1 <= limit <= 1000:
        raise ValueError("song audit limit must be 1..1000")
    cc = shutil.which(compiler)
    if not cc:
        raise ValueError("host GCC not installed")
    midi_dir = world / "sound/songs/midi"
    inputs = sorted(midi_dir.glob("*.mid"))
    selected = inputs[:limit]
    objects.mkdir(parents=True, exist_ok=True)
    results = []
    for mid in selected:
        source = mid.with_suffix(".s")
        dest = objects / (mid.stem + ".o")
        dest.unlink(missing_ok=True)
        entry = {"source": source.relative_to(world).as_posix(),
                 "midi": mid.relative_to(world).as_posix(),
                 "object": dest.name, "native_object": False}
        if not source.is_file():
            entry.update(status="missing_generated_midi_assembly",
                         errors=["World must generate .s from original MIDI first"])
            results.append(entry)
            continue
        try:
            original = source.read_text(encoding="utf-8", errors="surrogateescape")
            normalized, changes = transform_text(original)
            # Host GAS reads transformed text from stdin. MPlayDef, sample and
            # voicegroup includes still refer to real World files only.
            cmd = [cc, "-m32", "-x", "assembler", "-c", "-",
                   "-I", "sound", "-I", ".", "-o", str(dest)]
            done = subprocess.run(cmd, input=normalized.encode("utf-8", errors="surrogateescape"),
                                  cwd=world, capture_output=True, timeout=75)
            if done.returncode == 0 and dest.is_file():
                entry.update(status="native_object_compiled", native_object=True,
                             bytes=dest.stat().st_size)
            else:
                dest.unlink(missing_ok=True)
                entry.update(status="native_assembly_failed",
                             errors=done.stderr.decode(errors="replace").splitlines()[:40])
            entry["directive_changes"] = changes
        except (OSError, UnicodeError, subprocess.TimeoutExpired, ValueError) as exc:
            dest.unlink(missing_ok=True)
            entry.update(status="probe_exception", errors=[str(exc)])
        results.append(entry)
    return {"schema": 1, "stage": "P2_authentic_generated_MIDI_native_assembly",
            "available_original_midi": len(inputs),
            "requested": len(selected),
            "compiled": sum(e["native_object"] for e in results),
            "content_replaced_or_fabricated": False,
            "linked_into_game": False,
            "results": results}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--objects", default="native-world-music-objects")
    p.add_argument("--limit", type=int, default=24)
    p.add_argument("--report", default="native-original-music-asm.json")
    args = p.parse_args()
    result = inspect(args.world, args.objects, args.limit)
    Path(args.report).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Original M8 songs compiled:", result["compiled"], "/", result["requested"],
          "of", result["available_original_midi"], "available MIDIs")
    for item in result["results"]:
        if not item["native_object"]:
            print(item["source"], item["status"], " | ".join(item.get("errors", [])[:3]))
    print("Not a native game link or gameplay proof.")


if __name__ == "__main__":
    main()
