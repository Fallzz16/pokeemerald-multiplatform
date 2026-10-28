"""M9: fail-closed test-only OWE stage counter instrumentation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SRC = Path(__file__).resolve().parents[1] / "instrument_m9_owe_trace.py"
spec = importlib.util.spec_from_file_location("gw_m9_trace", SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class M9OweTraceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / "Makefile").write_text("modern:\n\t@true\n")
        p = self.root / "include/config/wild_encounter.h"
        p.parent.mkdir(parents=True)
        p.write_text("#define WE_OW_ENCOUNTERS                        TRUE\n")
        p = self.root / "src/wild_encounter_ow.c"
        p.parent.mkdir(parents=True)
        p.write_text("// unchanged header\n" + "\n".join(
            before for before, _ in mod.REPLACEMENTS) + "\n// unchanged footer\n")
        self.source = p

    def test_preflight_read_only(self):
        original = self.source.read_bytes()
        r = mod.run(self.root)
        self.assertEqual(r["mode"], "preflight")
        self.assertEqual(r["counter_fields"], 12)
        self.assertFalse(r["actual_gameplay_approved"])
        self.assertEqual(original, self.source.read_bytes())

    def test_scoped_transform(self):
        original = self.source.read_text()
        result = mod.run(self.root, True)
        updated = self.source.read_text()
        self.assertEqual(result["mode"], "applied")
        self.assertIn("unchanged header", updated)
        self.assertIn("unchanged footer", updated)
        for old, replacement in mod.REPLACEMENTS:
            self.assertIn(replacement, updated)
            self.assertNotIn(old, updated.replace(replacement, ""))
        self.assertNotEqual(original, updated)

    def test_no_repeat(self):
        mod.run(self.root, True)
        with self.assertRaisesRegex(ValueError, "anchor"):
            mod.run(self.root, True)

    def test_edited_source_rejected_without_partial_write(self):
        current = self.source.read_text().replace(
            mod.TILE_OLD, "// changed native spawn")
        self.source.write_text(current)
        with self.assertRaisesRegex(ValueError, "anchor"):
            mod.run(self.root, True)
        self.assertEqual(current, self.source.read_text())

    def test_duplicate_source_rejected(self):
        self.source.write_text(self.source.read_text() + mod.TILE_OLD)
        with self.assertRaisesRegex(ValueError, "anchor"):
            mod.run(self.root, True)

    def test_disabled_owe_refused(self):
        p = self.root / "include/config/wild_encounter.h"
        p.write_text("#define WE_OW_ENCOUNTERS                        FALSE\n")
        with self.assertRaisesRegex(ValueError, "disabled"):
            mod.run(self.root, True)


if __name__ == "__main__":
    unittest.main()
