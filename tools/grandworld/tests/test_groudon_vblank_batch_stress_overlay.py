"""Fail-closed native GBA sprite queue VBlank stress patch validation."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location("groudon_vblank_batch_stress_overlay",
                                            ROOT/"groudon_vblank_batch_stress_overlay.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class NativeQueueStressTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.world=Path(self.temp.name)
        (self.world/"src").mkdir()
        (self.world/"test/overworld").mkdir(parents=True)
        (self.world/"Makefile").write_text("modern:\n")
        self.src=self.world/"src/sprite.c"
        self.gen=self.world/"test/overworld/GenLuaSymbols.py"
        self.src.write_text(
            '#include "sprite.h"\n'+mod.OLD_GLOBAL+
            "void ProcessSpriteCopyRequests(void)\n{\n"
            "    if (sShouldProcessSpriteCopyRequests)\n    {\n"+
            mod.OLD_QUEUE_START+"\n        {\n"+mod.OLD_BODY+
            "\n            sSpriteCopyRequestCount--;\n            i++;\n        }\n"+
            mod.OLD_QUEUE_END+"\n",encoding="utf-8")
        self.gen.write_text(mod.OLD_SYMBOL,encoding="utf-8")

    def test_preflight_readonly(self):
        old=self.src.read_bytes()
        report=mod.instrument(self.world)
        self.assertEqual(report["stress_frame_copies_per_one_queue"],[1,2,3,4])
        self.assertFalse(report["different_simultaneously_visible_sprites_tested"])
        self.assertEqual(old,self.src.read_bytes())

    def test_instrument_actual_sprite_queue_and_limit_mode(self):
        mod.instrument(self.world,write=True)
        source=self.src.read_text()
        self.assertEqual(source.count("LZ77UnCompWrite16bit("),2)
        self.assertIn("gGWStressExtraCopies > 3 ? 3",source)
        self.assertIn("repeat <= stressMode",source)
        self.assertIn("batchCycles += cycles",source)
        self.assertIn("CpuCopy16",source)
        self.assertIn("REG_VCOUNT < DISPLAY_HEIGHT",source)
        self.assertIn("gGWStressOverBudgetBatches[stressMode]++",source)
        self.assertIn("gGWStressSamples",self.gen.read_text())

    def test_missing_anchor_never_partially_writes(self):
        before=self.src.read_bytes()
        self.gen.write_text("bad export symbols",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"FAIL CLOSED"):
            mod.instrument(self.world,write=True)
        self.assertEqual(self.src.read_bytes(),before)

    def test_double_apply_refused(self):
        mod.instrument(self.world,write=True)
        before=self.src.read_bytes()
        with self.assertRaisesRegex(ValueError,"FAIL CLOSED"):
            mod.instrument(self.world,write=True)
        self.assertEqual(self.src.read_bytes(),before)


if __name__=="__main__":
    unittest.main()
