"""M8: exercise GBA LZ77 inventory using synthetic, redistributable bytes."""
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

FILE = Path(__file__).resolve().parents[1] / "audit_lz77_resources.py"
spec = importlib.util.spec_from_file_location("gba_lz77_audit", FILE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(game_code=b"BPEE"):
    rom = bytearray(1 << 20)
    rom[0xAC:0xB0] = game_code
    rom[0xB2] = 0x96
    rom[0xBD] = (-sum(rom[0xA0:0xBD]) - 0x19) & 0xFF
    # 8 literals + 3 valid 8-byte backwards copies = 32 output bytes.
    stream = b"\x10\x20\x00\x00\x00ABCDEFGH\xe0\x50\x07\x50\x07\x50\x07"
    assert len(stream) == 20
    rom[0x100:0x100 + len(stream)] = stream
    # Physical ROM base plus the two hardware mirror windows.
    for ofs, addr in ((0xC0, 0x08000100), (0xC4, 0x0A000100),
                      (0xC8, 0x0C000100)):
        struct.pack_into("<I", rom, ofs, addr)
    return rom


class Lz77AuditTests(unittest.TestCase):
    def test_valid_stream_mirrors_and_deduplication(self):
        report = module.audit(fixture())
        self.assertEqual(report["game_code"], "BPEE")
        self.assertEqual(report["referenced_lz77_streams"], 1)
        self.assertEqual(report["referencing_pointer_fields"], 3)
        self.assertEqual(report["referenced_stream_stored_bytes"], 20)
        self.assertEqual(report["referenced_stream_expanded_bytes"], 32)
        self.assertEqual(report["expansion_ratio"], 1.6)
        self.assertFalse(report["fps_or_cycles_measured"])

    def test_invalid_length_truncated_stream_and_bad_backref(self):
        self.assertIsNone(module.lz77_span(fixture(), (1 << 20) - 1))
        self.assertIsNone(module.lz77_span(b"\x10\x20\x00\x00\x80\x00\x00", 0))
        self.assertIsNone(module.lz77_span(b"\x10\x01\x00\x80", 0))
        self.assertIsNone(module.lz77_span(b"\x10\x01\x00\x00\x00", 0))

    def test_bad_header_and_size_rejected(self):
        rom = fixture()
        rom[0xB2] = 0
        with self.assertRaisesRegex(ValueError, "fixed header"):
            module.audit(rom)
        rom = fixture()
        rom[0xBD] ^= 1
        with self.assertRaisesRegex(ValueError, "checksum"):
            module.audit(rom)
        with self.assertRaisesRegex(ValueError, "complete"):
            module.audit(rom[:-1])

    def test_incompatible_comparison_fails_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, out = [Path(tmp) / name for name in ("a.gba", "b.gba", "out.json")]
            a.write_bytes(fixture())
            b.write_bytes(fixture(b"ABCD"))
            cmd = [sys.executable, str(FILE), str(a), "--compare", str(b),
                   "--output", str(out)]
            done = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(done.returncode, 0)
            self.assertIn("different GBA game codes", done.stderr)
            self.assertFalse(out.exists())
            self.assertEqual(a.read_bytes(), fixture())

    def test_cli_identical_rom_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b, out = [Path(tmp) / name for name in ("a.gba", "b.gba", "out.json")]
            a.write_bytes(fixture())
            b.write_bytes(fixture())
            cmd = [sys.executable, str(FILE), str(a), "--compare", str(b),
                   "--output", str(out)]
            done = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            report = json.loads(out.read_text())
            self.assertEqual(report["comparison"]["second_minus_first"]["referenced_lz77_streams"], 0)
            self.assertTrue(report["comparison"]["not_an_fps_measurement"])


if __name__ == "__main__":
    unittest.main()
