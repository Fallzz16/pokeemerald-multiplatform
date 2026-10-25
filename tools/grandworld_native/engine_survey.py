#!/usr/bin/env python3
"""P2: survey real World/M8 native C source beyond the initial gameplay slice.

Reuses the ORIGINAL World preproc and generated real assets. Collects up to N
source files, preserving deterministic order. Successful object compilation is
not equivalent to a complete Windows game link/boot.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

try:
    from . import engine_probe
except ImportError:
    import engine_probe


def survey(world, objects, limit=120):
    world = Path(world).resolve()
    if limit < len(engine_probe.SOURCES) or limit > 500:
        raise ValueError("limit must cover initial slice and be <= 500")
    present = {p.name for p in (world / "src").glob("*.c")}
    preferred = [p for p in engine_probe.SOURCES if p in present]
    remaining = sorted(p for p in present if p not in preferred)
    selected = (preferred + remaining)[:limit]
    original = engine_probe.SOURCES
    try:
        engine_probe.SOURCES = tuple(selected)
        data = engine_probe.compile_engine(world, objects, use_preproc=True)
    finally:
        engine_probe.SOURCES = original
    categories = Counter()
    for row in data["objects"]:
        if row["status"] != "object_compiled":
            problem = next((x for x in row.get("errors", [])
                            if "error:" in x or "fatal" in x), "unclassified")
            categories[problem.rsplit("error:",1)[-1].strip()[:110]] += 1
    data["stage"] = "P2_extended_real_world_source_survey"
    data["total_available_c_sources"] = len(present)
    data["first_errors"] = categories.most_common(25)
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--objects", default="native-world-survey-objects")
    p.add_argument("--report", default="native-world-survey.json")
    p.add_argument("--limit", type=int, default=120)
    args = p.parse_args()
    data = survey(args.world, args.objects, args.limit)
    Path(args.report).write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
    print("REAL M8 NATIVE COMPILER SURVEY:", data["compiled"], "/", data["requested"],
          "objects compiled,", data["total_available_c_sources"], "C sources available")
    for x in data["objects"]:
        if x["status"] != "object_compiled":
            print(x["source"], x["status"], " | ", next(
                (err for err in x.get("errors",[]) if "error:" in err), "Unknown"))
    print("No claim of gameplay, native engine link or save compatibility.")

if __name__ == "__main__":
    main()
