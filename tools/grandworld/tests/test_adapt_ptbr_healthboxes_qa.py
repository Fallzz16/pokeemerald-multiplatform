"""PT-BR localization must not weaken any battle healthbox assertions."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / "adapt_ptbr_healthboxes_qa.py"
spec = importlib.util.spec_from_file_location("healthqa", PATH)
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)

CHECKS = (
    'F.check("gNumSafariBalls is 29 after one throw", true)\n'
    'F.check("an HP word changed (not the bar alone)", true)\n'
    'F.check("doubles_healthbox_reached", true)\n'
    'F.check("a doubles healthbox sprite is live", true)\n'
    'F.check("field control returns after doubles", true)\n'
)
ORIGINAL_SOURCE = CHECKS + (
    'if ' + qa.ORIGINAL + ' then return true end\n'
    'return ' + qa.ORIGINAL + ' ~= nil\n'
    'if ' + qa.ORIGINAL + ' then break end\n'
)


class HealthboxLocalizationQATests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.lua = self.root / qa.SCRIPT
        self.battle = self.root / qa.BATTLE
        self.lua.parent.mkdir(parents=True)
        self.battle.parent.mkdir(parents=True)
        self.lua.write_text(ORIGINAL_SOURCE, encoding="utf-8")
        self.battle.write_text(qa.LOCALIZED, encoding="utf-8")

    def test_preflight_is_read_only(self):
        self.assertEqual(qa.apply(self.root)["status"], "preflight")
        self.assertEqual(self.lua.read_text(), ORIGINAL_SOURCE)

    def test_only_three_text_lookups_change(self):
        result = qa.apply(self.root, True)
        updated = self.lua.read_text()
        self.assertEqual(result["changes"], 3)
        self.assertEqual(result["gameplay_files_changed"], 0)
        self.assertEqual(updated, ORIGINAL_SOURCE.replace(qa.ORIGINAL, qa.BILINGUAL))
        self.assertTrue(all(token in updated for token in CHECKS.strip().splitlines()))

    def test_missing_ptbr_prompt_fails_closed(self):
        self.battle.write_text("English")
        with self.assertRaisesRegex(ValueError, "localized battle action prompt"):
            qa.apply(self.root, True)
        self.assertEqual(self.lua.read_text(), ORIGINAL_SOURCE)

    def test_missing_healthbox_assertion_fails_closed(self):
        self.lua.write_text(ORIGINAL_SOURCE.replace('F.check("doubles_healthbox_reached"', 'F.check("oops"'))
        with self.assertRaisesRegex(ValueError, "gameplay assertion"):
            qa.apply(self.root, True)

    def test_changed_literal_count_fails_closed(self):
        self.lua.write_text(ORIGINAL_SOURCE.replace(qa.ORIGINAL, "something_else()", 1))
        with self.assertRaisesRegex(ValueError, "prompt anchors"):
            qa.apply(self.root, True)

    def test_reapplication_is_rejected(self):
        qa.apply(self.root, True)
        with self.assertRaisesRegex(ValueError, "prompt anchors"):
            qa.apply(self.root, True)


if __name__ == "__main__":
    unittest.main()
