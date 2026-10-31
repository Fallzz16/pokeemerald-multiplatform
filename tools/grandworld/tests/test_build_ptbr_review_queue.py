"""Validate risk-based PT-BR review queue status, never treating AI edits as approval."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "build_ptbr_review_queue.py"
spec = spec_from_file_location("ptbr_queue", MODULE)
queue = module_from_spec(spec)
spec.loader.exec_module(queue)


class PTBRReviewQueueTests(unittest.TestCase):
    def test_quality_flags(self):
        flags, priority = queue.classify(
            "{PLAYER}recebeu isso. Queres mais?$", "data/maps/Test/scripts.inc",
            "Text_TrainerIntro",
        )
        self.assertIn("placeholder_joined_to_word", flags)
        self.assertIn("pt_pt_grammar", flags)
        self.assertIn("story_or_major_event", flags)
        self.assertGreaterEqual(priority, 6)
        clean, score = queue.classify(
            "Voce ganhou uma INSIGNIA!$", "data/maps/Route1/scripts.inc",
            "Text_Greeting",
        )
        self.assertEqual(clean, [])
        self.assertEqual(score, 0)

    def test_complete_prioritized_queue(self):
        result = queue.build()
        self.assertEqual(result["total_drafts"], 5200)
        self.assertEqual(result["status_counts"]["previously_reviewed"], 1962)
        self.assertEqual(result["status_counts"]["editorial_ai_pending_approval"], 135)
        self.assertEqual(result["status_counts"]["assisted_pending_editorial"], 988)
        self.assertEqual(result["status_counts"]["untouched_by_stages_17_18"], 2115)
        self.assertEqual(len(result["pending_queue"]), 3238)
        priorities = [item["priority"] for item in result["pending_queue"]]
        self.assertEqual(priorities, sorted(priorities, reverse=True))
        self.assertEqual(len({
            (item["source"], item["symbol"]) for item in result["pending_queue"]
        }), 3238)
        self.assertIn("not a human-approved translation", result["purpose"])


if __name__ == "__main__":
    unittest.main()
