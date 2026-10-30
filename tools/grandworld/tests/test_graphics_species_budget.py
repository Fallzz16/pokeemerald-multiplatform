"""Source-only overworld metadata budget tests, no real sprite assets changed."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

FILE = Path(__file__).resolve().parents[1] / "graphics_species_budget.py"
spec = importlib.util.spec_from_file_location("graphics_species_budget", FILE)
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


class GraphicsSpeciesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / "src/data/pokemon/species_info"
        self.src.mkdir(parents=True)
        for gen in range(1, 10):
            lines = []
            for i in range(30):
                lines.append(
                    f"[SPECIES_TEST_G{gen}_{i}] = {{\n"
                    + ("OVERWORLD(sPicTable_Test, SIZE_64x64, SHADOW_SIZE_M, TRACKS_FOOT, sAnimTable_Following)\n"
                       if i == 0 else
                       "OVERWORLD(sPicTable_Test, SIZE_32x32, SHADOW_SIZE_M, TRACKS_FOOT, sAnimTable_Following)\n")
                    + ("OVERWORLD_FEMALE(sPicTable_F, SIZE_32x32, SHADOW_SIZE_M, TRACKS_FOOT, sAnimTable_Following)\n"
                       if i == 1 else "")
                    + "},\n"
                )
            (self.src / f"gen_{gen}_families.h").write_text(
                "".join(lines), encoding="utf-8")

    def test_dimension_inventory_and_female_frame(self):
        result = scanner.analyze(self.root)
        self.assertEqual(result["species_initializers_scanned"], 270)
        self.assertEqual(result["overview_counts"]["SIZE_64x64"], 9)
        self.assertEqual(result["overview_counts"]["SIZE_32x32"], 270)
        self.assertEqual(len(result["large_frame_declarations"]), 9)
        self.assertFalse(result["enabled_pokedex_size_proved"])
        self.assertFalse(result["runtime_vram_proved_by_this_inventory"])
        self.assertEqual(result["rom_bytes_saved"], 0)

    def test_fails_on_unknown_sprite_dimension(self):
        f = self.src / "gen_1_families.h"
        s = f.read_text()
        f.write_text(s.replace("SIZE_64x64", "SIZE_48x48", 1))
        with self.assertRaisesRegex(ValueError, "unexpected overworld syntax"):
            scanner.analyze(self.root)

    def test_missing_generation_is_fatal(self):
        (self.src / "gen_9_families.h").unlink()
        with self.assertRaises(FileNotFoundError):
            scanner.analyze(self.root)

    def test_duplicate_species_is_fatal(self):
        f = self.src / "gen_2_families.h"
        s = f.read_text()
        f.write_text(s.replace("SPECIES_TEST_G2_0", "SPECIES_TEST_G1_0"))
        with self.assertRaisesRegex(ValueError, "duplicate species"):
            scanner.analyze(self.root)


if __name__ == "__main__":
    unittest.main()
