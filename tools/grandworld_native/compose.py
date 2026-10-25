#!/usr/bin/env python3
"""Rebuild the pinned, patched Grand World source in a separate checkout.

This only composes sources. It does not claim that a native executable exists.
No edits to existing saves or to the Grand World repository are performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

WORLD_PIN = "15d3888b0d81322a04d3c71b0bce18948761ee44"
PATCHES = (
    ("integrate_world.py", ()),
    ("expand_gen4_pilot.py", ("--apply", "--with-gen5-trial")),
    ("add_hero_profiles.py", ()),
    ("add_kanto_avatar.py", ()),
    ("optimize_overworld_budget.py", ("--apply", "--shadows", "lean")),
    ("apply_grass_only.py", ("--apply",)),
    ("translate_ptbr_stage1.py", ("--apply",)),
    ("adapt_ptbr_greedy_gifts_qa.py", ("--apply",)),
    ("adapt_ptbr_healthboxes_qa.py", ("--apply",)),
)

def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

def check_source(world, grandworld):
    if not (world / "src" / "region_switch.c").is_file():
        raise RuntimeError("World source checkout is missing src/region_switch.c")
    if not (grandworld / "tools" / "grandworld" / "integrate_world.py").is_file():
        raise RuntimeError("Grand World patch scripts are missing")
    if git(world, "rev-parse", "HEAD") != WORLD_PIN:
        raise RuntimeError("World checkout does not match pinned commit")
    if git(world, "status", "--porcelain", "--untracked-files=normal"):
        raise RuntimeError("World checkout is not clean; refusing to overwrite changes")

def make_commands(world, grandworld):
    patches = grandworld / "tools" / "grandworld"
    return [[sys.executable, str(patches / name), str(world), *flags] for name, flags in PATCHES]

def compose(world, grandworld, report, apply):
    world = Path(world).resolve()
    grandworld = Path(grandworld).resolve()
    check_source(world, grandworld)
    commands = make_commands(world, grandworld)
    record = {
        "schema": 1,
        "stage": "P0_source_composition",
        "world_source_sha": WORLD_PIN,
        "grandworld_source_sha": git(grandworld, "rev-parse", "HEAD"),
        "patches": [name for name, _ in PATCHES],
        "apply_requested": apply,
        "patches_applied": False,
        "native_build_passed": False,
        "gameplay_verified": False,
    }
    if apply:
        # Abort at the first error. The directory is an expendable checkout,
        # never the original and never a directory containing player saves.
        for command in commands:
            subprocess.run(command, check=True)
        record["patches_applied"] = True
        record["changed_files"] = git(world, "status", "--porcelain").splitlines()
        digest = hashlib.sha256()
        for name in ("src/main_menu.c", "src/region_switch.c", "data/maps/RegionHub/scripts.inc"):
            p = world / name
            digest.update(name.encode("utf-8"))
            digest.update(p.read_bytes())
        record["source_sample_sha256"] = digest.hexdigest()
    Path(report).parent.mkdir(parents=True, exist_ok=True)
    Path(report).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return record

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", required=True, help="disposable pinned World checkout")
    parser.add_argument("--grandworld", default=".", help="Grand World repository checkout")
    parser.add_argument("--report", default="native-compose-report.json")
    parser.add_argument("--apply", action="store_true", help="apply all patches to disposable World tree")
    args = parser.parse_args()
    try:
        print(json.dumps(compose(args.world, args.grandworld, args.report, args.apply), indent=2))
    except (RuntimeError, subprocess.CalledProcessError, OSError) as exc:
        parser.exit(1, "Grand World native source composition failed: %s\n" % exc)

if __name__ == "__main__":
    main()
