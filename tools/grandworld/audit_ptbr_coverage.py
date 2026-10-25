#!/usr/bin/env python3
"""Inventory the static GBA text surface instead of inventing a % translated.

Includes all data/maps/*/scripts.inc labels, data/text/*.inc labels and
C _() literals in the files currently localized. Dynamic/generated text,
image lettering and scripts outside these paths are intentionally excluded.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import translate_ptbr_stage1 as pt

LABEL = re.compile(r"^([A-Za-z_]\w*)::?\s*$", re.M)
STRING = re.compile(r'(?m)^\s*\.string\s+"(?:\\.|[^"\\])*"\s*$')
CSTRING = re.compile(r'\b((?:gText|gMenuText|sText)_[A-Za-z0-9_]+)\[\]\s*=\s*_\("')
MACRO = re.compile(r"\{[^{}]+\}")


def scan_asm(path):
    content = path.read_text(encoding="utf-8")
    headers = list(LABEL.finditer(content))
    definitions = set()
    for idx, match in enumerate(headers):
        end = headers[idx + 1].start() if idx + 1 < len(headers) else len(content)
        if STRING.search(content, match.end(), end):
            definitions.add(match.group(1))
    return definitions


def scan_c(path):
    return set(CSTRING.findall(path.read_text(encoding="utf-8")))


def inventory(world):
    world = Path(world)
    if not (world / "Makefile").is_file():
        raise ValueError("World checkout missing")
    asm_paths = sorted((world / "data/maps").glob("*/scripts.inc"))
    asm_paths += sorted((world / "data/text").glob("*.inc"))
    c_paths = [world / path for path in pt.C_SECTIONS]
    translated = set()
    expected = {}
    for rel, rows in pt.ASM_SECTIONS.items():
        expected[rel] = set(rows)
    for rel, rows in pt.C_SECTIONS.items():
        expected[rel] = set(rows)
    details = defaultdict(lambda: {"defined": 0, "translated": 0, "pending": 0})
    missing_anchors = []
    biggest_pending = []
    totals = {"defined": 0, "translated": 0, "pending": 0}
    for path in asm_paths + c_paths:
        rel = str(path.relative_to(world))
        available = scan_c(path) if path.suffix == ".c" else scan_asm(path)
        claimed = expected.get(rel, set())
        not_found = claimed - available
        if not_found:
            missing_anchors.append({"file": rel, "symbols": sorted(not_found)})
        covered = available & claimed
        pending = available - claimed
        group = ("c_sources" if path.suffix == ".c" else
                 "common_text" if rel.startswith("data/text/") else
                 "overworld_map_text")
        details[group]["defined"] += len(available)
        details[group]["translated"] += len(covered)
        details[group]["pending"] += len(pending)
        for key in totals:
            totals[key] += {"defined": len(available), "translated": len(covered), "pending": len(pending)}[key]
        if len(pending) >= 10:
            biggest_pending.append({"file": rel, "pending": len(pending),
                                    "examples": sorted(pending)[:6]})
        translated.update((rel, label) for label in covered)
    if missing_anchors:
        raise ValueError("translated source symbols missing: " + str(missing_anchors[:5]))
    # Exact total is calculated from source labels, not from Word/ROM file size.
    if totals["translated"] != sum(len(d) for d in expected.values()):
        raise ValueError("translation total does not match manifest")
    return {
        "scope": "ASM static .string labels under data/text + data/maps; C _() declarations in localized C files",
        "limitations": "Not a whole-game coverage percentage: missing generated text, images and other C sources",
        "locale": "pt-BR ASCII, no accents",
        "totals": totals,
        "translation_entries": totals["translated"],
        "by_group": dict(details),
        "top_pending_files": sorted(biggest_pending, key=lambda x: -x["pending"])[:35],
        "untranslated_entries_remain": totals["pending"] > 0,
        "release_approved": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inventory(args.world)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"totals": result["totals"], "by_group": result["by_group"]}, indent=2))


if __name__ == "__main__":
    main()
