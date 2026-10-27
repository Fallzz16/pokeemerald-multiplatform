"""Focused tests for the real GBA NPC catalog and script source anchors."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "add_npc_avatar_picker.py"
spec = importlib.util.spec_from_file_location("gw_npc_picker", p)
gw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gw)

class NpcPickerTests(unittest.TestCase):
    def test_all_requested_approved_names_unique(self):
        self.assertGreaterEqual(len(gw.HUMAN_NPCS), 100)
        self.assertEqual(len(gw.HUMAN_NPCS), len(set(gw.HUMAN_NPCS)))
        for hero in ("RED", "LEAF", "BROCK", "MISTY", "GIOVANNI",
                     "STEVEN", "WALLY", "CYNTHIA"):
            if hero == "CYNTHIA":
                self.assertNotIn(hero, gw.HUMAN_NPCS)  # not originally available in pinned World
            else:
                self.assertIn(hero, gw.HUMAN_NPCS)
    def test_catalog_has_no_quiet_gfx_number_guesses(self):
        head = gw.header_text(["BROCK", "MISTY"])
        self.assertIn("OBJ_EVENT_GFX_BROCK", head)
        self.assertIn("OBJ_EVENT_GFX_MISTY", head)
        self.assertIn("sGWAvatarClassicName, 0", head)
        self.assertNotIn("3284", head)  # unverified Quetzal ROM graphics indices
    def test_fail_closed_anchor_missing(self):
        with self.assertRaisesRegex(ValueError, "exactly one"):
            gw.replace_once("some other text", "old", "new", "fixture")
    def test_fail_closed_duplicate_anchor(self):
        with self.assertRaisesRegex(ValueError, "saw 2"):
            gw.replace_once("AAA/AAA", "AAA", "BBB", "fixture")
    def test_six_row_pagination_is_bounded(self):
        self.assertEqual(gw.PAGE_SIZE, 6)
        self.assertLess(len(gw.HUMAN_NPCS), 256)  # persisted index fits in existing u16
        self.assertEqual(gw.VAR_ID, "0x40E5")

if __name__ == "__main__":
    unittest.main()
