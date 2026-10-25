#!/usr/bin/env python3
"""Audit human-review risks in PT-BR drafts without altering game sources."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

EUROPEAN = re.compile(
    r"\b(?:rapariga|raparigas|ganhaste|fizeste|perdeste|estiveste|"
    r"derrotaste|voltaste|queres|podes|deves|devias|tens|teu|tua|"
    r"vosso|vossa|fixe|fixes|giro|gira|miudos|miudas|esplendido|"
    r"estais|connosco|convosco)\b", re.IGNORECASE)
ENGLISH = re.compile(
    r"\b(?:you're|you've|your|would|should|don't|please|thanks|hello|goodbye)\b",
    re.IGNORECASE)
GLUED = re.compile(r"\}(?=[A-Za-z])")
BREAK = re.compile(r"\\[npl]")


def flags(value):
    result = []
    if EUROPEAN.search(value):
        result.append("possible_pt_europeu")
    if ENGLISH.search(value):
        result.append("possible_english_residue")
    if GLUED.search(value):
        result.append("placeholder_joined_to_word")
    if "SEED BULLET" in value:
        result.append("move_name_order")
    if any(len(re.sub(r"\{[^{}]+\}", "XXXXXXXX", line)) > 35
           for line in BREAK.split(value.rstrip("$"))):
        result.append("possible_overflow")
    return result


def audit(root, example_limit=150):
    root = Path(root)
    index = json.loads((root / "ptbr_auto_review_index.json").read_text())
    registry = json.loads((root / "ptbr_reviewed_auto7.json").read_text())
    reviewed = {(source, symbol)
                for source, labels in registry["reviewed_labels_by_source"].items()
                for symbol in labels}
    found = set()
    issues = Counter()
    by_file = defaultdict(Counter)
    examples = []
    entries = 0
    for shard in index["shards"]:
        batch = json.loads((root / shard).read_text(encoding="utf-8"))
        for rel, texts in batch.get("asm", {}).items():
            for symbol, parts in texts.items():
                key = rel, symbol
                if key in found:
                    raise ValueError("duplicate draft label: " + repr(key))
                found.add(key)
                entries += 1
                if key in reviewed:
                    continue
                for kind in flags("".join(parts)):
                    issues[kind] += 1
                    by_file[rel][kind] += 1
                    if len(examples) < example_limit:
                        examples.append({"file": rel, "symbol": symbol,
                                         "reason": kind})
    missing = reviewed - found
    if missing:
        raise ValueError("review registry references missing drafts: " +
                         repr(sorted(missing)[:3]))
    if entries != index["added_entries"]:
        raise ValueError("draft count drift: %d != %d" %
                         (entries, index["added_entries"]))
    if len(reviewed) != registry["reviewed_auto_entries"]:
        raise ValueError("review registry count drift")
    return {
        "review_status": "diagnostic_only_no_gameplay_certification",
        "automated_draft_entries": entries,
        "human_language_reviewed": len(reviewed),
        "pending_human_language_review": entries - len(reviewed),
        "heuristic_warnings": dict(issues),
        "warning_counts_by_file": {k: dict(v) for k, v in by_file.items()},
        "sample_unreviewed_warnings": examples,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-dir", type=Path,
                        default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.manifest_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("warning_counts_by_file",
                                   "sample_unreviewed_warnings")}, indent=2))


if __name__ == "__main__":
    main()
