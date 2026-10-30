"""Ensure asset inventory never changes, deletes, or mistakes near matches."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "master_asset_inventory.py"
spec = importlib.util.spec_from_file_location("master_asset_inventory", SOURCE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AssetInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.world = Path(self.tmp.name)
        (self.world / "Makefile").write_text("modern:\n\t@true\n")
        (self.world / "graphics").mkdir()
        (self.world / "sound").mkdir()
        self.a = self.world / "graphics" / "a.png"
        self.b = self.world / "graphics" / "b.png"
        self.c = self.world / "sound" / "c.wav"
        self.a.write_bytes(b"pixel sprite")
        self.b.write_bytes(b"pixel sprite")
        self.c.write_bytes(b"different")

    def test_exact_duplicates_only_and_no_mutations(self):
        before = [f.read_bytes() for f in (self.a, self.b, self.c)]
        result = audit.inventory(self.world)
        self.assertEqual(result["exact_duplicate_sets"], 1)
        self.assertEqual(result["files_scanned"], 3)
        self.assertEqual(result["raw_source_duplicate_bytes_upper_bound"], 12)
        self.assertFalse(result["modifications_applied"])
        self.assertEqual(result["actual_rom_bytes_saved"], 0)
        self.assertEqual(before, [f.read_bytes() for f in (self.a, self.b, self.c)])

    def test_similar_is_not_identical(self):
        self.b.write_bytes(b"pixel spritE")
        result = audit.inventory(self.world)
        self.assertEqual(result["exact_duplicate_sets"], 0)

    def test_skips_symlinks_to_protect_external_paths(self):
        (self.world / "graphics" / "linked.png").symlink_to(self.a)
        self.assertEqual(audit.inventory(self.world)["files_scanned"], 3)

    def test_missing_checkout_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Makefile missing"):
            audit.inventory(self.world / "unknown")

    def test_missing_assets_fails_closed(self):
        self.c.unlink()
        (self.world / "sound").rmdir()
        with self.assertRaisesRegex(ValueError, "source folder"):
            audit.inventory(self.world)


if __name__ == "__main__":
    unittest.main()
