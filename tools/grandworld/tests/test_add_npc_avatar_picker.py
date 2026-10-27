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
    def test_header_stores_strings_and_graphics_only_once(self):
        head = gw.header_text(gw.HUMAN_NPCS)
        self.assertEqual(len(gw.HUMAN_NPCS), 192)
        self.assertIn("#define GW_AVATAR_CHOICES_COUNT 193", head)
        self.assertIn("extern const struct GWAvatarChoice sGWAvatarChoices[", head)
        self.assertIn("#ifdef GW_NPC_AVATAR_DEFINE", head)
        self.assertEqual(head.count("const struct GWAvatarChoice sGWAvatarChoices["), 2)
        self.assertEqual(head.count("static const u8 sGWAvatarName"), 192)
        self.assertEqual(head.count("static const u8 sGWAvatarClassicName"), 1)

    def test_repeated_pagination_does_not_allocate_or_free_windows(self):
        body = gw.INTRO_FUNCTIONS
        begin = body.index("static void GW_AvatarMenuInput(u8 taskId)\n{")
        pagination = body[begin:body.index("    input = Menu_ProcessInputNoWrap();", begin)]
        self.assertIn("GW_DrawAvatarChoices(taskId, FALSE)", pagination)
        self.assertNotIn("AddWindow(", pagination)
        self.assertNotIn("RemoveWindow(", pagination)
        self.assertEqual(body.count("AddWindow(&sGWAvatarWindow)"), 1)
        self.assertIn("if (window == WINDOW_NONE)", body)
        self.assertIn("VarSet(VAR_GW_NPC_AVATAR, 0)", body)

    def test_prompt_does_not_redraw_large_intro_dialogue_over_picker(self):
        body = gw.INTRO_FUNCTIONS
        self.assertIn("AddWindow(&sOutfitPromptWindowTemplate)", body)
        self.assertIn("IsTextPrinterActiveOnWindow(tPromptWindowId)", body)
        self.assertNotIn("OakSpeechPrintMessage(sGWAvatarHelp", body)
        self.assertIn("firstDraw ? COPYWIN_FULL : COPYWIN_GFX", body)
        self.assertIn("ClearDialogWindowAndFrame(tPromptWindowId, TRUE)", body)

    def test_existing_intro_prompt_task_macros_have_data_pointer(self):
        # Oak's tPromptWindowId is a preprocessor alias for data[N].
        # Without a local 'data' variable the GBA compiler rejects the file.
        source = gw.INTRO_FUNCTIONS
        for function in ("GW_DrawAvatarChoices", "GW_CloseAvatarChoices",
                         "GW_AvatarMenuStart", "GW_AvatarMenuShow"):
            marker = "static void " + function + "(u8 taskId"
            start = source.index(marker)
            open_brace = source.index("{", start)
            body = source[open_brace:open_brace + 100]
            with self.subTest(function=function):
                self.assertIn("s16 *data = gTasks[taskId].data;", body)

    def test_oak_menu_window_slot_does_not_alias_pagination(self):
        # Pinned World uses tMenuWindowId = data[13] in src/oak_speech.c.
        # A page index in data[13] silently modifies the active window ID,
        # sending later draws to unrelated windows (seen in mGBA 10/13).
        body = gw.INTRO_FUNCTIONS
        self.assertEqual(body.count("gTasks[taskId].data[12]"), 5)
        self.assertNotIn("gTasks[taskId].data[13]", body)
        self.assertIn("gTasks[taskId].tMenuWindowId", body)

    def test_menu_fits_gba_bg_tiles_without_overrun(self):
        import re
        body = gw.INTRO_FUNCTIONS
        base = int(re.search(r"baseBlock = (\d+)", body).group(1))
        width = int(re.search(r"width = (\d+)", body).group(1))
        height = int(re.search(r"height = (\d+)", body).group(1))
        self.assertLessEqual(base + width * height, 512)
        self.assertEqual(gw.PAGE_SIZE, 6)
        self.assertEqual((len(gw.HUMAN_NPCS) + gw.PAGE_SIZE) // gw.PAGE_SIZE, 33)

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
