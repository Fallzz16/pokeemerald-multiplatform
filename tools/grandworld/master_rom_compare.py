#!/usr/bin/env python3
"""Compare genuine ARM linker footprints for independent Grand World GBA builds.

ROM filesize is padded to 32 MiB and MUST NOT be used as a savings metric.
This tool never edits a ROM, changes save data, strips species, or removes assets.
"""
import argparse
import json
from pathlib import Path
import sys

CAPACITY = {"ROM": 32 * 1024 * 1024, "EWRAM": 256 * 1024, "IWRAM": 32 * 1024}
RESERVE = {"ROM": 1024 * 1024, "EWRAM": 8 * 1024, "IWRAM": 2 * 1024}


def _validate(data, label):
    if not isinstance(data, dict) or not data.get("rom_sha256"):
        raise ValueError(f"{label}: missing provenance hash")
    if data.get("rom_bytes") != CAPACITY["ROM"]:
        raise ValueError(f"{label}: expected a real 32 MiB padded GBA image")
    if data.get("memory_budget_passed") is not True:
        raise ValueError(f"{label}: memory budget not passed")
    used = data.get("linker_memory_bytes")
    free = data.get("free_bytes")
    if not isinstance(used, dict) or not isinstance(free, dict):
        raise ValueError(f"{label}: missing linker memory evidence")
    for region, capacity in CAPACITY.items():
        amount = used.get(region)
        remainder = free.get(region)
        if type(amount) is not int or type(remainder) is not int:
            raise ValueError(f"{label}: {region} not a measured integer")
        if not 0 <= amount <= capacity or remainder != capacity - amount:
            raise ValueError(f"{label}: {region} inconsistent with physical hardware")
        if remainder < RESERVE[region]:
            raise ValueError(f"{label}: {region} below safety reserve")
    return used, free


def compare(baseline, candidate):
    base_used, base_free = _validate(baseline, "baseline")
    new_used, new_free = _validate(candidate, "candidate")
    if baseline["rom_sha256"] == candidate["rom_sha256"]:
        raise ValueError("same ROM hash: cannot claim an independent optimization build")
    changes = {key: {
        "before_bytes": base_used[key], "after_bytes": new_used[key],
        "bytes_saved": base_used[key] - new_used[key],
        "remaining_bytes": new_free[key],
        "safety_reserve_bytes": RESERVE[key],
    } for key in CAPACITY}
    return {
        "kind": "measured_linker_memory_comparison",
        "baseline_sha256": baseline["rom_sha256"],
        "candidate_sha256": candidate["rom_sha256"],
        "capacity_bytes": CAPACITY,
        "memory": changes,
        "rom_bytes_saved": changes["ROM"]["bytes_saved"],
        "rom_saving_percent_of_baseline": round(100 * changes["ROM"]["bytes_saved"] / base_used["ROM"], 4),
        "smaller_rom_payload": new_used["ROM"] < base_used["ROM"],
        "no_ewram_iwram_static_regression": all(new_used[k] <= base_used[k] for k in ("EWRAM", "IWRAM")),
        "reserves_preserved": all(new_free[k] >= RESERVE[k] for k in CAPACITY),
        "gameplay_proved_by_this_report": False,
        "fps_measured_by_this_report": False,
        "save_compatibility_proved_by_this_report": False,
        "ready_for_master": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline", type=Path)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    try:
        first = json.loads(args.baseline.read_text(encoding="utf-8"))
        second = json.loads(args.candidate.read_text(encoding="utf-8"))
        result = compare(first, second)
    except (OSError, ValueError, KeyError, ZeroDivisionError) as error:
        sys.exit("FAIL CLOSED: " + str(error))
    output = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
