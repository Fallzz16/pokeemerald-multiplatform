#!/usr/bin/env python3
"""Guard AI-editorial Stage 18 PT-BR edits without claiming human sign-off."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PARTS = [f"ptbr_editorial_stage18_part{i}.json" for i in (1, 2, 3)]
OLD_REVIEWS = ["ptbr_reviewed_auto7.json"] + [
    f"ptbr_reviewed_stage{i}.json" for i in range(8, 17)
]
STAGE17_PARTS = [f"ptbr_assisted_stage17_part{i}.json" for i in (1, 2, 3)]
CONTROL_BREAK = re.compile(r"\\[npl]")
VARIABLE = re.compile(r"\{[^{}]+\}")


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def flatten(manifests, key):
    seen = {}
    totals = []
    for name in manifests:
        manifest = load(name)
        labels = manifest[key]
        local = 0
        for shard, sources in labels.items():
            for source, names in sources.items():
                for symbol in names:
                    identity = (source, symbol)
                    if identity in seen:
                        raise ValueError(f"duplicate stage label {identity}")
                    seen[identity] = shard
                    local += 1
        totals.append((manifest, local))
    return seen, totals


class PTBREditorialStage18Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.editorial, cls.parts = flatten(PARTS, "changed_labels_by_shard_and_source")
        cls.assisted, _ = flatten(STAGE17_PARTS, "changed_labels_by_shard_and_source")
        cls.prior = set()
        for filename in OLD_REVIEWS:
            for source, names in load(filename)["reviewed_labels_by_source"].items():
                cls.prior.update((source, symbol) for symbol in names)

    def test_exact_count_and_coverage(self):
        self.assertEqual(len(self.editorial), 135)
        self.assertEqual([m["entries"] for m, _ in self.parts], [71, 46, 18])
        self.assertEqual(len({shard for shard in self.editorial.values()}), 13)
        self.assertEqual([m["part"] for m, _ in self.parts], [1, 2, 3])
        self.assertTrue(all(m["stage"] == 18 for m, _ in self.parts))
        self.assertTrue(all(n == m["entries"] for m, n in self.parts))

    def test_editorial_does_not_rewrite_previous_reviewed_entries(self):
        self.assertFalse(set(self.editorial).intersection(self.prior))

    def test_editorial_vs_assisted_are_not_double_counted(self):
        assisted = set(self.assisted)
        reviewed_again = set(self.editorial) & assisted
        newly_touched = set(self.editorial) - assisted
        self.assertEqual(len(reviewed_again), 65)
        self.assertEqual(len(newly_touched), 70)
        self.assertEqual(
            [m["previously_assisted_stage17"] for m, _ in self.parts],
            [36, 17, 12],
        )
        self.assertEqual(
            [m["previously_untouched_by_stage17"] for m, _ in self.parts],
            [35, 29, 6],
        )

    def test_edited_text_is_complete_and_conservatively_formatted(self):
        cache = {}
        for (source, symbol), shard in self.editorial.items():
            if shard not in cache:
                cache[shard] = load(Path(shard).name)["asm"]
            text = "".join(cache[shard][source][symbol])
            self.assertTrue(text.isascii(), (source, symbol))
            self.assertEqual(text.count("$"), 1, (source, symbol))
            self.assertTrue(text.endswith("$"), (source, symbol))
            for chunk in CONTROL_BREAK.split(text[:-1]):
                approx = VARIABLE.sub("XXXXXXXX", chunk)
                self.assertLessEqual(len(approx), 35, (source, symbol, approx))

    def test_no_false_claim_of_human_approval(self):
        for manifest, _ in self.parts:
            self.assertEqual(
                manifest["status"],
                "editorial_ai_rewrite_pending_independent_linguistic_and_visual_review",
            )


if __name__ == "__main__":
    unittest.main()
