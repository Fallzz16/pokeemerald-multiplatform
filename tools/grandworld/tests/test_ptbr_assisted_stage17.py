#!/usr/bin/env python3
"""Verify stage 17 assisted PT-BR edits without claiming human review."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOKEN_SPLIT = re.compile(r"\\\\[npl]")
PART_FILES = [f"ptbr_assisted_stage17_part{i}.json" for i in range(1, 4)]
REVIEW_FILES = ["ptbr_reviewed_auto7.json"] + [
    f"ptbr_reviewed_stage{i}.json" for i in range(8, 17)
]


def read_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def assisted_labels():
    entries = {}
    total = 0
    for name in PART_FILES:
        part = read_json(name)
        assert part["stage"] == 17
        assert part["status"] == "machine_assisted_pending_contextual_review_not_human_approved"
        seen_here = 0
        for shard, sources in part["changed_labels_by_shard_and_source"].items():
            for source, labels in sources.items():
                for label in labels:
                    key = (source, label)
                    assert key not in entries, "duplicate assisted label: " + str(key)
                    entries[key] = shard
                    seen_here += 1
        assert seen_here == part["modified_entries"], name
        total += seen_here
    assert total == 1054, f"unexpected assisted text count: {total}"
    return entries


class PTBRAssistedStage17Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = assisted_labels()

    def test_does_not_duplicate_earlier_individual_reviews(self):
        earlier = set()
        for name in REVIEW_FILES:
            data = read_json(name)
            for source, labels in data["reviewed_labels_by_source"].items():
                for label in labels:
                    earlier.add((source, label))
        self.assertFalse(set(self.entries) & earlier)

    def test_modified_strings_are_complete_ascii_and_within_heuristic(self):
        shards = {}
        for (source, label), shard in self.entries.items():
            if shard not in shards:
                shards[shard] = read_json(Path(shard).name)["asm"]
            text = "".join(shards[shard][source][label])
            self.assertTrue(text.isascii(), (source, label))
            self.assertTrue(text.endswith("$"), (source, label))
            self.assertEqual(text.count("$"), 1, (source, label))
            for line in TOKEN_SPLIT.split(text[:-1]):
                visible = re.sub(r"\\{[^{}]+\\}", "XXXXXXXX", line)
                self.assertLessEqual(len(visible), 35, (source, label, visible))

    def test_scope_and_manual_review_remain_distinct(self):
        self.assertEqual(len(self.entries), 1054)
        self.assertEqual(len({shard for shard in self.entries.values()}), 21)
        for name in PART_FILES:
            self.assertNotIn("release_approved", read_json(name))
            self.assertIn("pending_contextual_review", read_json(name)["status"])


if __name__ == "__main__":
    unittest.main()
