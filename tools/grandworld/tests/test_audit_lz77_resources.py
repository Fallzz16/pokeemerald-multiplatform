"""Unit tests using fabricated bytes only; no commercial ROM fixtures."""
import importlib.util
from pathlib import Path
import struct
import unittest

PATH = Path(__file__).resolve().parents[1] / "audit_lz77_resources.py"
spec = importlib.util.spec_from_file_location("audit_lz77", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture(with_pointer=True, valid=True):
    rom = bytearray(1 << 20)
    rom[0xAC:0xB0] = b"BPEE"
    rom[0xB2] = 0x96
    rom[0xBD] = (-0x19 - sum(rom[0xA0:0xBD])) & 0xFF
    # 8 literal bytes, then 4 references of 9 bytes each, distance 1.
    stream = bytes([0x10, 44, 0, 0, 0]) + b"ABCDEFGH" + bytes([0xF0, 0x60, 0, 0x60, 0, 0x60, 0, 0x60, 0])
    rom[0x100:0x100 + len(stream)] = stream
    if with_pointer:
        struct.pack_into("<I", rom, 0xC0, mod.ROM_BASE + 0x100)
    if not valid:
        rom[0x10E] = 0xFF  # first reference too far back
    return bytes(rom)


class RomResourcesTests(unittest.TestCase):
    def test_valid_pointer_referenced_stream(self):
        r = mod.audit(fixture())
        self.assertEqual(r["referenced_lz77_streams"], 1)
        self.assertEqual(r["referenced_stream_expanded_bytes"], 44)
        self.assertEqual(r["referencing_pointer_fields"], 1)
        self.assertFalse(r["fps_or_cycles_measured"])

    def test_mirrored_rom_pointer_and_deduplication(self):
        rom = bytearray(fixture())
        struct.pack_into("<I", rom, 0xC4, 0x0A000100)
        struct.pack_into("<I", rom, 0xC8, 0x0C000100)
        result = mod.audit(bytes(rom))
        self.assertEqual(result["referenced_lz77_streams"], 1)
        self.assertEqual(result["referencing_pointer_fields"], 3)

    def test_no_pointer_does_not_claim_resources(self):
        r = mod.audit(fixture(with_pointer=False))
        self.assertEqual(r["referenced_lz77_streams"], 0)
        self.assertIsNone(r["expansion_ratio"])

    def test_backreference_bounds(self):
        self.assertIsNone(mod.lz77_span(fixture(valid=False), 0x100))
        self.assertEqual(mod.audit(fixture(valid=False))["referenced_lz77_streams"], 0)

    def test_reject_header_corruption(self):
        wrong = bytearray(fixture())
        wrong[0xB2] = 0
        with self.assertRaisesRegex(ValueError, "fixed"):
            mod.audit(wrong)
        wrong = bytearray(fixture())
        wrong[0xBD] ^= 1
        with self.assertRaisesRegex(ValueError, "checksum"):
            mod.audit(wrong)

    def test_reject_invalid_streams(self):
        self.assertIsNone(mod.lz77_span(b"\x10\xff\xff\xff\x00", 0))
        self.assertIsNone(mod.lz77_span(b"\x10\x20\x00\x00\x80\x00\x00", 0))
        self.assertIsNone(mod.lz77_span(b"\x10\x20\x00\x00\x00", 0))


if __name__ == "__main__":
    unittest.main()
