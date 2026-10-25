"""Portable-only nested save ABI layout overlay tests."""
import unittest
from tools.grandworld_native.save_struct_overlay import DECLARATIONS, transform

class NestedABITests(unittest.TestCase):
    def test_immutable_original_declarations_under_arm(self):
        source = "\n".join(DECLARATIONS)
        modified = transform(source)
        for decl in DECLARATIONS:
            self.assertIn(decl[:-2], modified)
        self.assertEqual(modified.count("#if defined(PORTABLE)"), len(DECLARATIONS))
        self.assertEqual(modified.count("__attribute__((aligned(4)))"), len(DECLARATIONS))
        self.assertEqual(modified.count("#endif"), len(DECLARATIONS))
    def test_refuse_drift_or_repeated_application(self):
        source = "\n".join(DECLARATIONS)
        with self.assertRaises(ValueError):
            transform(source.replace("u16 quantity;", "u32 quantity;"))
        with self.assertRaises(ValueError):
            transform(transform(source))

if __name__ == "__main__":
    unittest.main()
