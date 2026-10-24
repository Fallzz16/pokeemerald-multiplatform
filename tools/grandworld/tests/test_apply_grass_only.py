"""Fail-closed source patch tests. Fixtures contain no commercial game assets."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SRC = Path(__file__).resolve().parents[1] / "apply_grass_only.py"
spec = importlib.util.spec_from_file_location("grandworld_grass_only", SRC)
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class GrassOnlyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.world = Path(self.tmp.name)
        cfg_dir = self.world / "include/config"
        cfg_dir.mkdir(parents=True)
        (self.world / "src").mkdir()
        (self.world / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
        self.cfg = cfg_dir / "wild_encounter.h"
        self.src = self.world / "src/wild_encounter.c"
        self.cfg.write_text(
            "// Vanilla\n" + patch.VANILLA + "\n" + patch.CONFIG_OLD + "\n",
            encoding="utf-8"
        )
        self.src.write_text(
            "\n\n".join(old for old, _ in patch.ANCHORS.values()) + "\n",
            encoding="utf-8"
        )

    def test_preflight_has_no_side_effects(self):
        cfg, src = self.cfg.read_bytes(), self.src.read_bytes()
        self.assertEqual(patch.apply(self.world)["mode"], "preflight")
        self.assertEqual(cfg, self.cfg.read_bytes())
        self.assertEqual(src, self.src.read_bytes())
        self.assertEqual(list(self.world.rglob("*.gw-grass-original")), [])

    def test_all_six_mechanics_patched_and_existing_code_retained(self):
        before = self.src.read_text()
        result = patch.apply(self.world, write=True)
        self.assertEqual(result["mode"], "applied")
        self.assertFalse(result["runtime_gameplay_verified"])
        self.assertIn(patch.GRASS_SETTING, self.cfg.read_text())
        self.assertIn(patch.CONFIG_NEW, self.cfg.read_text())
        self.assertNotIn(patch.CONFIG_OLD, self.cfg.read_text())
        self.assertIn(patch.VANILLA, self.cfg.read_text())
        expected = before
        for old, new in patch.ANCHORS.values():
            expected = expected.replace(old, new, 1)
        self.assertEqual(self.src.read_text(), expected)
        self.assertEqual(self.src.with_name(self.src.name + ".gw-grass-original").read_text(), before)
        self.assertEqual(self.cfg.with_name(self.cfg.name + ".gw-grass-original").read_text(),
                         "// Vanilla\n" + patch.VANILLA + "\n" + patch.CONFIG_OLD + "\n")
        with self.assertRaisesRegex(ValueError, "already"):
            patch.apply(self.world, write=True)

    def test_one_changed_function_aborts_entire_patch(self):
        self.src.write_text(self.src.read_text().replace(
            "bool8 DoesCurrentMapHaveFishingMons(void)",
            "bool8 ChangedFishingFunction(void)"
        ))
        cfg, src = self.cfg.read_bytes(), self.src.read_bytes()
        with self.assertRaisesRegex(ValueError, "fishing_availability"):
            patch.apply(self.world, write=True)
        self.assertEqual((cfg, src), (self.cfg.read_bytes(), self.src.read_bytes()))
        self.assertEqual(list(self.world.rglob("*.gw-grass-original")), [])

    def test_duplicate_anchor_refused(self):
        self.src.write_text(self.src.read_text() + patch.ANCHORS["step"][0])
        with self.assertRaisesRegex(ValueError, "step"):
            patch.apply(self.world, write=True)

    def test_unexpected_owe_config_refused(self):
        self.cfg.write_text(self.cfg.read_text().replace(patch.CONFIG_OLD, patch.CONFIG_NEW))
        with self.assertRaisesRegex(ValueError, "generated overworld spawns"):
            patch.apply(self.world, write=True)

    def test_missing_world_checkout_refused(self):
        with self.assertRaisesRegex(ValueError, "complete pinned"):
            patch.apply(self.world / "empty", write=True)


if __name__ == "__main__":
    unittest.main()
