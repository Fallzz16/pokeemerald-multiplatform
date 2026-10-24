"""Regression for the evidence-backed Wally mGBA input repair."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "catch_fix", Path(__file__).resolve().parents[1] / "fix_catch_tutorial_input.py")
fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)


class CatchFixTests(unittest.TestCase):
    def test_exactly_one_input_changed_and_assertions_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "CatchTutorial.lua"
            data = ('local function watchTutorial(tag, budget)\n'
                    'if i % 24 == 0 then F.press("B", 1) end\n'
                    'F.check("wally text names WALLY", wallyText ~= nil)\n'
                    'F.check("kanto_text_has_no_WALLY", true)\nend\n')
            f.write_text(data)
            fix.apply(f)
            result = f.read_text()
            self.assertEqual(result.replace(fix.AFTER, fix.BEFORE), data)
            self.assertIn('F.check("wally text names WALLY", wallyText ~= nil)', result)
            self.assertIn('F.check("kanto_text_has_no_WALLY", true)', result)
            with self.assertRaisesRegex(ValueError, "drift"):
                fix.apply(f)

    def test_rejects_missing_or_duplicate_hook_without_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "CatchTutorial.lua"
            for data in ('unrelated content', fix.BEFORE + '\n' + fix.BEFORE):
                with self.subTest(data=data):
                    f.write_text(data)
                    with self.assertRaisesRegex(ValueError, "drift"):
                        fix.apply(f)
                    self.assertEqual(f.read_text(), data)


if __name__ == "__main__":
    unittest.main()
