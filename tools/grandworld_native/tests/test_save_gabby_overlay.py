import unittest
from tools.grandworld_native.save_gabby_overlay import ANCHOR, transform

class GabbySaveABITests(unittest.TestCase):
    def test_native_only_alignment_preserves_gba_source(self):
        source = "#if 1\n" + ANCHOR + "\n#endif\n"
        patched = transform(source)
        self.assertIn("#if defined(PORTABLE)\n__attribute__((aligned(4)))", patched)
        self.assertIn("#else", "#else")  # no edit of ARM path
        self.assertIn(ANCHOR[:-2], patched)
        self.assertEqual(patched.count("struct GabbyAndTyData"), 1)

    def test_fail_closed_on_source_drift_or_second_patch(self):
        with self.assertRaises(ValueError):
            transform(ANCHOR.replace("u8 valB_4:4;", "u16 valB_4:4;"))
        with self.assertRaises(ValueError):
            transform(transform(ANCHOR))

if __name__ == "__main__":
    unittest.main()
