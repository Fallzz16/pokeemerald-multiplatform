"""Fail-closed test-only Groudon frame LZ10 integration checks."""
import importlib.util
from pathlib import Path
import tempfile
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1]/"apply_groudon_frame_lz10.py"
sys.path.insert(0,str(SOURCE.parent))
spec=importlib.util.spec_from_file_location("apply_groudon_frame_lz10",SOURCE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class GroudonPilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.world=Path(self.tmp.name)
        (self.world/"src/data/object_events").mkdir(parents=True)
        (self.world/"include/config").mkdir(parents=True)
        (self.world/"Makefile").write_text("all:\n",encoding="utf-8")
        (self.world/"include/config/overworld.h").write_text(
            "#define OW_GFX_COMPRESS                FALSE\n",encoding="utf-8")
        self.table=self.world/"src/data/object_events/object_event_pic_tables_followers.h"
        self.sprite=self.world/"src/sprite.c"
        self.table.write_text(mod.ANIM_ORIGINAL+"\n",encoding="utf-8")
        self.sprite.write_text(
            '#include "sprite.h"\n'+mod.SPRITE_COPY_ORIGINAL+"\n"
            +mod.REQUEST_ORIGINAL+"\n",encoding="utf-8")
        self.nm="08001000 00003000 R gObjectEventPic_Groudon\n"
        self.cart=bytearray(mod.ROM_BYTES)
        self.cart[0xAC:0xB0]=b"BPEE"
        # Six visually distinct but individually repetitive 2048 B frames.
        for i in range(mod.FRAME_COUNT):
            self.cart[0x1000+i*mod.FRAME_BYTES:
                      0x1000+(i+1)*mod.FRAME_BYTES]=bytes([i])*mod.FRAME_BYTES

    def test_dryrun_has_zero_source_changes(self):
        original=[self.table.read_bytes(),self.sprite.read_bytes()]
        report=mod.apply(self.world,self.nm,self.cart)
        self.assertEqual(report["raw_frames"],6)
        self.assertTrue(report["all_frames_lossless_roundtrip"])
        self.assertFalse(report["whole_sheet_compression"])
        self.assertIsNone(report["actual_rom_bytes_saved"])
        self.assertEqual(original,[self.table.read_bytes(),self.sprite.read_bytes()])
        self.assertFalse((self.world/"src/data/object_events/grandworld_groudon_frame_lz10.h").exists())

    def test_apply_emits_exactly_six_packed_frames(self):
        report=mod.apply(self.world,self.nm,self.cart,write=True)
        table=self.table.read_text()
        sprite=self.sprite.read_text()
        header=(self.world/"src/data/object_events/grandworld_groudon_frame_lz10.h").read_text()
        self.assertEqual(table.count(".relativeFrames = 2"),6)
        self.assertIn('#include "grandworld_groudon_frame_lz10.h"',table)
        for i in range(6):
            self.assertIn("sGWGroudonLzFrame"+str(i),header)
        self.assertIn("LZ77UnCompVram",sprite)
        self.assertIn("images[0].relativeFrames == 2",sprite)
        self.assertIn("sSpriteCopyRequests[i].size & 0x8000",sprite)
        self.assertTrue(report["candidate_raw_byte_saving_before_code_overhead"]>0)
        # The generated ROM bytes are padded to u32 alignment, not output frames.
        self.assertEqual(header.count("static const u32"),6)

    def test_preflight_rejects_wrong_graphics_size(self):
        with self.assertRaisesRegex(ValueError,"Groudon 64x64 x6"):
            mod.apply(self.world,"08001000 00002000 R gObjectEventPic_Groudon\n",self.cart)

    def test_preflight_rejects_corrupt_anchor_without_partial_write(self):
        self.table.write_text("wrong source\n")
        saved=self.sprite.read_bytes()
        with self.assertRaisesRegex(ValueError,"FAIL CLOSED"):
            mod.apply(self.world,self.nm,self.cart,write=True)
        self.assertEqual(saved,self.sprite.read_bytes())

    def test_preflight_rejects_enabled_whole_sheet_compression(self):
        (self.world/"include/config/overworld.h").write_text(
            "#define OW_GFX_COMPRESS TRUE\n")
        with self.assertRaisesRegex(ValueError,"whole-sheet"):
            mod.apply(self.world,self.nm,self.cart)


if __name__=="__main__":
    unittest.main()
