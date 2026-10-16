"""Structural guard for native LAN sprite palette isolation.

This checks integration/guards, not GBA rendering; manual game QA required.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class RemotePaletteRegression(unittest.TestCase):
    def test_palette_allocation_is_remote_only(self):
        code = (ROOT / "src" / "event_object_movement.c").read_text(encoding="utf-8")
        start = code.index("#define LAN_REMOTE_PALETTE_TAG 0xECF0")
        end = code.index("void LanVirtualObjectMove", start)
        part = code[start:end]
        self.assertIn("slot = LoadSpritePalette(&palette);", part)
        self.assertIn("if (slot == 0xFF)", part)
        self.assertIn("PatchObjectPalette(graphicsInfo->paletteTag, slot);", part)
        self.assertIn("gSprites[spriteId].oam.paletteNum = slot;", part)
        self.assertIn("FreeSpritePaletteByTag(LAN_REMOTE_PALETTE_TAG);", part)
        self.assertNotIn("PatchObjectPalette(graphicsInfo->paletteTag, PALSLOT_PLAYER)", part)

    def test_sprite_is_discarded_if_dynamic_palette_fails(self):
        code = (ROOT / "src" / "link.c").read_text(encoding="utf-8")
        start = code.index("if (sLanRemoteInitialized &&\n            !LanVirtualObjectSetRemotePalette")
        self.assertIn("LanVirtualObjectDestroy(LAN_VIRTUAL_PLAYER_ID);", code[start:start+230])
        self.assertIn("sLanRemoteInitialized = FALSE;", code[start:start+250])

    def test_portable_header_guard(self):
        header = (ROOT / "include" / "event_object_movement.h").read_text(encoding="utf-8")
        self.assertIn("#ifdef PORTABLE\nbool32 LanVirtualObjectExists", header)
        self.assertIn("bool32 LanVirtualObjectSetRemotePalette(u8 virtualObjId, u8 graphicsId);", header)

if __name__ == "__main__":
    unittest.main()
