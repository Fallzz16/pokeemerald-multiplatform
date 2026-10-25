"""P2 World frame extraction safety tests; no changes to GBA or real saves."""
import unittest
from tools.grandworld_native.world_frame_overlay import transform, BOOT, LOOP_START, LOOP_END, NEXT_SECTION

SAMPLE = (
    "void AgbMain(void)\n{\n" + BOOT + "\n}\n\n" +
    LOOP_START +
    "        ReadKeys();\n"
    "        if (gSoftResetDisabled) {\n"
    "            UpdateLinkAndCallCallbacks();\n"
    "        }\n"
    "        PlayTimeCounter_Update();\n"
    "        MapMusicMain();\n" +
    LOOP_END + NEXT_SECTION + "\n    foo();\n}\n"
)
class FrameOverlayTests(unittest.TestCase):
    def test_portable_frame_matches_actual_loop_body(self):
        edited = transform(SAMPLE)
        self.assertIn(LOOP_START, edited)
        self.assertIn(LOOP_END, edited)
        self.assertEqual(edited.count("void GwWorldFrame("), 1)
        self.assertEqual(edited.count("void GwWorldVBlank("), 1)
        # The native loop performs the same game operations, minus CPU busy-wait.
        native = edited.split("void GwWorldFrame(void)", 1)[1]
        self.assertIn("ReadKeys();", native)
        self.assertIn("MapMusicMain();", native)
        self.assertNotIn("WaitForVBlank();", native)
        self.assertIn("#else\n" + BOOT + "\n#endif", edited)

    def test_original_bios_loop_not_broken_when_guards_disabled(self):
        edited = transform(SAMPLE)
        self.assertIn(LOOP_START + SAMPLE.split(LOOP_START,1)[1].split(LOOP_END,1)[0] + LOOP_END, edited)

    def test_anchor_drift_and_repeat_rejected(self):
        for bad in (SAMPLE.replace("MapMusicMain();", "Bar();"),
                    SAMPLE.replace("WaitForVBlank();", "Other();"),
                    SAMPLE.replace("ReadKeys();", "Other();"),
                    SAMPLE.replace(BOOT, "Other();")):
            with self.assertRaises(ValueError):
                transform(bad)
        with self.assertRaises(ValueError):
            transform(transform(SAMPLE))

if __name__ == "__main__":
    unittest.main()
