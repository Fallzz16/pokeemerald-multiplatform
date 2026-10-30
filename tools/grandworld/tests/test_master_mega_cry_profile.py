"""Unit tests: opt-in compact Mega cry is reversible and refuses upstream drift."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "master_mega_cry_profile.py"
spec = importlib.util.spec_from_file_location("master_mega_cry_profile", SOURCE)
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


class MasterMegaCryProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "Makefile").write_text("modern:\n\t@true\n")
        for rel, tokens in profile.REQUIRED.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(tokens) + "\n")
        for rel, (original, _) in profile.MEGA_SOURCE_PATCHES.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("/* unrelated species data */\n" + original + "\n")
        self.conf = self.root / profile.CONF

    def test_preflight_read_only(self):
        before = self.conf.read_bytes()
        result = profile.run(self.root)
        self.assertEqual(before, self.conf.read_bytes())
        self.assertFalse(result["gameplay_approved"])

    def test_only_mega_cry_choice_changes(self):
        previous = self.conf.read_text()
        result = profile.run(self.root, apply=True)
        current = self.conf.read_text()
        self.assertEqual(current, previous.replace(
            "#define P_MODIFIED_MEGA_CRIES            P_MEGA_EVOLUTIONS",
            "#define P_MODIFIED_MEGA_CRIES            FALSE"))
        self.assertIn("#define P_CRIES_ENABLED                  TRUE", current)
        self.assertIn("CRY_MODE_HIGH_PITCH", current)
        self.assertFalse(result["distinct_mega_cry_audio_kept"])
        for rel, (_, guarded) in profile.MEGA_SOURCE_PATCHES.items():
            self.assertIn(guarded, (self.root / rel).read_text())

    def test_reapplication_fails_closed(self):
        profile.run(self.root, apply=True)
        with self.assertRaisesRegex(ValueError, "drift"):
            profile.run(self.root, apply=True)

    def test_upstream_sound_logic_drift_refuses_any_edit(self):
        path = self.root / profile.SOUND
        path.write_text("changed original sound source")
        snapshot = self.conf.read_bytes()
        with self.assertRaisesRegex(ValueError, "drift"):
            profile.run(self.root, apply=True)
        self.assertEqual(snapshot, self.conf.read_bytes())

    def test_unguarded_mega_species_drift_fails_closed(self):
        path = self.root / next(iter(profile.MEGA_SOURCE_PATCHES))
        path.write_text("upstream changed this species")
        snapshot = self.conf.read_bytes()
        with self.assertRaisesRegex(ValueError, "identifier drift"):
            profile.run(self.root, apply=True)
        self.assertEqual(snapshot, self.conf.read_bytes())

    def test_regular_cries_never_disabled(self):
        self.conf.write_text(self.conf.read_text().replace(
            "#define P_CRIES_ENABLED                  TRUE",
            "#define P_CRIES_ENABLED                  FALSE"))
        with self.assertRaisesRegex(ValueError, "drift"):
            profile.run(self.root, apply=True)


if __name__ == "__main__":
    unittest.main()
