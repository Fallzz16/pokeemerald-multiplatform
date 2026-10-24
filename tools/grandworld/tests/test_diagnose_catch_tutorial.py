"""Ensure the diagnostic variant never removes or alters a gameplay assertion."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / "diagnose_catch_tutorial.py"
spec = importlib.util.spec_from_file_location("diagnose_catch", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DiagnosticTests(unittest.TestCase):
    def test_only_wally_input_changes(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / "original.lua", Path(d) / "variant.lua"
            original = ('local function watchTutorial(tag, budget)\n'
                        'if i % 24 == 0 then F.press("B", 1) end\n'
                        'F.check("wally text names WALLY", condition)\nend\n')
            src.write_text(original)
            module.prepare(src, dst)
            modified = dst.read_text()
            self.assertEqual(modified.count('F.check("wally text names WALLY", condition)'), 1)
            self.assertEqual(modified.count('F.press("B", 1)'), 1)
            self.assertIn('if tag == "kanto" and i % 24 == 0', modified)

    def test_rejects_upstream_drift_and_existing_destination(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / "original.lua", Path(d) / "variant.lua"
            src.write_text('no expected patch anchor')
            with self.assertRaises(ValueError):
                module.prepare(src, dst)
            src.write_text('if i % 24 == 0 then F.press("B", 1) end')
            dst.write_text('existing evidence')
            with self.assertRaises(ValueError):
                module.prepare(src, dst)


if __name__ == "__main__":
    unittest.main()
