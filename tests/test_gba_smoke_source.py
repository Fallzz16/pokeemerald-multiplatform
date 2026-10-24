"""Guard the headless runtime navigation smoke's isolated input schedule.

This is a static regression check; only the GitHub runner running libmgba can
confirm that the compiled GBA program actually reaches new-game screens.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class HeadlessGbaProbeTests(unittest.TestCase):
    def test_disposable_emulation_has_45000_frame_probe(self):
        source = (ROOT / "tools/kanto/gba_headless_smoke.c").read_text(encoding="utf-8")
        self.assertIn("i <= 45000", source)
        self.assertIn("i == 4501", source)
        self.assertIn("i == 4901", source)
        self.assertIn("dialogue_visible", source)
        self.assertIn("i % 95 < 5", source)
        self.assertIn("sample_location(core, i, saveblock_symbol)", source)
        self.assertIn("current.group == 0 && current.number == 9", source)
        self.assertIn("first_littleroot_frame", source)
        self.assertIn("(i - 9701) % 130 == 0", source)
        self.assertIn("save_ppm(\"gba-navigation-frame-45000.ppm\"", source)
        self.assertIn('fprintf(report, "overworld_verified=%s', source)
        self.assertIn('save_reload_verified=false', source)
        self.assertNotIn("savedataRestore(", source)
        self.assertNotIn("loadSave(", source)
        self.assertNotIn("busWrite", source)

    def test_workflow_retains_advisory_separate_job(self):
        workflow = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
        self.assertIn("  gba-headless-smoke:", workflow)
        self.assertIn("    continue-on-error: true", workflow)
        self.assertIn("gba-navigation-frame-45000.ppm", workflow)
        self.assertIn("timeout -k 10 180 apt-get update", workflow)

if __name__ == "__main__":
    unittest.main(verbosity=2)
