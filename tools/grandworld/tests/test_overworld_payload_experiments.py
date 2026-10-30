"""Verify GBA image byte extraction and reversible LZ10 without touching assets."""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "overworld_payload_experiments.py"
spec = importlib.util.spec_from_file_location("overworld_payload_experiments", SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class LinkedOverworldPayloadTests(unittest.TestCase):
    @staticmethod
    def fixture():
        rom = bytearray(mod.ROM_SIZE)
        rom[0xAC:0xB0] = b"BPEE"
        # Distinct symbols A/B have exactly equal bytes: same size,
        # different linked addresses. An aliased symbol shares A address.
        a = bytes([1, 2, 3, 4] * 256)
        c = bytes((i % 251 for i in range(1024)))
        rom[0x1000:0x1400] = a
        rom[0x2000:0x2400] = a
        rom[0x3000:0x3400] = c
        nm = """08001000 00000400 R gObjectEventPic_TestA
08002000 00000400 R gObjectEventPic_TestB
08001000 00000400 R gObjectEventPic_TestA_Alias
08003000 00000400 R gObjectEventPic_TestC
02004000 00000200 B gObjectEventPic_NotRom
"""
        return rom, nm

    def test_exact_duplicate_scan_excludes_alias_double_count(self):
        rom, nm = self.fixture()
        result = mod.scan(nm, rom, pilot_limit=3)
        self.assertEqual(result["symbols_scanned"], 4)
        self.assertEqual(result["unique_linked_addresses"], 3)
        self.assertEqual(result["exact_duplicate_groups"], 1)
        self.assertEqual(result["exact_duplicate_potential_upper_bound_bytes"], 1024)
        self.assertEqual(result["lz10_pilot_symbol_count"], 3)
        self.assertTrue(result["lz10_pilot_roundtrip_verified"])
        self.assertEqual(result["actual_rom_bytes_saved"], 0)
        self.assertFalse(result["ready_for_merge"])

    def test_near_match_does_not_count_as_duplicate(self):
        rom, nm = self.fixture()
        rom[0x2001] ^= 1
        result = mod.scan(nm, rom, pilot_limit=0)
        self.assertEqual(result["exact_duplicate_groups"], 0)

    def test_rejects_wrong_cart_identity(self):
        rom, nm = self.fixture()
        rom[0xAC:0xB0] = b"????"
        with self.assertRaisesRegex(ValueError, "expected authentic"):
            mod.scan(nm, rom, pilot_limit=0)

    def test_rejects_out_of_bounds_symbols(self):
        rom, _ = self.fixture()
        with self.assertRaisesRegex(ValueError, "outside GBA"):
            mod.scan("09ffff00 00000300 R gObjectEventPic_Bad", rom, pilot_limit=0)

    def test_lz10_roundtrips_repetitive_and_uncompressible_data(self):
        for source in (b"", b"ABCD" * 128, bytes(range(256)) * 4,
                       bytes([0] * 2048), b"xyzxyzxyzxyzx"):
            compressed = mod.lz10_encode(source)
            self.assertEqual(mod.lz10_decode(compressed), source)

    def test_lz10_rejects_corrupt_stream(self):
        with self.assertRaisesRegex(ValueError, "header"):
            mod.lz10_decode(b"no")
        with self.assertRaisesRegex(ValueError, "truncated"):
            mod.lz10_decode(b"\x10\x10\x00\x00")


if __name__ == "__main__":
    unittest.main()
