"""Fail-closed proof tests for real PT-BR GBA mGBA save/travel coverage.

Fixtures emulate verdict *files*, not gameplay. The CI runs actual Lua on mGBA.
"""
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
spec = importlib.util.spec_from_file_location(
    "ptbr_gba_progression_audit", BASE / "audit_ptbr_gba_progression.py")
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


class PtbrGbaProgressionGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.world = Path(self.tmp.name)
        (self.world / "_pwtest").mkdir()
        rom_path = self.world / "pokemonworld.gba"
        with rom_path.open("wb") as out:
            out.truncate(audit_module.ROM_SIZE)
        header = bytearray(0x1E)
        header[0x0C:0x10] = b"BPEE"
        header[0x12] = 0x96
        header[0x1D] = (-sum(header[:0x1D]) - 0x19) & 0xFF
        with rom_path.open("r+b") as out:
            out.seek(0xA0)
            out.write(header)
        md5 = hashlib.md5(rom_path.read_bytes()).hexdigest().upper()
        self.md5 = md5
        for name, count in audit_module.REQUIRED_SUITES:
            (self.world / "_pwtest" / (name + ".PASS")).write_text(
                f"PASS {count}/{count} rom={md5} at=2026-10-25T20:00:00 suite={name}\n",
                encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def stamp(self, name):
        return self.world / "_pwtest" / (name + ".PASS")

    def test_complete_real_emulator_proof_contract(self):
        report = audit_module.audit(self.world)
        self.assertEqual(report["suite_count"], 10)
        self.assertEqual(report["expected_assertion_passes"], 702)
        self.assertEqual(len(report["real_mgba_suite_proofs"]), 10)
        self.assertEqual(report["target"], "PTBR_GBA_ARM_not_PC")
        self.assertFalse(report["intro_hero_picker_ui_certified"])
        self.assertFalse(report["existing_player_save_compatibility_certified"])
        self.assertFalse(report["manual_gameplay_certified"])
        self.assertFalse(report["release_approved"])

    def test_missing_mgba_suite_fails_closed(self):
        self.stamp("GrandWorldSaveLyra").unlink()
        with self.assertRaisesRegex(ValueError, "required mGBA suite absent"):
            audit_module.audit(self.world)

    def test_fail_and_pass_together_are_rejected(self):
        (self.world / "_pwtest" / "GrandWorldSixRoutes.FAIL").write_text("FAIL\n")
        with self.assertRaisesRegex(ValueError, "conflicting mGBA verdict"):
            audit_module.audit(self.world)

    def test_stale_rom_hash_is_rejected(self):
        name = "GrandWorldHeroSave"
        self.stamp(name).write_text(
            f"PASS 37/37 rom={'0' * 32} at=2026-10-25 suite={name}\n")
        with self.assertRaisesRegex(ValueError, "stale or incomplete"):
            audit_module.audit(self.world)

    def test_incomplete_assertion_total_is_rejected(self):
        name = "GrandWorldCrossRegionSave"
        self.stamp(name).write_text(
            f"PASS 175/175 rom={self.md5} at=2026-10-25 suite={name}\n")
        with self.assertRaisesRegex(ValueError, "stale or incomplete"):
            audit_module.audit(self.world)

    def test_multiline_or_malformed_stamp_is_rejected(self):
        with self.stamp("GrandWorldSaveRed").open("a") as out:
            out.write("PASS 38/38 forged extra verdict\n")
        with self.assertRaisesRegex(ValueError, "stale or incomplete"):
            audit_module.audit(self.world)

    def test_rom_header_corruption_is_rejected(self):
        with (self.world / "pokemonworld.gba").open("r+b") as out:
            out.seek(0xB2)
            out.write(b"\x00")
        with self.assertRaisesRegex(ValueError, "not the complete"):
            audit_module.audit(self.world)


if __name__ == "__main__":
    unittest.main()
