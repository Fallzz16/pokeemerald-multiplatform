"""Regression: translation may not disable starter exclusivity QA checks."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "adapt_ptbr_greedy_gifts_qa.py"
spec = importlib.util.spec_from_file_location("ptbr_qa", SCRIPT)
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)

ELM_LINE = 'if "Probably shouldn\'t touch" not in elm:'
FAKE = (
    "def test_starters():\n"
    "    " + ELM_LINE + "\n"
    "        bad.append('Elm missing')\n"
    "    if 'FLAG_JOHTO_STARTER_CHOSEN' not in body:\n"
    "        bad.append('Johto flag missing')\n"
    "    " + qa.OLD + "\n"
    "        bad.append('Birch missing')\n"
)


class PTBRGreedyGiftQATests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.check = self.root / qa.QA_PATH
        self.script = self.root / qa.MAP_PATH
        self.check.parent.mkdir(parents=True)
        self.script.parent.mkdir(parents=True)
        self.check.write_text(FAKE, encoding="utf-8")
        self.script.write_text(
            qa.MARKER + '\n\t.string "Voce ja pegou seu POKEMON.\\nDeixe os outros descansarem.$"\n',
            encoding="utf-8")

    def test_preflight_does_not_write(self):
        self.assertEqual(qa.apply(self.root)["mode"], "preflight")
        self.assertEqual(self.check.read_text(), FAKE)

    def test_only_one_qa_assertion_changes(self):
        result = qa.apply(self.root, write=True)
        self.assertTrue(result["qa_guard_preserved"])
        self.assertEqual(result["gameplay_files_modified"], 0)
        self.assertEqual(self.check.read_text(), FAKE.replace(qa.OLD, qa.NEW))
        self.assertIn("FLAG_JOHTO_STARTER_CHOSEN", self.check.read_text())

    def test_missing_translated_birch_lock_rejected_without_writing(self):
        self.script.write_text(qa.MARKER + '\n\t.string "Wrong text$"\n')
        with self.assertRaisesRegex(ValueError, "starter lock"):
            qa.apply(self.root, write=True)
        self.assertEqual(self.check.read_text(), FAKE)

    def test_drifted_original_qa_guard_rejected(self):
        self.check.write_text(FAKE.replace(qa.OLD, "if True:"))
        with self.assertRaisesRegex(ValueError, "QA guard changed"):
            qa.apply(self.root, write=True)

    def test_no_elm_gate_cannot_pass(self):
        self.check.write_text(FAKE.replace(ELM_LINE, "if False:"))
        with self.assertRaisesRegex(ValueError, "Elm starter protection"):
            qa.apply(self.root, write=True)

    def test_reapplication_is_rejected(self):
        qa.apply(self.root, write=True)
        with self.assertRaisesRegex(ValueError, "QA guard changed"):
            qa.apply(self.root, write=True)


if __name__ == "__main__":
    unittest.main()
