"""GBA-only ARM linker audit: no Windows/SDL2 symbols are required."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

# CI checks out Grand World under grandworld/; import the exact sibling tool,
# independently of the repository's current working directory.
SCRIPT = Path(__file__).resolve().parents[1] / "audit_gba_arm_link.py"
spec = importlib.util.spec_from_file_location("grandworld_gba_arm_audit", SCRIPT)
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)

AuditError = audit_module.AuditError
ROM_SIZE = audit_module.ROM_SIZE
analyze = audit_module.analyze
inspect_elf_header = audit_module.inspect_elf_header
inspect_rom = audit_module.inspect_rom
parse_nm_posix = audit_module.parse_nm_posix

GOOD_DEFINED = ("Start T 08000000 00000004\n"
                "Init T 08000004 00000050\n"
                "AgbMain T 08000201 00000400\n"
                "SoftReset T 08030000\n")


class GbaArmLinkAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.elf = Path(self.tmp.name) / "pokemonworld.elf"
        self.rom = Path(self.tmp.name) / "pokemonworld.gba"
        header = bytearray(52)
        header[:7] = b"\x7fELF\x01\x01\x01"
        struct.pack_into("<HHI", header, 16, 2, 40, 1)
        struct.pack_into("<I", header, 24, 0x08000000)
        self.elf.write_bytes(header)
        with self.rom.open("wb") as out:
            out.seek(ROM_SIZE - 1)
            out.write(b"\x00")
        with self.rom.open("r+b") as out:
            out.seek(0xA0)
            buf = bytearray(0x1E)
            buf[:12] = b"POKEMON WRLD"
            buf[0x0C:0x10] = b"BPEE"
            buf[0x12] = 0x96
            buf[0x1D] = (-sum(buf[:0x1D]) - 0x19) & 0xFF
            out.write(buf)

    def tearDown(self):
        self.tmp.cleanup()

    def test_genuine_arm_link_with_correct_rom_header(self):
        report = analyze(self.elf, self.rom, GOOD_DEFINED, "")
        self.assertTrue(report["verified"])
        self.assertEqual(report["undefined_strong_symbol_count"], 0)
        self.assertIn("SoftReset", report["previously_native_unresolved_symbols_found_in_gba"])
        self.assertFalse(report["gba_boot_or_gameplay_verified_by_this_audit"])
        self.assertEqual(report["rom_bytes"], ROM_SIZE)

    def test_missing_real_arm_link_symbol_is_rejected(self):
        with self.assertRaisesRegex(AuditError, "unresolved STRONG ARM"):
            analyze(self.elf, self.rom, GOOD_DEFINED, "ForgottenFunction U\n")

    def test_weak_undefined_is_recorded_separately(self):
        report = analyze(self.elf, self.rom, GOOD_DEFINED, "OptionalHook w\n")
        self.assertEqual(report["optional_undefined_weak_symbols"], ["OptionalHook"])

    def test_missing_boot_symbol_is_not_accepted(self):
        with self.assertRaisesRegex(AuditError, "missing authentic GBA boot symbols"):
            analyze(self.elf, self.rom, "Start T 08000000\nInit T 08000004\n", "")

    def test_x86_or_relocatable_elf_is_rejected(self):
        blob = bytearray(self.elf.read_bytes())
        struct.pack_into("<H", blob, 18, 3)
        self.elf.write_bytes(blob)
        with self.assertRaisesRegex(AuditError, "expected executable ARM ELF"):
            inspect_elf_header(self.elf)
        struct.pack_into("<H", blob, 18, 40)
        struct.pack_into("<H", blob, 16, 1)
        self.elf.write_bytes(blob)
        with self.assertRaisesRegex(AuditError, "expected executable ARM ELF"):
            inspect_elf_header(self.elf)

    def test_rom_checksum_and_code_are_verified(self):
        with self.rom.open("r+b") as rom:
            rom.seek(0xBD)
            rom.write(b"\x00")
        with self.assertRaisesRegex(AuditError, "complement checksum"):
            inspect_rom(self.rom)

    def test_nm_output_rejects_garbage(self):
        with self.assertRaisesRegex(AuditError, "unexpected nm POSIX output"):
            parse_nm_posix("unexpected\n")

    def test_elf_start_address_must_match_entry(self):
        with self.assertRaisesRegex(AuditError, "does not match Start"):
            analyze(self.elf, self.rom,
                    GOOD_DEFINED.replace("Start T 08000000", "Start T 08000004"), "")


if __name__ == "__main__":
    unittest.main()
