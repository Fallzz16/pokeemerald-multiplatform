"""Shadow profile comparison unit tests. Pure fabricated report metadata."""
import copy
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "compare_shadow_profiles.py"
spec = importlib.util.spec_from_file_location("shadow_compare", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixtures():
    p1 = {"resolved_shadow_mode": "lean"}
    p2 = {"resolved_shadow_mode": "full"}
    a = {"game_code": "BPEE", "memory_budget_passed": True,
         "rom_sha256": "a" * 64, "rom_bytes": 33554432,
         "linker_memory_bytes": {"ROM": 24590000, "EWRAM": 235000, "IWRAM": 28200}}
    b = copy.deepcopy(a)
    b["rom_sha256"] = "b" * 64
    b["linker_memory_bytes"]["ROM"] += 120
    lz_a = {"sha256": a["rom_sha256"], "rom_bytes": 33554432,
            "referenced_lz77_streams": 100, "referenced_stream_stored_bytes": 50000,
            "referenced_stream_expanded_bytes": 130000}
    lz_b = dict(lz_a, sha256=b["rom_sha256"])
    return p1, p2, a, b, lz_a, lz_b


class ShadowComparisonTests(unittest.TestCase):
    def test_good_pair(self):
        r = mod.evaluate(*fixtures())
        self.assertEqual(r["full_minus_lean_memory_bytes"]["ROM"], 120)
        self.assertFalse(r["fps_measured"])
        self.assertFalse(r["in_game_shadow_toggle_implemented"])

    def test_cross_rom_evidence_rejected(self):
        args = list(fixtures())
        args[-1]["sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "different ROMs"):
            mod.evaluate(*args)

    def test_profile_mismatch_rejected(self):
        args = list(fixtures())
        args[0]["resolved_shadow_mode"] = "full"
        with self.assertRaisesRegex(ValueError, "lean profile"):
            mod.evaluate(*args)

    def test_unapproved_memory_budget_rejected(self):
        args = list(fixtures())
        args[2]["memory_budget_passed"] = False
        with self.assertRaisesRegex(ValueError, "budget not verified"):
            mod.evaluate(*args)

    def test_malformed_memory_rejected(self):
        args = list(fixtures())
        args[3]["linker_memory_bytes"].pop("IWRAM")
        with self.assertRaisesRegex(ValueError, "memory fields"):
            mod.evaluate(*args)


if __name__ == "__main__":
    unittest.main()
