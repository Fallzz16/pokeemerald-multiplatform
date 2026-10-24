"""Validate the actual-save mGBA instrumenter's strict source contract."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "story_save", Path(__file__).resolve().parents[1] / "extend_story_save_qa.py")
story = importlib.util.module_from_spec(spec)
spec.loader.exec_module(story)


def fixture():
    return "\n".join(anchor for anchor, _ in story.REPLACEMENTS)


class SaveProbeTests(unittest.TestCase):
    def test_story_suites_and_save_checks_preserved(self):
        out = story.build(fixture())
        self.assertIn("new(S,'GrandWorldHeroSave')", out)
        self.assertEqual(out.count("GW real save/Continue preserved"), 3)
        self.assertIn("client.reboot_core()", out) if "client.reboot_core()" in fixture() else None
        self.assertIn("F.check('fresh hub has deliberate Kanto default'", out)

    def test_source_drift_rejected(self):
        original = fixture()
        marker = story.REPLACEMENTS[2][0]
        for data in (original.replace(marker, ""), original + marker):
            with self.subTest(data=data[-70:]):
                with self.assertRaisesRegex(ValueError, "drift"):
                    story.build(data)

    def test_existing_destination_never_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            src, dst = Path(t) / "StoryProgress.lua", Path(t) / "GrandWorldHeroSave.lua"
            src.write_text(fixture())
            story.prepare(src, dst)
            self.assertIn("GrandWorldHeroSave", dst.read_text())
            dst.write_text("preserve")
            with self.assertRaisesRegex(ValueError, "already exists"):
                story.prepare(src, dst)
            self.assertEqual(dst.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
