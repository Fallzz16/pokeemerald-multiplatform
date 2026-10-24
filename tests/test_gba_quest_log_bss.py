"""Verify Quest UI has no initialized writable handles in unsupported GBA .data.

The assertion is intentionally source-level; actual GNU ld still validates
whether the resulting ARM object contains discarded initialized sections.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
QUEST = ROOT / "src" / "quest_log.c"


class QuestLogGbaBssTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = QUEST.read_text(encoding="utf-8")

    def test_window_handles_use_zero_initialized_bss(self):
        for name in ("Backdrop", "Header", "Body", "Footer"):
            with self.subTest(name=name):
                self.assertRegex(self.source,
                                 rf"static u8 sQuest{name}WindowId;")
                self.assertNotRegex(self.source,
                                    rf"static u8 sQuest{name}WindowId\s*=")

    def test_open_establishes_valid_handles_before_allocating(self):
        block = self.source.split("void QuestLog_Open(void)", 1)[1].split(
            "void QuestLog_Close(void)", 1)[0]
        for name in ("Backdrop", "Header", "Body", "Footer"):
            self.assertIn(f"sQuest{name}WindowId = WINDOW_NONE;", block)
        self.assertIn("sQuestWindowsCreated = TRUE;", block)
        self.assertLess(block.index("sQuestWindowsCreated = TRUE;"),
                        block.index("AddWindow("))

    def test_cleanup_and_update_protect_unopened_state(self):
        cleanup = self.source.split("void QuestLog_Close(void)", 1)[1].split(
            "bool8 QuestLog_Update(void)", 1)[0]
        self.assertIn("if (!sQuestWindowsCreated)", cleanup)
        self.assertIn("sQuestWindowsCreated = FALSE;", cleanup)
        update = self.source.split("bool8 QuestLog_Update(void)", 1)[1].split(
            "bool8 QuestLog_HasActiveQuest(void)", 1)[0]
        self.assertIn("if (!sQuestWindowsCreated", update)


if __name__ == "__main__":
    unittest.main(verbosity=2)
