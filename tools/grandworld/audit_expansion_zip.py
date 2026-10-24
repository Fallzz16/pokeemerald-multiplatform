#!/usr/bin/env python3
"""Read-only audit of an uploaded pokeemerald-expansion ZIP against M8 pilot families."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

def audit(zip_path, pilot_path):
    spec = importlib.util.spec_from_file_location("m8_pilot", pilot_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    selected = tuple(mod.PILOT) + tuple(mod.GEN5_PILOT)
    if len(selected) != 43 or len(set(selected)) != 43:
        raise ValueError("M8 manifest must contain 43 unique family representatives")
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        roots = {p.split("/")[0] for p in names if "/" in p}
        if len(roots) != 1:
            raise ValueError("ZIP must have exactly one source root")
        prefix = next(iter(roots)) + "/"
        def has(path):
            return prefix + path in names
        species = []
        for name in selected:
            base = "graphics/pokemon/" + name.lower() + "/"
            required = ("anim_front.png", "back.png", "icon.png", "normal.pal")
            found = {file: has(base + file) for file in required}
            species.append({"family": name, "assets": found, "representative_complete": all(found.values())})
        targets = {
            "tests_debug": ("src/debug.c",),
            "summary": ("src/pokemon_summary_screen.c", "include/config/summary_screen.h"),
            "map_popups": ("src/map_name_popup.c", "include/map_name_popup.h"),
            "followers": ("src/follower_npc.c", "include/config/follower_npc.h"),
            "hgss_pokedex": ("src/pokedex_plus_hgss.c", "include/config/pokedex_plus_hgss.h"),
        }
        return {
            "source_zip_sha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
            "expected_families": len(selected),
            "complete_representatives": sum(s["representative_complete"] for s in species),
            "species": species,
            "components": {key: {f: has(f) for f in files} for key, files in targets.items()},
            "safe_to_import_directly": False,
            "notes": [
                "No game assets were extracted or redistributed",
                "Representative files do not verify evolutions, forms or palettes in World",
                "No SaveBlock, GBA ABI, runtime, memory or license compatibility proven",
                "M8 verified criteria remain unchanged"
            ],
        }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("zip", type=Path)
    p.add_argument("--pilot", type=Path, default=Path(__file__).with_name("expand_gen4_pilot.py"))
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = audit(args.zip, args.pilot)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Representatives present: {result['complete_representatives']}/43; ROM unchanged")

if __name__ == "__main__":
    main()
