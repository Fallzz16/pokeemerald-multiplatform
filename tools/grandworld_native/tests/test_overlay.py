import unittest
from tools.grandworld_native.overlay import DEFINES, IO, replace_exact

class OverlayTests(unittest.TestCase):
    def test_each_world_anchor_preserves_nonportable_define(self):
        for before, after in {**DEFINES, **IO}.items():
            self.assertIn(before, after)
            self.assertIn("#ifdef PORTABLE", after)
            self.assertIn("#else", after)
            self.assertIn("#endif", after)

    def test_exact_replacement(self):
        src = "first\n#define VRAM      0x6000000\nlast"
        patched = replace_exact(src, {"#define VRAM      0x6000000": DEFINES["#define VRAM      0x6000000"]})
        self.assertIn("extern unsigned char VRAM_", patched)
        self.assertTrue(patched.startswith("first\n"))
        self.assertTrue(patched.endswith("\nlast"))

    def test_modified_upstream_fails_closed(self):
        with self.assertRaises(ValueError):
            replace_exact("altered", DEFINES)
        with self.assertRaises(ValueError):
            replace_exact("#define PLTT          0x5000000\n#define PLTT          0x5000000",
                          {"#define PLTT          0x5000000": "patched"})

if __name__ == "__main__":
    unittest.main()
