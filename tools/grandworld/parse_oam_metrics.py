#!/usr/bin/env python3
"""Parse real mGBA hardware OAM samples (not a CPU/FPS benchmark)."""
import argparse
import hashlib
import json
from pathlib import Path
import re

PATTERN = re.compile(
    r"OAM_METRIC scenario=([a-z_]+) frames=(\d+) active_min=(\d+) active_max=(\d+) active_avg=(\d+\.\d+)"
)


def report(log, rom):
    seen = {}
    for scenario, frames_s, min_s, max_s, avg_s in PATTERN.findall(log):
        frames, low, high, avg = int(frames_s), int(min_s), int(max_s), float(avg_s)
        if scenario in seen:
            raise ValueError("duplicated OAM scenario in mGBA log")
        if frames < 60 or not 0 <= low <= avg + 0.001 <= high + 0.001 <= 128:
            raise ValueError("invalid OAM hardware sample values")
        seen[scenario] = {
            "frames": frames,
            "active_min": low,
            "active_max": high,
            "active_average": avg,
            "free_sprite_slots_at_peak": 128 - high,
        }
    if set(seen) != {"hub_idle", "hub_after_movement"}:
        raise ValueError(f"missing required mGBA OAM scenarios: {sorted(seen)}")
    if not re.search(r"VERDICT GrandWorldOamBudget: [1-9]\d*/[1-9]\d* PASS", log):
        raise ValueError("missing successful suite verdict in mGBA log")
    return {
        "rom_sha256": hashlib.sha256(rom).hexdigest(),
        "scenarios": seen,
        "hardware_oam_slots": 128,
        "fps_measured": False,
        "cpu_cycles_measured": False,
        "notes": "Enabled OAM object count measured over actual emulated frames. A one-frame occupancy peak is not FPS proof.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("rom", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = report(args.log.read_text(encoding="utf-8"), args.rom.read_bytes())
    data = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(data, encoding="utf-8")
    print(data, end="")


if __name__ == "__main__":
    main()
