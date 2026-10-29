"""Pure-source M9 OWE palette correction tests (not mGBA gameplay)."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "patch_m9_owe_palette_budget.py"
spec = importlib.util.spec_from_file_location("m9_owe_palette_budget", SOURCE)
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class PaletteBudgetPatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.world = Path(self.tmp.name)
        (self.world / "Makefile").write_text("modern:\n\t@true\n", encoding="utf-8")
        for relative, body in {
            "include/config/wild_encounter.h": (
                "#define WE_OW_ENCOUNTERS TRUE\n#define WE_VANILLA_RANDOM TRUE\n"),
            "include/config/overworld.h": (
                "#define OW_FOLLOWERS_ENABLED TRUE\n#define OW_GFX_COMPRESS FALSE\n"),
            patch.HELPER_PATH: "/* retained native loader */\n" + patch.HELPER_OLD +
                               "\n/* remainder must remain unchanged */\n",
            patch.OWE_PATH: (
                "/* keep movement, spawn, battles, fishing and followers */\n"
                + patch.NOTE_OLD + "static bool32 CheckCanLoadOWE_Palette(void) {\n"
                + patch.PALETTE_OLD + "}\n/* unchanged */\n"),
        }.items():
            file = self.world / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(body, encoding="utf-8")

    def test_preflight_is_read_only(self):
        before = {
            name: (self.world / name).read_bytes()
            for name in (patch.HELPER_PATH, patch.OWE_PATH)
        }
        result = patch.run(self.world, False)
        self.assertEqual(result["mode"], "preflight")
        self.assertFalse(result["gameplay_approved"])
        for name, blob in before.items():
            self.assertEqual(blob, (self.world / name).read_bytes())

    def test_scoped_patch_changes_only_two_expected_blocks(self):
        before_helper = (self.world / patch.HELPER_PATH).read_text()
        before_owe = (self.world / patch.OWE_PATH).read_text()
        result = patch.run(self.world, True)
        after_helper = (self.world / patch.HELPER_PATH).read_text()
        after_owe = (self.world / patch.OWE_PATH).read_text()
        self.assertEqual(result["mode"], "applied")
        self.assertEqual(after_helper, before_helper.replace(
            patch.HELPER_OLD, patch.HELPER_NEW, 1))
        self.assertEqual(after_owe, before_owe.replace(
            patch.NOTE_OLD, patch.NOTE_NEW, 1).replace(
                patch.PALETTE_OLD, patch.PALETTE_NEW, 1))
        self.assertIn("return species;", after_helper)
        self.assertIn("return slotsNeeded <= numFreePalSlots;", after_owe)
        self.assertIn("keep movement, spawn, battles, fishing and followers", after_owe)
        self.assertFalse(result["active_owe_cap_changed"])
        self.assertFalse(result["encounter_rates_changed"])

    def test_rejects_repeated_application(self):
        patch.run(self.world, True)
        with self.assertRaisesRegex(ValueError, "already applied"):
            patch.run(self.world, True)

    def test_changed_first_anchor_prevents_any_write(self):
        helper_file = self.world / patch.HELPER_PATH
        original = helper_file.read_bytes()
        owe_file = self.world / patch.OWE_PATH
        owe_file.write_text(owe_file.read_text().replace(
            patch.PALETTE_OLD, "// unknown upstream version\n"))
        with self.assertRaisesRegex(ValueError, "anchor changed"):
            patch.run(self.world, True)
        self.assertEqual(helper_file.read_bytes(), original)

    def test_missing_helper_anchor_prevents_any_write(self):
        p = self.world / patch.HELPER_PATH
        p.write_text("unknown engine", encoding="utf-8")
        owe_before = (self.world / patch.OWE_PATH).read_bytes()
        with self.assertRaisesRegex(ValueError, "anchor changed"):
            patch.run(self.world, True)
        self.assertEqual((self.world / patch.OWE_PATH).read_bytes(), owe_before)

    def test_duplicate_anchor_rejected(self):
        p = self.world / patch.OWE_PATH
        p.write_text(p.read_text() + patch.PALETTE_OLD)
        with self.assertRaisesRegex(ValueError, "anchor changed"):
            patch.run(self.world, True)

    def test_disallows_non_visible_configuration(self):
        p = self.world / "include/config/wild_encounter.h"
        p.write_text(p.read_text().replace(
            "#define WE_OW_ENCOUNTERS TRUE", "#define WE_OW_ENCOUNTERS FALSE"))
        with self.assertRaisesRegex(ValueError, "WE_OW_ENCOUNTERS"):
            patch.run(self.world, True)

    def test_disallows_follower_disable(self):
        p = self.world / "include/config/overworld.h"
        p.write_text(p.read_text().replace(
            "#define OW_FOLLOWERS_ENABLED TRUE", "#define OW_FOLLOWERS_ENABLED FALSE"))
        with self.assertRaisesRegex(ValueError, "OW_FOLLOWERS_ENABLED"):
            patch.run(self.world, True)

    def test_missing_complete_checkout(self):
        with self.assertRaisesRegex(ValueError, "Makefile"):
            patch.run(self.world / "not-there", True)


if __name__ == "__main__":
    unittest.main()
