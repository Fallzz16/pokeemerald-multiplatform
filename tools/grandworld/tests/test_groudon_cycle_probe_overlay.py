"""Unit tests for disposable-only real ARM/GBA Timer2+3 profiling overlay."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SRC=Path(__file__).resolve().parents[1]/"groudon_cycle_probe_overlay.py"
spec=importlib.util.spec_from_file_location("groudon_cycle_probe_overlay",SRC)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CycleProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"src").mkdir()
        (self.root/"test/overworld/lua").mkdir(parents=True)
        self.sprite=self.root/"src/sprite.c"
        self.symbols=self.root/"test/overworld/GenLuaSymbols.py"
        self.sprite.write_text('#include "sprite.h"\n'+mod.GLOBALS_ANCHOR+mod.SRC_ANCHOR+"\n")
        self.symbols.write_text(mod.SYMBOL_ANCHOR)
        self.qa='F.run(function()\n'+mod.QA_MARKER+'end)\n'

    def test_readonly_preflight_and_generated_references(self):
        before=(self.sprite.read_bytes(),self.symbols.read_bytes())
        r=mod.instrument(self.root,self.qa)
        self.assertFalse(r["ready_for_release"])
        self.assertEqual(r["extra_static_ewram_bytes"],16)
        self.assertEqual(before,(self.sprite.read_bytes(),self.symbols.read_bytes()))

    def test_apply_writes_only_disposable_profiler(self):
        mod.instrument(self.root,self.qa,write=True)
        src=self.sprite.read_text()
        lua=(self.root/"test/overworld/lua/GrandWorldGroudonFollowerLZ10.lua").read_text()
        self.assertIn("CycleCountStart()",src)
        self.assertIn("CycleCountEnd()",src)
        self.assertIn("REG_TM2CNT_H | REG_TM3CNT_H",src)
        self.assertIn("GROUDON_CPU samples=",lua)
        self.assertIn("gGWLZPeakCycles",self.symbols.read_text())

    def test_fail_closed_no_partial_write(self):
        self.symbols.write_text("broken symbols",encoding="utf-8")
        before=self.sprite.read_bytes()
        with self.assertRaisesRegex(ValueError,"FAIL CLOSED"):
            mod.instrument(self.root,self.qa,write=True)
        self.assertEqual(before,self.sprite.read_bytes())

    def test_double_apply_refused(self):
        mod.instrument(self.root,self.qa,write=True)
        with self.assertRaisesRegex(ValueError,"FAIL CLOSED"):
            mod.instrument(self.root,self.qa,write=True)


if __name__=="__main__":
    unittest.main()
