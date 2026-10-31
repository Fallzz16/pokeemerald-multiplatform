#!/usr/bin/env python3
"""Prioritize remaining PT-BR dialogue debt; never mark assisted edits approved."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
EUROPEAN = re.compile(
    r"\b(?:queres|tens|teu|tua|contigo|convosco|connosco|vais|podes|"
    r"deves|devias|es|rapariga|miudo|equipa|equipas|registo|registar|"
    r"giro|fixe|fizeste|ganhaste|estiveste|apanhar|coleccionar|"
    r"conseguiste|ouviste|estou a|esta a|estamos a)\b", re.IGNORECASE
)
ENGLISH = re.compile(
    r"\b(?:you're|you've|please|yourself|the|thanks|goodbye|"
    r"hello|have to|would|should|don't)\b", re.IGNORECASE
)
JOINED_VAR = re.compile(r"\}(?=[a-zA-Z])")
PLACEHOLDER = re.compile(r"\{[^{}]+\}")
BREAK = re.compile(r"\\[npl]")
STORY = re.compile(r"(League|Gym|Rival|Rocket|Aqua|Magma|Story|"
                   r"Legend|Champion|Elite|Starter|Professor|Region)", re.I)


def read_json(root, name):
    return json.loads((root / name).read_text(encoding="utf-8"))


def labels_from_review(root, names):
    result = set()
    for name in names:
        manifest = read_json(root, name)
        for src, labels in manifest["reviewed_labels_by_source"].items():
            for label in labels:
                key = (src, label)
                if key in result:
                    raise ValueError("duplicate review entry: " + repr(key))
                result.add(key)
    return result


def labels_from_parts(root, prefix, count):
    result = set()
    for i in range(1, count + 1):
        entry = read_json(root, f"{prefix}_part{i}.json")
        per_part = 0
        for sources in entry["changed_labels_by_shard_and_source"].values():
            for src, labels in sources.items():
                for label in labels:
                    key = (src, label)
                    if key in result:
                        raise ValueError("duplicate assisted/editorial entry: " + repr(key))
                    result.add(key)
                    per_part += 1
        expected = entry["modified_entries" if "assisted" in prefix else "entries"]
        if per_part != expected:
            raise ValueError("manifest count mismatch: " + prefix)
    return result


def classify(text, path, symbol):
    issues = []
    if not text.isascii():
        issues.append("non_ascii")
    if text.count("$") != 1 or not text.endswith("$"):
        issues.append("invalid_terminator")
    if JOINED_VAR.search(re.sub(r"\{POKEBLOCK\}S\b", "POKEBLOCKS", text)):
        issues.append("placeholder_joined_to_word")
    if EUROPEAN.search(text):
        issues.append("pt_pt_grammar")
    if ENGLISH.search(text):
        issues.append("english_residue")
    chunks = BREAK.split(text.rstrip("$"))
    if any(len(PLACEHOLDER.sub("XXXXXXXX", chunk)) > 35 for chunk in chunks):
        issues.append("possible_text_overflow")
    if STORY.search(path + "/" + symbol):
        issues.append("story_or_major_event")
    critical = {"non_ascii", "invalid_terminator", "placeholder_joined_to_word",
                "possible_text_overflow"}
    severity = (3 * len(critical.intersection(issues))
                + 2 * len({"pt_pt_grammar", "english_residue"}.intersection(issues))
                + int("story_or_major_event" in issues))
    return issues, severity


def build(root=ROOT):
    root = Path(root)
    index = read_json(root, "ptbr_auto_review_index.json")
    human = labels_from_review(
        root, ["ptbr_reviewed_auto7.json"] +
        [f"ptbr_reviewed_stage{i}.json" for i in range(8, 17)]
    )
    assisted = labels_from_parts(root, "ptbr_assisted_stage17", 3)
    editorial = labels_from_parts(root, "ptbr_editorial_stage18", 3)
    if human & (assisted | editorial):
        raise ValueError("review status overlap")
    if len(human) != 1962 or len(assisted) != 1053 or len(editorial) != 135:
        raise ValueError("unexpected historical translation registry counts")
    result = []
    seen = set()
    for shard in index["shards"]:
        data = read_json(root, shard)
        for src, entries in data["asm"].items():
            for symbol, fragments in entries.items():
                key = (src, symbol)
                if key in seen:
                    raise ValueError("duplicate source symbol: " + repr(key))
                seen.add(key)
                value = "".join(fragments)
                status = ("previously_reviewed" if key in human else
                          "editorial_ai_pending_approval" if key in editorial else
                          "assisted_pending_editorial" if key in assisted else
                          "untouched_by_stages_17_18")
                issues, severity = classify(value, src, symbol)
                result.append({
                    "source": src,
                    "symbol": symbol,
                    "shard": shard,
                    "status": status,
                    "priority": severity,
                    "issues": issues,
                    "text": value,
                })
    if len(result) != index["added_entries"] or not (human | assisted | editorial).issubset(seen):
        raise ValueError("draft count drift")
    pending = [r for r in result if r["status"] != "previously_reviewed"]
    pending.sort(key=lambda item: (-item["priority"], item["source"], item["symbol"]))
    counts = Counter(item["status"] for item in result)
    warnings = Counter(flag for item in pending for flag in item["issues"])
    expected = {
        "previously_reviewed": 1962,
        "editorial_ai_pending_approval": 135,
        "assisted_pending_editorial": 988,
        "untouched_by_stages_17_18": 2115,
    }
    if dict(counts) != expected:
        raise ValueError("review queue classification drift: " + repr(counts))
    return {
        "purpose": "quality_triage_only; not a human-approved translation",
        "total_drafts": len(result),
        "status_counts": dict(counts),
        "warning_counts": dict(warnings),
        "pending_queue": pending,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-dir", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = build(args.manifest_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "total_drafts": output["total_drafts"],
        "status_counts": output["status_counts"],
        "warning_counts": output["warning_counts"],
        "queued": len(output["pending_queue"]),
    }, indent=2))


if __name__ == "__main__":
    main()
