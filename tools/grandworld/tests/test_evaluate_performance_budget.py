"""Strict memory budget tests with synthetic ROM bytes; never use game assets."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "evaluate_performance_budget.py"
spec = importlib.util.spec_from_file_location("m8_budget_eval", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fake_rom():
    rom = bytearray(32 * 1024 * 1024)
    rom[0xAC:0xB0] = b"BPEE"
    rom[0xB2] = 0x96
    rom[0xBD] = (-0x19 - sum(rom[0xA0:0xBD])) & 0xFF
    return bytes(rom)


def fake_log(rom=24595356, ewram=235264, iwram=28200):
    return (f"ROM: {rom} B\n"
            f"EWRAM: {ewram} B\n"
            f"IWRAM: {iwram} B\n")


class BudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = fake_rom()

    def test_correct_memories_and_hash(self):
        r = mod.report(self.rom, fake_log())
        self.assertTrue(r["memory_budget_passed"])
        self.assertEqual(r["free_bytes"]["EWRAM"], 262144 - 235264)
        self.assertFalse(r["fps_measured"])
        self.assertFalse(r["gameplay_homologated"])
        self.assertEqual(len(r["rom_sha256"]), 64)

    def test_invalid_last_trio_rejected(self):
        for value in ("", "ROM: 1 B\nIWRAM: 2 B\n",
                      "ROM: 1 B\nROM: 2 B\nIWRAM: 3 B\n"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "linker"):
                    mod.report(self.rom, value)

    def test_real_arm_linker_rows_include_other_columns(self):
        log = ("            EWRAM:      235264 B       256 KB     89.75%\n"
               "            IWRAM:       28200 B        32 KB     86.06%\n"
               "              ROM:    24595356 B        32 MB     73.30%\n")
        result = mod.report(self.rom, log)
        self.assertEqual(result["linker_memory_bytes"]["ROM"], 24595356)

    def test_memory_out_of_range(self):
        for values in ({'ewram': 262145}, {'iwram': 0}, {'rom': 33554433}):
            with self.subTest(values=values):
                with self.assertRaisesRegex(ValueError, "overflow"):
                    mod.report(self.rom, fake_log(**values))

    def test_minimum_ram_headroom_failure(self):
        with self.assertRaisesRegex(ValueError, "IWRAM headroom"):
            mod.report(self.rom, fake_log(iwram=31800))

    def test_bad_header_or_rom_size(self):
        for offset, new in [(0xB2, 0), (0xBD, 1), (0xAC, ord('X'))]:
            mutated = bytearray(self.rom)
            mutated[offset] = new
            with self.subTest(offset=offset):
                with self.assertRaises(ValueError):
                    mod.report(bytes(mutated), fake_log())
        with self.assertRaisesRegex(ValueError, "32 MiB"):
            mod.report(self.rom[:-1], fake_log())

    def test_no_negative_reserve(self):
        with self.assertRaisesRegex(ValueError, "negative"):
            mod.report(self.rom, fake_log(), {"ROM": -1, "EWRAM": 0, "IWRAM": 0})

    def test_realistic_last_complete_report(self):
        log = "ROM: 222222 B\nEWRAM: 50000 B\nIWRAM: 3000 B\n" + fake_log()
        self.assertEqual(mod.report(self.rom, log)["linker_memory_bytes"]["IWRAM"], 28200)


if __name__ == "__main__":
    unittest.main()
