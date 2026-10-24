"""M8 grass-only/adaptive-shadows exact patch contract with synthetic source fixtures."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

FILE = Path(__file__).resolve().parents[1] / "apply_quetzal_profile.py"
spec = importlib.util.spec_from_file_location("m8_quetzal_profile", FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "include/config").mkdir(parents=True)
        (self.root / "src").mkdir()
        self.wild_cfg = self.root / "include/config/wild_encounter.h"
        self.ow_cfg = self.root / "include/config/overworld.h"
        self.wild_src = self.root / "src/wild_encounter_ow.c"
        self.effect_src = self.root / "src/field_effect_helpers.c"
        self.wild_cfg.write_text(
            mod.RANDOM_ON + "\n" + mod.OWE_ON + "\n", encoding="utf-8")
        self.ow_cfg.write_text(
            mod.SHADOW_VANILLA + "\n#define OW_GFX_COMPRESS                FALSE\n"
            "#define OW_FOLLOWERS_ENABLED           TRUE\n", encoding="utf-8")
        self.wild_src.write_text(
            mod.UPDATE_OLD +
            "\n    if (ArePlayerFieldControlsLocked() || FlagGet(DN_FLAG_SEARCHING) || 0) return;\n"
            "    // original guards\n", encoding="utf-8")
        self.effect_src.write_text(
            mod.SHADOW_START + "\n         && gSprites[i].sLocalId == 0) return FALSE;\n    }\n" +
            mod.SHADOW_OBJECT + "\n    return FALSE;\n}\n", encoding="utf-8")

    def test_preflight_read_only(self):
        before = [p.read_bytes() for p in (self.wild_cfg, self.ow_cfg, self.wild_src, self.effect_src)]
        r = mod.apply(self.root, False)
        self.assertEqual(r["mode"], "preflight")
        self.assertFalse(r["runtime_fps_measured"])
        self.assertEqual(before, [p.read_bytes() for p in (self.wild_cfg, self.ow_cfg, self.wild_src, self.effect_src)])

    def test_exact_edit_preserves_vanilla_and_saves(self):
        result = mod.apply(self.root, True)
        self.assertEqual(len(result["changes"]), 4)
        self.assertIn(mod.RANDOM_ON, self.wild_cfg.read_text())
        self.assertIn(mod.OWE_OFF, self.wild_cfg.read_text())
        self.assertIn(mod.SHADOW_ALL, self.ow_cfg.read_text())
        self.assertIn("OW_FOLLOWERS_ENABLED", self.ow_cfg.read_text())
        self.assertIn("sOWESpawnCountdown == OWE_NO_ENCOUNTER_SET", self.wild_src.read_text())
        self.assertIn("usedSprites++", self.effect_src.read_text())
        self.assertIn("OBJ_EVENT_ID_FOLLOWER", self.effect_src.read_text())
        self.assertFalse(result["save_layout_changed"])
        self.assertFalse(result["gfx_compression_changed"])

    def test_idempotence_refuses_reapply(self):
        mod.apply(self.root, True)
        state = [p.read_bytes() for p in (self.wild_cfg, self.ow_cfg, self.wild_src, self.effect_src)]
        with self.assertRaises(ValueError):
            mod.apply(self.root, True)
        self.assertEqual(state, [p.read_bytes() for p in (self.wild_cfg, self.ow_cfg, self.wild_src, self.effect_src)])

    def test_refuses_unexpected_source_without_partial_write(self):
        previous = self.wild_cfg.read_bytes()
        self.effect_src.write_text("wrong version\n")
        with self.assertRaises(ValueError):
            mod.apply(self.root, True)
        self.assertEqual(previous, self.wild_cfg.read_bytes())
        self.assertIn(mod.SHADOW_VANILLA, self.ow_cfg.read_text())

    def test_refuses_vanilla_random_disable_and_gfx_drift(self):
        self.wild_cfg.write_text(self.wild_cfg.read_text().replace(mod.RANDOM_ON, "#define WE_VANILLA_RANDOM           FALSE"))
        with self.assertRaisesRegex(ValueError, "vanilla grass"):
            mod.apply(self.root, True)
        self.wild_cfg.write_text(mod.RANDOM_ON + "\n" + mod.OWE_ON)
        self.ow_cfg.write_text(self.ow_cfg.read_text().replace(
            "#define OW_GFX_COMPRESS                FALSE", "#define OW_GFX_COMPRESS                TRUE"))
        with self.assertRaisesRegex(ValueError, "VRAM"):
            mod.apply(self.root, True)

    def test_fails_on_multiple_shadow_anchors(self):
        self.effect_src.write_text(self.effect_src.read_text() + mod.SHADOW_START)
        with self.assertRaisesRegex(ValueError, "shadow budget count"):
            mod.apply(self.root, True)


if __name__ == "__main__":
    unittest.main()
