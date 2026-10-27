"""Focused fixtures for read-only M9 Master Visible policy; no game assets."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / "verify_master_visible.py"
spec = importlib.util.spec_from_file_location("gw_master_visible_gate", PATH)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class MasterVisibleGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "Makefile").write_text("all:\n\t@true\n", encoding="utf-8")
        for relative, flags in gate.CONFIG.items():
            p = self.root / relative
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("".join(f"#define {k} {v}\n" for k, v in flags.items()),
                         encoding="utf-8")
        for relative, hooks in gate.SOURCE_HOOKS.items():
            p = self.root / relative
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("".join(f"void {token};\n" for token in hooks),
                         encoding="utf-8")

    def test_healthy_original_policy_is_read_only(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = gate.verify(self.root)
        after = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result["profile"], "M9_MASTER_VISIBLE")
        self.assertEqual(result["source_checks"], 16)
        self.assertFalse(result["visible_spawns_observed_in_emulator"])
        self.assertFalse(result["gameplay_approved"])

    def test_earlier_grass_only_override_is_rejected(self):
        p = self.root / "include/config/wild_encounter.h"
        p.write_text(p.read_text().replace(
            "#define WE_OW_ENCOUNTERS TRUE", "#define WE_OW_ENCOUNTERS FALSE"))
        with self.assertRaisesRegex(ValueError, "WE_OW_ENCOUNTERS=TRUE"):
            gate.verify(self.root)

    def test_forced_grass_patch_detected_even_if_toggle_stays_true(self):
        p = self.root / "src/wild_encounter.c"
        p.write_text(p.read_text() + "\n#ifdef GW_GRASS_ONLY_WILD\n#endif\n")
        with self.assertRaisesRegex(ValueError, "incompatible"):
            gate.verify(self.root)

    def test_duplicate_flag_fails_closed(self):
        p = self.root / "include/config/wild_encounter.h"
        p.write_text(p.read_text() + "#define WE_VANILLA_RANDOM TRUE\n")
        with self.assertRaisesRegex(ValueError, "WE_VANILLA_RANDOM=TRUE"):
            gate.verify(self.root)

    def test_missing_fishing_hook_fails_closed(self):
        p = self.root / "src/wild_encounter.c"
        p.write_text(p.read_text().replace("FishingWildEncounter(", "RenamedFishing("))
        with self.assertRaisesRegex(ValueError, "FishingWildEncounter"):
            gate.verify(self.root)

    def test_owe_follower_disabled_fails_closed(self):
        p = self.root / "include/config/overworld.h"
        p.write_text(p.read_text().replace(
            "#define OW_FOLLOWERS_ENABLED TRUE", "#define OW_FOLLOWERS_ENABLED FALSE"))
        with self.assertRaisesRegex(ValueError, "OW_FOLLOWERS_ENABLED=TRUE"):
            gate.verify(self.root)

    def test_not_a_world_checkout_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Makefile"):
            gate.verify(self.root / "missing")


if __name__ == "__main__":
    unittest.main()
