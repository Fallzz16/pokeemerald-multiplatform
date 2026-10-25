"""Regression tests for review-only draft quality diagnostics."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "audit_ptbr_draft_quality.py"
spec = importlib.util.spec_from_file_location("ptbr_draft_quality", SCRIPT)
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


class PTBRDraftQualityTests(unittest.TestCase):
    def test_heuristic_flags(self):
        self.assertIn("possible_pt_europeu", quality.flags("Deves voltar, rapariga."))
        self.assertIn("placeholder_joined_to_word", quality.flags("{PLAYER}recebeu algo."))
        self.assertIn("possible_overflow", quality.flags("A" * 36 + "$"))
        self.assertIn("move_name_order", quality.flags("TM09 tem SEED BULLET.$"))
        self.assertEqual(quality.flags("Voce recebeu TM09: BULLET SEED.$"), [])

    def test_registry_and_counts(self):
        report = quality.audit(SCRIPT.parent, example_limit=4)
        self.assertEqual(report["automated_draft_entries"], 5200)
        self.assertEqual(report["human_language_reviewed"], 210)
        self.assertEqual(report["pending_human_language_review"], 4990)
        self.assertLessEqual(len(report["sample_unreviewed_warnings"]), 4)
        self.assertEqual(report["review_status"],
                         "diagnostic_only_no_gameplay_certification")


if __name__ == "__main__":
    unittest.main()
