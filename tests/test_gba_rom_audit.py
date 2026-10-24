"""Deterministic isolated tests for GBA header integrity checks."""
import hashlib
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "kanto"))
from gba_rom_audit import verify_rom, GbaRomValidationError


def synthetic_rom():
    b = bytearray(0xC0)
    b[0:4] = (0xEA00007F).to_bytes(4, "little")
    b[4:0xA0] = bytes(range(156))
    b[0xA0:0xAC] = b"POKEMON EMER"
    b[0xAC:0xB0] = b"BPEE"
    b[0xB0:0xB2] = b"01"
    b[0xB2] = 0x96
    b[0xBD] = (-(sum(b[0xA0:0xBD]) + 0x19)) & 0xFF
    return b


class GbaRomAuditTests(unittest.TestCase):
    def test_good_synthetic_header_not_gameplay(self):
        b = synthetic_rom()
        info = verify_rom(b, hashlib.sha1(b[4:0xA0]).hexdigest())
        self.assertEqual(info["game_code"], "BPEE")
        self.assertFalse(info["gameplay_verified"])
        self.assertFalse(info["boot_verified"])

    def test_header_checksum_corruption_rejected(self):
        b = synthetic_rom()
        b[0xBD] ^= 1
        with self.assertRaisesRegex(GbaRomValidationError, "complement"):
            verify_rom(b, hashlib.sha1(b[4:0xA0]).hexdigest())

    def test_logo_change_rejected(self):
        b = synthetic_rom()
        with self.assertRaisesRegex(GbaRomValidationError, "boot-logo"):
            verify_rom(b)

    def test_wrong_game_code_rejected(self):
        b = synthetic_rom()
        b[0xAC:0xB0] = b"ABCD"
        with self.assertRaisesRegex(GbaRomValidationError, "game code"):
            verify_rom(b, hashlib.sha1(b[4:0xA0]).hexdigest())

    def test_too_short_rom_rejected(self):
        with self.assertRaisesRegex(GbaRomValidationError, "length"):
            verify_rom(b"ABCD")


if __name__ == "__main__":
    unittest.main(verbosity=2)
