"""Isolated tests of WRAM staging queue: never mutate the stable game."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE=Path(__file__).resolve().parents[1]/"groudon_wram_stage_overlay.py"
spec=importlib.util.spec_from_file_location("groudon_wram_stage_overlay",SOURCE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class GroudonWRAMStageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.world=Path(self.temp.name)
        (self.world/"Makefile").write_text("modern:\n")
        (self.world/"src").mkdir()
        (self.world/"test/overworld").mkdir(parents=True)
        self.sprite=self.world/"src/sprite.c"
        self.generator=self.world/"test/overworld/GenLuaSymbols.py"
        self.sprite.write_text(
            mod.DECLARE_ORIGINAL+"\n\n"+
            mod.CLEAR_ORIGINAL+"\n\n"+
            mod.COMPACT_ORIGINAL+"\n\n"+
            mod.SPRITE_COPY_NEW+"\n\n"+
            mod.PROCESS_ORIGINAL+"\n\n"+
            mod.REQUEST_NEW+"\n",encoding="utf-8")
        self.generator.write_text(mod.SYMBOL_ORIGINAL,encoding="utf-8")

    def test_non_mutating_preflight(self):
        old=(self.sprite.read_bytes(),self.generator.read_bytes())
        report=mod.stage(self.world)
        self.assertEqual(report["staged_total_bytes"],8192)
        self.assertEqual(report["slots"],4)
        self.assertFalse(report["release_ready"])
        self.assertEqual(old,(self.sprite.read_bytes(),self.generator.read_bytes()))

    def test_proper_queue_ownership_and_fallback(self):
        mod.stage(self.world,write=True)
        source=self.sprite.read_text()
        self.assertIn("LZ77UnCompWram",source)
        self.assertIn("LZ77UnCompVram",source)
        self.assertIn("sGWGroudonStagedSlots++",source)
        self.assertIn("sGWGroudonStaging[slot]",source)
        self.assertIn("REG_VCOUNT < DISPLAY_HEIGHT",source)
        self.assertIn("request->size & 0x7FFF",source)
        self.assertEqual(source.count("sGWGroudonStagedSlots = 0;"),3) # declaration + consume + cancel
        self.assertIn("gGWGroudonStagingFallbacks",self.generator.read_text())

    def test_source_changes_fail_without_partial_write(self):
        saved=self.sprite.read_bytes()
        self.generator.write_text("bogus generator",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"FAIL CLOSED"):
            mod.stage(self.world,write=True)
        self.assertEqual(self.sprite.read_bytes(),saved)

    def test_does_not_apply_twice(self):
        mod.stage(self.world,write=True)
        before=self.sprite.read_bytes()
        with self.assertRaisesRegex(ValueError,"FAIL CLOSED"):
            mod.stage(self.world,write=True)
        self.assertEqual(self.sprite.read_bytes(),before)


if __name__=="__main__":
    unittest.main()
