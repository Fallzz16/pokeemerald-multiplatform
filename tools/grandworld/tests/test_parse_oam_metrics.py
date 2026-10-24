"""Tests for hardware OAM metrics parser using synthetic mGBA console logs."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "parse_oam_metrics.py"
spec = importlib.util.spec_from_file_location("m8_oam_parse", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

LOG = (
    "OAM_METRIC scenario=hub_idle frames=180 active_min=7 active_max=15 active_avg=11.500\n"
    "OAM_METRIC scenario=hub_after_movement frames=120 active_min=8 active_max=17 active_avg=12.125\n"
    "VERDICT GrandWorldOamBudget: 2/2 PASS\n"
)


class OamMetricsTests(unittest.TestCase):
    def test_valid_metrics(self):
        report = mod.report(LOG, b"synthetic-only")
        self.assertEqual(report["scenarios"]["hub_idle"]["frames"], 180)
        self.assertEqual(report["scenarios"]["hub_after_movement"]["free_sprite_slots_at_peak"], 111)
        self.assertEqual(len(report["rom_sha256"]), 64)
        self.assertFalse(report["fps_measured"])

    def test_missing_case_refused(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            mod.report(LOG.split("OAM_METRIC scenario=hub_after_movement")[0] +
                       "VERDICT GrandWorldOamBudget: 2/2 PASS\n", b"test")

    def test_missing_completion_refused(self):
        with self.assertRaisesRegex(ValueError, "verdict"):
            mod.report(LOG.replace("VERDICT GrandWorldOamBudget: 2/2 PASS", ""), b"test")

    def test_duplicate_case_refused(self):
        with self.assertRaisesRegex(ValueError, "duplicated"):
            mod.report(LOG + LOG, b"test")

    def test_unphysical_samples_refused(self):
        for bad in (
            LOG.replace("active_max=15", "active_max=130"),
            LOG.replace("active_avg=11.500", "active_avg=29.000"),
            LOG.replace("frames=180", "frames=10"),
        ):
            with self.subTest(sample=bad[:85]):
                with self.assertRaisesRegex(ValueError, "invalid"):
                    mod.report(bad, b"test")


if __name__ == "__main__":
    unittest.main()
