import tempfile
import unittest
from pathlib import Path

from tools.grandworld_native.symbol_source_audit import scan_sources


class WorldSourceOwnerTests(unittest.TestCase):
    def test_real_script_labels_and_unresolved_without_owners(self):
        with tempfile.TemporaryDirectory() as folder:
            world = Path(folder)
            script = world / "data" / "maps" / "Hub" / "scripts.inc"
            script.parent.mkdir(parents=True)
            script.write_text("Hub_EventScript_Travel::\n\t.byte 1\n", encoding="utf-8")
            asm = world / "src" / "real_helpers.s"
            asm.parent.mkdir()
            asm.write_text("SomeAsmRoutine:\n\t.byte 0\n", encoding="utf-8")
            inventory = scan_sources(world, {
                "Hub_EventScript_Travel", "SomeAsmRoutine", "MissingSymbol"
            })
            self.assertEqual(inventory["symbols_with_literal_asm_source_labels"], 2)
            self.assertEqual(inventory["symbols_without_literal_asm_source_labels"], 1)
            self.assertIn("MissingSymbol", inventory["sample_without_owners"])
            self.assertFalse(inventory["native_link_complete"])
            self.assertTrue(inventory["source_owner_lookup_is_heuristic"])

    def test_asm_comments_do_not_create_fake_symbols(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            base = root / "data"
            base.mkdir()
            (base / "example.s").write_text(
                "  @ ImaginaryLabel:\n  .4byte OtherLabel\nRealLabel:\n",
                encoding="utf-8")
            result = scan_sources(root, {"ImaginaryLabel", "OtherLabel", "RealLabel"})
            self.assertEqual(result["symbols_with_literal_asm_source_labels"], 1)
            self.assertIn("RealLabel", result["sample_candidate_owners"])

if __name__ == "__main__":
    unittest.main()
