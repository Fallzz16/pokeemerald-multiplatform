"""Unit tests of fail-closed, isolated, grass-only classic encounter patch."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "enable_classic_grass_encounters.py"
spec = importlib.util.spec_from_file_location("m8_grass", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class GrassOnlyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "include/config").mkdir(parents=True)
        (self.root / "src").mkdir()
        self.config = self.root / "include/config/wild_encounter.h"
        self.core = self.root / "src/wild_encounter.c"
        self.owe = self.root / "src/wild_encounter_ow.c"
        self.config.write_text(mod.CLASSIC_RANDOM + "\n" + mod.OWE_ACTIVE + "\n")
        self.core.write_text(
            "#include \"global.h\"\n"
            "bool8 StandardWildEncounter(u16 curMetatileBehavior, u16 prevMetatileBehavior)\n"
            "{\n" + mod.LAND_OLD + "}\n"
            "bool8 SweetScentWildEncounter(void)\n"
            "{\n" + mod.SCENT_OLD + "}\n"
            "bool8 FishingWildEncounter(void) { return TRUE; }\n")
        self.owe.write_text(mod.OWE_ENTRY +
                            "    if (!WE_OW_ENCOUNTERS\n"
                            "     || FlagGet(WE_OWE_FLAG_DISABLED))\n"
                            "        return;\n}\n")

    def snapshot(self):
        return {p: p.read_bytes() for p in (self.config, self.core, self.owe)}

    def test_dry_run_has_no_disk_edits(self):
        old = self.snapshot()
        out = mod.apply(self.root)
        self.assertEqual(out["mode"], "preflight")
        self.assertEqual(old, self.snapshot())

    def test_classic_grass_only_and_no_generated_overworld_wild(self):
        report = mod.apply(self.root, write=True)
        self.assertEqual(report["mode"], "applied")
        self.assertEqual(len(report["modified"]), 3)
        self.assertIn(mod.OWE_DISABLED, self.config.read_text())
        self.assertIn(mod.CLASSIC_RANDOM, self.config.read_text())
        self.assertNotIn(mod.OWE_ACTIVE, self.config.read_text())
        code = self.core.read_text()
        self.assertIn(mod.LAND_NEW, code)
        self.assertIn(mod.SCENT_NEW, code)
        self.assertIn("MetatileBehavior_IsTallGrass", code)
        self.assertIn("MetatileBehavior_IsLongGrass", code)
        self.assertIn("MetatileBehavior_IsAshGrass", code)
        self.assertIn("FishingWildEncounter(void) { return TRUE; }", code)
        self.assertIn("if (!WE_OW_ENCOUNTERS)\n", self.owe.read_text())
        self.assertIn("DespawnAllOverworldWildEncounters", self.owe.read_text())
        self.assertNotIn(mod.OWE_ENTRY, self.owe.read_text())
        self.assertFalse(report["fps_measured"])

    def test_reapply_fails_closed(self):
        mod.apply(self.root, write=True)
        snapshot = self.snapshot()
        with self.assertRaises(ValueError):
            mod.apply(self.root, write=True)
        self.assertEqual(snapshot, self.snapshot())

    def test_reject_changed_owe_source_without_writing_anything(self):
        self.owe.write_text(self.owe.read_text().replace(mod.OWE_ENTRY, "void Renamed(void)\n{\n"))
        old = self.snapshot()
        with self.assertRaisesRegex(ValueError, "early OWE"):
            mod.apply(self.root, write=True)
        self.assertEqual(old, self.snapshot())

    def test_reject_random_encounters_disabled(self):
        self.config.write_text(self.config.read_text().replace(mod.CLASSIC_RANDOM,
                                                              "#define WE_VANILLA_RANDOM           FALSE"))
        with self.assertRaisesRegex(ValueError, "classic random"):
            mod.apply(self.root, write=True)

    def test_reject_duplicate_land_checks(self):
        self.core.write_text(self.core.read_text() + mod.LAND_OLD)
        old = self.snapshot()
        with self.assertRaisesRegex(ValueError, "walking trigger"):
            mod.apply(self.root, write=True)
        self.assertEqual(old, self.snapshot())

    def test_reject_existing_grass_modification(self):
        self.core.write_text(self.core.read_text().replace(mod.LAND_OLD, mod.LAND_NEW))
        with self.assertRaisesRegex(ValueError, "walking trigger"):
            mod.apply(self.root, write=True)

    def test_reject_ambiguous_owe_cleanup_guard(self):
        self.owe.write_text(self.owe.read_text() +
                            "    if (!WE_OW_ENCOUNTERS\n")
        with self.assertRaisesRegex(ValueError, "no longer unique"):
            mod.apply(self.root, write=True)

    def test_original_files_are_not_modified_when_one_file_absent(self):
        self.core.unlink()
        before = self.config.read_bytes()
        with self.assertRaisesRegex(ValueError, "source tree"):
            mod.apply(self.root, write=True)
        self.assertEqual(self.config.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
