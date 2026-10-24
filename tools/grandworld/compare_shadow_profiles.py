#!/usr/bin/env python3
"""Compare *identical-source* GBA shadow build metrics, not runtime FPS."""
import argparse
import json
from pathlib import Path

KEYS = ("ROM", "EWRAM", "IWRAM")


def evaluate(lean_profile, full_profile, lean_budget, full_budget, lean_lz, full_lz):
    if lean_profile.get("resolved_shadow_mode") != "lean":
        raise ValueError("lean profile mismatch")
    if full_profile.get("resolved_shadow_mode") != "full":
        raise ValueError("full profile mismatch")
    for label, budget, lz in (("lean", lean_budget, lean_lz), ("full", full_budget, full_lz)):
        if budget.get("game_code") != "BPEE" or not budget.get("memory_budget_passed"):
            raise ValueError(label + " ROM hardware budget not verified")
        if budget.get("rom_sha256") != lz.get("sha256"):
            raise ValueError(label + " budget/LZ77 metrics are from different ROMs")
        if lz.get("rom_bytes") != budget.get("rom_bytes"):
            raise ValueError(label + " ROM size disagrees across metrics")
        memory = budget.get("linker_memory_bytes")
        if not isinstance(memory, dict) or set(memory) != set(KEYS):
            raise ValueError(label + " incomplete memory fields")
        if any(type(memory[k]) is not int for k in KEYS):
            raise ValueError(label + " invalid memory value types")
    delta = {key: full_budget["linker_memory_bytes"][key] -
                  lean_budget["linker_memory_bytes"][key] for key in KEYS}
    compressed = ("referenced_lz77_streams", "referenced_stream_stored_bytes",
                  "referenced_stream_expanded_bytes")
    return {
        "experiment": "same pinned PKMN-World and Grand World integration; O2 only; shadow flag is the variable",
        "lean_rom_sha256": lean_budget["rom_sha256"],
        "full_rom_sha256": full_budget["rom_sha256"],
        "lean_memory_bytes": lean_budget["linker_memory_bytes"],
        "full_memory_bytes": full_budget["linker_memory_bytes"],
        "full_minus_lean_memory_bytes": delta,
        "full_minus_lean_referenced_lz77": {
            key: full_lz[key] - lean_lz[key] for key in compressed
        },
        "shadows_are_compile_time_configurable": True,
        "in_game_shadow_toggle_implemented": False,
        "compression_runtime_policy_modified": False,
        "fps_measured": False,
        "oam_runtime_occupancy_compared": False,
        "aesthetic_quality_certified": False,
        "notes": "Compilation/memory and asset comparison only. Evaluate both profiles in mGBA/hardware before shipping.",
    }


def load(path):
    result = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError("comparison input must be a JSON object")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("lean_profile", "full_profile", "lean_budget", "full_budget", "lean_lz", "full_lz"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(*(load(getattr(args, key)) for key in
                        ("lean_profile", "full_profile", "lean_budget",
                         "full_budget", "lean_lz", "full_lz")))
    data = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(data, encoding="utf-8")
    print(data, end="")


if __name__ == "__main__":
    main()
