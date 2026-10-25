"""The save ABI patch must only change two portable-only declarations."""
from pathlib import Path
import tempfile
import unittest

from tools.grandworld_native.save_abi_overlay import (
    TIME, DOME, ASSERTION, transform, stage
)

SOURCE = "#include <stdint.h>\n" + TIME + "\n" + DOME + "\n" + ASSERTION + "\n"

class PortableSaveOverlayTests(unittest.TestCase):
    def test_two_guards_preserve_gba_declarations(self):
        target = transform(SOURCE)
        self.assertEqual(target.count("#if defined(PORTABLE)"), 2)
        self.assertIn(ASSERTION, target)
        self.assertIn("struct Time", target)
        self.assertIn("struct BattleDomeTrainer", target)
        self.assertNotEqual(SOURCE, target)

    def test_anchor_drift_fails_closed(self):
        with self.assertRaises(ValueError):
            transform(SOURCE.replace("struct Time", "struct TimeChanged"))
        with self.assertRaises(ValueError):
            transform(SOURCE.replace(ASSERTION, ""))

    def test_dry_run_never_edits_world(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header = root / "include/global.h"
            header.parent.mkdir()
            (root / "src").mkdir()
            (root / "src/region_switch.c").write_text("", encoding="utf-8")
            header.write_text(SOURCE, encoding="utf-8")
            report = root / "report.json"
            data = stage(root, report, False)
            self.assertEqual(header.read_text(encoding="utf-8"), SOURCE)
            self.assertFalse(data["apply_requested"])
            self.assertFalse(data["save_assert_removed"])
            self.assertTrue(report.is_file())

    def test_apply_only_to_disposable_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header = root / "include/global.h"
            header.parent.mkdir()
            (root / "src").mkdir()
            (root / "src/region_switch.c").write_text("", encoding="utf-8")
            header.write_text(SOURCE, encoding="utf-8")
            stage(root, root / "audit.json", True)
            self.assertEqual(header.read_text(encoding="utf-8"), transform(SOURCE))
            with self.assertRaises(ValueError):
                stage(root, root / "audit2.json", True)  # Cannot be applied twice.

if __name__ == "__main__":
    unittest.main()
