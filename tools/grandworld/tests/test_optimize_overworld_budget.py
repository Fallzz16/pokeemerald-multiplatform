"""Fail-closed tests for opt-in sprite and encounter fast-path profile."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "optimize_overworld_budget.py"
spec = importlib.util.spec_from_file_location("m8_budget", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class OverworldBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "include/config").mkdir(parents=True)
        (self.root / "src").mkdir()
        self.config = self.root / "include/config/overworld.h"
        self.config.write_text(
            mod.SHADOW_OLD + "\n#define OW_GFX_COMPRESS                FALSE\n"
            "#define OW_FOLLOWERS_ENABLED           TRUE\n", encoding="utf-8")
        self.encounter_cfg = self.root / "include/config/wild_encounter.h"
        self.encounter_cfg.write_text(
            "#define WE_OW_ENCOUNTERS                        TRUE\n", encoding="utf-8")
        self.encounter = self.root / "src/wild_encounter_ow.c"
        self.encounter.write_text(
            "void UpdateOverworldWildEncounter(void) {\n"
            + mod.EARLY_OLD + mod.GUARD_OLD + "\n}\n", encoding="utf-8")

    def test_preflight_does_not_write(self):
        a = self.config.read_bytes()
        b = self.encounter.read_bytes()
        r = mod.apply(self.root, False)
        self.assertEqual(r["mode"], "preflight")
        self.assertEqual((a, b), (self.config.read_bytes(), self.encounter.read_bytes()))

    def test_minimal_edits_preserve_runtime_features(self):
        before = self.encounter.read_text()
        r = mod.apply(self.root, True)
        self.assertEqual(r["mode"], "applied")
        self.assertIn(mod.SHADOW_NEW, self.config.read_text())
        self.assertNotIn(mod.SHADOW_OLD, self.config.read_text())
        self.assertEqual(self.encounter.read_text(),
                         before.replace(mod.GUARD_OLD, mod.GUARD_NEW)
                               .replace(mod.EARLY_OLD, mod.EARLY_NEW))
        self.assertEqual(self.encounter.read_text().count("FlagGet(DN_FLAG_SEARCHING)"), 1)
        self.assertIn(mod.EARLY_NEW, self.encounter.read_text())
        self.assertNotIn(mod.EARLY_OLD, self.encounter.read_text())
        self.assertIn("OW_FOLLOWERS_ENABLED           TRUE", self.config.read_text())
        self.assertIn("WE_OW_ENCOUNTERS", self.encounter_cfg.read_text())
        with self.assertRaises(ValueError):
            mod.apply(self.root, True)

    def test_native_owe_guard_reaches_spawn_timer(self):
        # This hardcoded C excerpt mirrors the pinned upstream source. The
        # previous optimizer forgot the original guard's return statement,
        # leaving a SECOND unconditional return after the replacement.
        original = (
            "void UpdateOverworldWildEncounter(void) {\n"
            "    bool32 shouldSpawnWaterMons = ShouldSpawnWaterOWE();\n"
            "    \n"
            "    if (ArePlayerFieldControlsLocked() || FlagGet(DN_FLAG_SEARCHING) || "
            "!CheckCurrentWildMonHeaderForOWE(shouldSpawnWaterMons))\n"
            "        return;\n"
            "\n    if (!WE_OW_ENCOUNTERS\n"
            + mod.GUARD_OLD + "\n}\n"
        )
        self.encounter.write_text(original, encoding="utf-8")
        mod.apply(self.root, True)
        optimized = self.encounter.read_text(encoding="utf-8")
        self.assertIn(mod.EARLY_NEW, optimized)
        self.assertIn("\n    if (!WE_OW_ENCOUNTERS", optimized)
        self.assertNotIn(mod.EARLY_NEW + "        return;\n", optimized)
        self.assertEqual(optimized.count("        return;"), 2)
        # No unrelated graphics, follower, cave, or random-encounter guards
        # are changed by the early-return fix.
        self.assertIn(mod.GUARD_NEW, optimized)

    def test_changed_original_return_fails_closed(self):
        original = self.encounter.read_bytes()
        self.encounter.write_text(self.encounter.read_text().replace(
            mod.EARLY_OLD, mod.EARLY_OLD.replace("        return;", "        return FALSE;")))
        mutated = self.encounter.read_bytes()
        with self.assertRaisesRegex(ValueError, "guard"):
            mod.apply(self.root, True)
        self.assertEqual(self.encounter.read_bytes(), mutated)
        self.assertNotEqual(original, mutated)

    def test_explicit_full_shadows_retains_aesthetic_flag(self):
        original = self.config.read_bytes()
        result = mod.apply(self.root, True, shadows="full")
        self.assertEqual(result["resolved_shadow_mode"], "full")
        self.assertEqual(self.config.read_bytes(), original)
        self.assertIn(mod.EARLY_NEW, self.encounter.read_text())
        self.assertNotIn(mod.GUARD_OLD, self.encounter.read_text())

    def test_auto_prioritizes_sprite_budget_with_followers(self):
        self.assertEqual(mod.apply(self.root, False)["resolved_shadow_mode"], "lean")
        self.assertEqual(mod.apply(self.root, False, shadows="full")["resolved_shadow_mode"], "full")

    def test_auto_keeps_full_shadows_without_followers(self):
        self.config.write_text(self.config.read_text().replace(
            "#define OW_FOLLOWERS_ENABLED           TRUE",
            "#define OW_FOLLOWERS_ENABLED           FALSE"))
        result = mod.apply(self.root, True)
        self.assertEqual(result["resolved_shadow_mode"], "full")
        self.assertIn(mod.SHADOW_OLD, self.config.read_text())

    def test_refuses_changed_early_guard_atomically(self):
        original = self.config.read_bytes()
        self.encounter.write_text(self.encounter.read_text().replace(
            "bool32 shouldSpawnWaterMons = ShouldSpawnWaterOWE();",
            "bool32 shouldSpawnWaterMons = 0;"))
        with self.assertRaisesRegex(ValueError, "guard"):
            mod.apply(self.root, True)
        self.assertEqual(self.config.read_bytes(), original)

    def test_invalid_requested_shadow_mode(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            mod.apply(self.root, True, shadows="unsupported")

    def test_changed_anchor_fails_without_partial_edits(self):
        old = self.config.read_bytes()
        self.encounter.write_text("unexpected version", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "guard"):
            mod.apply(self.root, True)
        self.assertEqual(self.config.read_bytes(), old)

    def test_disabled_follower_sprite_policy_fails_closed(self):
        self.config.write_text(self.config.read_text().replace(
            "#define OW_GFX_COMPRESS                FALSE",
            "#define OW_GFX_COMPRESS                TRUE"))
        with self.assertRaisesRegex(ValueError, "VRAM policy"):
            mod.apply(self.root, True)

    def test_unexpected_multiple_anchors_fail_closed(self):
        old = self.config.read_text()
        self.config.write_text(old + mod.SHADOW_OLD + "\n")
        with self.assertRaisesRegex(ValueError, "two|found 2"):
            mod.apply(self.root, True)


if __name__ == "__main__":
    unittest.main()
