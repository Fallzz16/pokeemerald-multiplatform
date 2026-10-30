"""Pure-source tests for accurate GBA ROM linker footprint comparisons."""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "master_rom_compare.py"
spec = importlib.util.spec_from_file_location("master_rom_compare", SOURCE)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def sample(hash_char, rom=24564352, ewram=235300, iwram=28200):
    used = {"ROM": rom, "EWRAM": ewram, "IWRAM": iwram}
    return {
        "rom_sha256": hash_char * 64,
        "rom_bytes": 33554432,
        "memory_budget_passed": True,
        "linker_memory_bytes": used,
        "free_bytes": {k: tool.CAPACITY[k] - v for k, v in used.items()},
    }


class CompareBuilds(unittest.TestCase):
    def test_size_savings_are_actual_linker_usage(self):
        result = tool.compare(sample("a"), sample("b", rom=24000000))
        self.assertEqual(result["rom_bytes_saved"], 564352)
        self.assertTrue(result["smaller_rom_payload"])
        self.assertTrue(result["no_ewram_iwram_static_regression"])
        self.assertFalse(result["ready_for_master"])
        self.assertFalse(result["fps_measured_by_this_report"])

    def test_larger_payload_is_not_misrepresented_as_compression(self):
        result = tool.compare(sample("a"), sample("b", rom=25000000))
        self.assertLess(result["rom_bytes_saved"], 0)
        self.assertFalse(result["smaller_rom_payload"])

    def test_ram_regression_is_reported_even_when_rom_shrinks(self):
        result = tool.compare(sample("a"), sample("b", rom=24000000, ewram=235301))
        self.assertFalse(result["no_ewram_iwram_static_regression"])

    def test_same_rom_cannot_claim_independent_result(self):
        with self.assertRaisesRegex(ValueError, "same ROM hash"):
            tool.compare(sample("a"), sample("a"))

    def test_forged_remaining_bytes_rejected(self):
        corrupt = sample("b")
        corrupt["free_bytes"]["ROM"] += 1
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            tool.compare(sample("a"), corrupt)

    def test_oversized_rom_rejected(self):
        with self.assertRaisesRegex(ValueError, "safety reserve"):
            tool.compare(sample("a"), sample("b", rom=tool.CAPACITY["ROM"] - 100))

    def test_non_32mib_rom_rejected(self):
        candidate = sample("b")
        candidate["rom_bytes"] = 24 * 1024 * 1024
        with self.assertRaisesRegex(ValueError, "32 MiB"):
            tool.compare(sample("a"), candidate)

    def test_missing_memory_validation_rejected(self):
        candidate = sample("b")
        candidate["memory_budget_passed"] = False
        with self.assertRaisesRegex(ValueError, "not passed"):
            tool.compare(sample("a"), candidate)


if __name__ == "__main__":
    unittest.main()
