"""Synthetic fixture tests for the strict localized-ROM mGBA evidence gate.

Fixture stamps are NOT gameplay proof; only CI's actual mGBA run can provide it.
"""
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import audit_ptbr_m8_gameplay as qa


class PtbrM8GameplayEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.world = Path(self.tmp.name)
        self.stamps = self.world / "_pwtest"
        self.stamps.mkdir()
        self.md5 = "A" * 32

    def stamp(self, suite, checks, md5=None):
        (self.stamps / (suite + ".PASS")).write_text(
            f"PASS {checks}/{checks} rom={md5 or self.md5} "
            f"at=2026-10-25T01:00:00Z suite={suite}\n", encoding="utf-8"
        )

    def all_pass(self):
        for suite, checks in qa.SUITES:
            self.stamp(suite, checks)

    def test_all_thirteen_exact_rom_suites_are_required(self):
        self.assertEqual(len(qa.SUITES), 13)
        self.assertEqual(len({name for name, _ in qa.SUITES}), 13)
        self.assertEqual(sum(count for _, count in qa.SUITES), 813)
        self.assertEqual(
            {name for name, _ in qa.SUITES if name.startswith("GrandWorldSave")},
            {"GrandWorldSaveBrendan", "GrandWorldSaveMay", "GrandWorldSaveRed",
             "GrandWorldSaveLeaf", "GrandWorldSaveEthan", "GrandWorldSaveLyra"}
        )
        self.all_pass()
        proofs = qa.verify_stamps(self.world, self.md5)
        self.assertEqual(sum(x["passed"] for x in proofs), 813)

    def test_missing_any_protagonist_save_is_a_hard_failure(self):
        self.all_pass()
        (self.stamps / "GrandWorldSaveLyra.PASS").unlink()
        with self.assertRaisesRegex(ValueError, "required mGBA suite absent"):
            qa.verify_stamps(self.world, self.md5)

    def test_wrong_cartridge_md5_rejected_even_with_every_pass(self):
        self.all_pass()
        with self.assertRaisesRegex(ValueError, "stale or incomplete"):
            qa.verify_stamps(self.world, "B" * 32)

    def test_failed_or_partial_cross_region_save_is_rejected(self):
        self.all_pass()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.stamp("GrandWorldCrossRegionSave", 175)
            qa.verify_stamps(self.world, self.md5)
        self.stamp("GrandWorldCrossRegionSave", 176)
        (self.stamps / "GrandWorldCrossRegionSave.FAIL").write_text("failed\n")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            qa.verify_stamps(self.world, self.md5)

    def test_no_rom_or_save_edits_from_stamp_inspection(self):
        self.all_pass()
        saved = self.world / "test-player.sav"
        saved.write_bytes(b"unique original fixture data")
        before = saved.read_bytes()
        qa.verify_stamps(self.world, self.md5)
        self.assertEqual(saved.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
