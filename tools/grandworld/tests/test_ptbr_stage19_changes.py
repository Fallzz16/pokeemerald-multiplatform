"""Verify stage19 changes are unique and isolated; AI editing is not human approval."""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PARTS = [f"ptbr_stage19_changes_part{i}.json" for i in range(1, 5)]
SOURCE_FILES = ["ptbr_reviewed_auto7.json"] + [
    f"ptbr_reviewed_stage{i}.json" for i in range(8, 17)
]
BREAK = re.compile(r"\\[nlp]")
VARIABLE = re.compile(r"\{[^{}]+\}")


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


class Stage19Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.labels = {}
        cls.counts = []
        for part in PARTS:
            d = load(part)
            n = 0
            for shard, sources in d["changed_labels_by_shard_and_source"].items():
                for src, symbols in sources.items():
                    for label in symbols:
                        key = (src, label)
                        if key in cls.labels:
                            raise ValueError("duplicate stage19 label: " + str(key))
                        cls.labels[key] = shard
                        n += 1
            cls.counts.append(n)
            if n != d["changed_entries"]:
                raise ValueError("stage19 manifest drift: " + part)

    def test_exact_auditable_changes(self):
        self.assertEqual(self.counts, [194, 280, 88, 42])
        self.assertEqual(len(self.labels), 604)
        self.assertEqual(len(set(self.labels.values())), 20)

    def test_previous_reviews_are_frozen(self):
        older = set()
        for name in SOURCE_FILES:
            d = load(name)
            for src, names in d["reviewed_labels_by_source"].items():
                for label in names:
                    key = (src, label)
                    self.assertNotIn(key, older)
                    older.add(key)
        self.assertEqual(len(older), 1962)
        locked = load("ptbr_stage19_prior_review_lock.json")
        snapshot = {(src, label)
                    for src, labels in locked["reviewed_labels_by_source"].items()
                    for label in labels}
        self.assertEqual(older, snapshot)
        self.assertFalse(older.intersection(self.labels))

    def test_ascii_terminator_and_text_heuristics(self):
        shards = {}
        for (src, label), path in self.labels.items():
            if path not in shards:
                shards[path] = load(Path(path).name)["asm"]
            text = "".join(shards[path][src][label])
            self.assertTrue(text.isascii(), (src, label))
            self.assertEqual(text.count("$"), 1, (src, label))
            self.assertTrue(text.endswith("$"), (src, label))
            for chunk in BREAK.split(text[:-1]):
                approximated = VARIABLE.sub("XXXXXXXX", chunk)
                self.assertLessEqual(len(approximated), 35,
                                     (src, label, approximated))

    def test_never_claims_human_approval(self):
        for part in PARTS:
            d = load(part)
            self.assertEqual(
                d["status"],
                "ai_assisted_draft_changes_pending_independent_linguistic_and_gameplay_review",
            )


if __name__ == "__main__":
    unittest.main()
