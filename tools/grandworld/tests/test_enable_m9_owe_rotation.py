"""Source-only regressions for the opt-in M9 OWE rotation adapter."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "enable_m9_owe_rotation.py"
spec = importlib.util.spec_from_file_location("m9_owe_rotation", SOURCE)
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class NativeOWERotationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.world = Path(self.temp.name)
        (self.world / "Makefile").write_text("modern:\n\t@true\n")
        cfg = "\n".join("#define " + k + " " + v
                           for k, v in patch.REQUIRED.items()) + "\n"
        c = "\n".join(patch.SOURCE_TOKENS) + "\n"
        for path, data in ((patch.CONFIG, cfg), (patch.SOURCE, c)):
            file = self.world / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(data)

    def test_preflight_does_not_write(self):
        config = self.world / patch.CONFIG
        before = config.read_bytes()
        result = patch.run(self.world)
        self.assertEqual(before, config.read_bytes())
        self.assertEqual(result["mode"], "read_only_preflight")
        self.assertFalse(result["gameplay_approved"])

    def test_changes_only_two_native_flags(self):
        config = self.world / patch.CONFIG
        before = config.read_text()
        patch.run(self.world, apply=True)
        after = config.read_text()
        expected = before
        for key, value in patch.CHANGES.items():
            expected = expected.replace("#define " + key + " FALSE",
                                        "#define " + key + " " + value)
        self.assertEqual(after, expected)
        self.assertIn("#define WE_OW_ENCOUNTERS TRUE", after)
        self.assertIn("#define WE_VANILLA_RANDOM TRUE", after)

    def test_fails_closed_on_second_application(self):
        patch.run(self.world, apply=True)
        with self.assertRaisesRegex(ValueError, "expected exactly WE_OWE_SPAWN_REPLACEMENT"):
            patch.run(self.world, apply=True)

    def test_fails_closed_when_original_shiny_logic_changed(self):
        source = self.world / patch.SOURCE
        source.write_text(source.read_text().replace(
            "if (WE_OWE_PREVENT_SHINY_DESPAWN && info->isShiny)",
            "if (FALSE)"))
        before = (self.world / patch.CONFIG).read_bytes()
        with self.assertRaisesRegex(ValueError, "safeguard changed"):
            patch.run(self.world, apply=True)
        self.assertEqual(before, (self.world / patch.CONFIG).read_bytes())

    def test_fails_closed_on_duplicate_flag(self):
        config = self.world / patch.CONFIG
        config.write_text(config.read_text() + "#define WE_OWE_SPAWN_REPLACEMENT FALSE\n")
        with self.assertRaisesRegex(ValueError, "expected exactly WE_OWE_SPAWN_REPLACEMENT"):
            patch.run(self.world, apply=True)

    def test_preserves_files_when_engine_missing(self):
        with self.assertRaisesRegex(ValueError, "Makefile missing"):
            patch.run(self.world / "missing", apply=True)


if __name__ == "__main__":
    unittest.main()
