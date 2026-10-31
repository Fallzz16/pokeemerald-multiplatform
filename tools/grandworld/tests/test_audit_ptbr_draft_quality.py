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
        self.assertEqual(quality.flags("Fiz {POKEBLOCK}S com minha familia!$"), [])
        self.assertEqual(
            quality.flags("Batalha!{PLAY_BGM}{MUS_RG_ENCOUNTER_GYM_LEADER}$"), [])
        self.assertIn("placeholder_joined_to_word",
                      quality.flags("{PLAYER}recebeu TM.$"))

    def test_registry_and_counts(self):
        report = quality.audit(SCRIPT.parent, example_limit=4)
        self.assertEqual(report["automated_draft_entries"], 5200)
        self.assertEqual(report["human_language_reviewed"], 1064)
        self.assertEqual(report["human_reviewed_stage8"], 239)
        self.assertEqual(report["human_reviewed_stage9"], 328)
        self.assertEqual(report["human_reviewed_stage10"], 117)
        self.assertEqual(report["human_reviewed_stage11"], 170)
        self.assertEqual(report["pending_human_language_review"], 4136)
        self.assertLessEqual(len(report["sample_unreviewed_warnings"]), 4)
        self.assertEqual(report["review_status"],
                         "diagnostic_only_no_gameplay_certification")


if __name__ == "__main__":
    unittest.main()
