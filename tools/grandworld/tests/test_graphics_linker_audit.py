"""Fail-closed tests for linker-backed graphic symbol accounting."""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "graphics_linker_audit.py"
spec = importlib.util.spec_from_file_location("graphics_linker_audit", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class LinkerGraphicsTests(unittest.TestCase):
    def test_parses_rom_resident_categories_and_deduplicates_aliases(self):
        nm = """08001000 00000200 R gObjectEventPic_Brendan
08001200 00000020 R gOverworldPalette_Brendan
08001220 00000020 R gShinyOverworldPalette_Brendan
08002000 00001000 R gMonFrontPic_Bulbasaur
08002000 00001000 R gMonFrontPic_BulbasaurAlias
08003000 00000800 R gMonBackPic_Bulbasaur
08003800 00000020 R gMonPalette_Bulbasaur
08003820 00000020 R gMonShinyPalette_Bulbasaur
08003840 00000400 R gMonIcon_Bulbasaur
02001000 00000400 B gMonIcon_EwramNotRom
"""
        d = mod.analyze(nm)
        self.assertEqual(d["category_bytes"]["overworld_frames"], 512)
        self.assertEqual(d["category_bytes"]["mon_front_battle"], 4096)
        self.assertEqual(d["total_unique_classified_symbol_bytes"], 512+32+32+4096+2048+32+32+1024)
        self.assertEqual(d["unique_allocations"], 8)
        self.assertEqual(len(d["alias_symbols_excluded"]), 1)
        self.assertFalse(d["complete_rom_asset_coverage"])
        self.assertEqual(d["actual_rom_bytes_saved"], 0)

    def test_rejects_no_rom_graphic_symbols(self):
        with self.assertRaisesRegex(ValueError, "no linked ROM graphic"):
            mod.analyze("02001000 00000400 B gObjectEventPic_Test\n")

    def test_skips_out_of_rom_addresses_and_zero_sizes(self):
        text = ("08001000 00000200 R gObjectEventPic_Brendan\n"
                "09fffff0 00000020 R gObjectEventPic_Outside\n"
                "08002000 00000000 R gObjectEventPic_Empty\n")
        d = mod.analyze(text)
        self.assertEqual(d["total_unique_classified_symbol_bytes"], 512)
        self.assertEqual(d["unique_allocations"], 1)


if __name__ == "__main__":
    unittest.main()
