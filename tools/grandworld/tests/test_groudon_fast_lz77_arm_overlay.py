"""Fail-closed switch test: faster ARM LZ10 decoder, unchanged runtime semantics."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/"groudon_fast_lz77_arm_overlay.py"
spec=importlib.util.spec_from_file_location("groudon_fast_lz77_arm_overlay",SOURCE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FastArmLZ77Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.world=Path(self.temp.name)
        (self.world/"src").mkdir()
        (self.world/"Makefile").write_text("modern:\n")
        self.source=self.world/"src/sprite.c"
        self.asm=self.world/"src/gw_fast_lz77.s"
        self.asm.write_text("@ MIT License\n.arm\n"+mod.SYMBOL+":\n    bx lr\n")
        self.source.write_text(mod.PROTOTYPE_ANCHOR+
            "void test(void) {\n"
            "    CycleCountStart();\n"+mod.INVOKE+"\n"
            "    CycleCountEnd();\n"+mod.INVOKE+"\n}\n")

    def test_readonly_and_two_timed_calls(self):
        previous=self.source.read_bytes()
        r=mod.patch(self.world)
        self.assertEqual(r["replacement_call_sites"],2)
        self.assertFalse(r["speed_win_proved"])
        self.assertEqual(previous,self.source.read_bytes())

    def test_apply_and_leave_other_functions(self):
        mod.patch(self.world,write=True)
        changed=self.source.read_text()
        self.assertEqual(changed.count(mod.REPLACEMENT),2)
        self.assertIn("CycleCountStart();",changed)
        self.assertIn("CycleCountEnd();",changed)
        self.assertIn("extern void LZ77UnCompWrite16bit",changed)

    def test_reject_unlicensed_or_missing_arm_source(self):
        old=self.source.read_bytes()
        self.asm.write_text(".arm\nLZ77UnCompWrite16bit:\n bx lr\n")
        with self.assertRaisesRegex(ValueError,"MIT license"):
            mod.patch(self.world,write=True)
        self.assertEqual(self.source.read_bytes(),old)

    def test_double_apply_refused(self):
        mod.patch(self.world,write=True)
        with self.assertRaisesRegex(ValueError,"FAIL CLOSED"):
            mod.patch(self.world,write=True)


if __name__=="__main__":
    unittest.main()
