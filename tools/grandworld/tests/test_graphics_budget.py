"""Focused tests for zero-gameplay-change graphics budget instrumentation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, BASE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


overlay = load("graphics_budget_overlay")
report = load("graphics_budget_report")


def line(stage, *, used=360, free=664, largest=600, runs=2,
         reserved=32, sprites=12, palettes=8, owe=2, follower=1,
         dup_slots=0, dup_pairs=0):
    return (
        f"  GRAPHICS_BUDGET stage={stage} used={used} free={free} "
        f"largest_free={largest} free_runs={runs} reserved={reserved} "
        f"sprites={sprites} palettes={palettes} owe={owe} follower={follower} "
        f"palette_duplicate_slots={dup_slots} palette_duplicate_pairs={dup_pairs}\n")


class BudgetReportTests(unittest.TestCase):
    def good_log(self):
        return (
            line("field-before-spawn", owe=0)
            + line("sample-10", owe=2)
            + line("sample-20", used=400, free=624, largest=440)
            + line("field-after-2400-frames", used=400, free=624, largest=440)
            + line("field-after-real-battle-flee", used=330, free=694,
                   largest=670, owe=0, follower=1)
        )

    def test_calculates_real_tile_and_fragmentation_metrics(self):
        data = report.analyze(self.good_log())
        self.assertEqual(data["peak_allocated_tiles"], 400)
        self.assertEqual(data["peak_allocated_obj_bytes"], 12800)
        self.assertEqual(data["minimum_free_tiles"], 624)
        self.assertEqual(data["smallest_largest_free_run"], 440)
        self.assertFalse(data["measured_fps"])
        self.assertEqual(data["rom_bytes_saved"], 0)
        self.assertFalse(data["ready_for_release"])

    def test_identical_colors_are_only_audit_candidates(self):
        data = report.analyze(self.good_log().replace(
            "palette_duplicate_slots=0 palette_duplicate_pairs=0",
            "palette_duplicate_slots=1 palette_duplicate_pairs=1"))
        self.assertEqual(data["peak_exact_color_duplicate_palette_slots"], 1)
        self.assertFalse(data["potential_palette_merging_safe"])

    def test_corrupt_palette_pair_count_fails(self):
        log = self.good_log().replace(
            "palette_duplicate_slots=0 palette_duplicate_pairs=0",
            "palette_duplicate_slots=1 palette_duplicate_pairs=1000")
        with self.assertRaisesRegex(ValueError, "duplicate pair"):
            report.analyze(log)

    def test_missing_required_snapshot_fails(self):
        with self.assertRaisesRegex(ValueError, "missing required snapshots"):
            report.analyze(self.good_log().replace("field-after-real-battle-flee",
                                                   "removed-stage"))

    def test_wrong_bitmap_size_fails(self):
        with self.assertRaisesRegex(ValueError, "bitmap size"):
            report.analyze(self.good_log().replace("used=360 free=664",
                                                   "used=360 free=665"))

    def test_duplicate_stage_fails(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            report.analyze(self.good_log() + line("sample-10"))

    def test_wild_sprite_must_be_sampled(self):
        with self.assertRaisesRegex(ValueError, "no live wild"):
            report.analyze(self.good_log().replace("owe=2", "owe=0"))

    def test_corrupt_palette_count_fails(self):
        with self.assertRaisesRegex(ValueError, "palette"):
            report.analyze(self.good_log().replace("palettes=8", "palettes=18"))


class GraphicsOverlayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "src").mkdir()
        (self.root / "test/overworld/lua").mkdir(parents=True)
        self.sprite = self.root / "src/sprite.c"
        self.generator = self.root / "test/overworld/GenLuaSymbols.py"
        self.lua = self.root / "test/overworld/lua/GrandWorldM9LandOWE.lua"
        self.sprite.write_text(overlay.SPRITE_ANCHOR + "\n", encoding="utf-8")
        self.generator.write_text(overlay.SYMBOL_ANCHOR, encoding="utf-8")
        self.lua.write_text(
            overlay.LUA_INSERT_BEFORE
            + "\n".join('  logRuntimeBudget("' + x + '")'
                        for x in overlay.LUA_CALL_STAGES) + "\n"
            + overlay.LUA_SAMPLE_ANCHOR, encoding="utf-8")

    def test_dry_run_is_read_only(self):
        paths = [self.sprite, self.generator, self.lua]
        originals = [p.read_bytes() for p in paths]
        result = overlay.instrument(self.root)
        self.assertFalse(result["gameplay_sources_changed"])
        self.assertEqual(originals, [p.read_bytes() for p in paths])

    def test_apply_exposes_bitmap_and_adds_samples(self):
        overlay.instrument(self.root, apply=True)
        self.assertIn(overlay.SPRITE_REPLACEMENT, self.sprite.read_text())
        self.assertIn("gReservedSpriteTileCount", self.generator.read_text())
        source = self.lua.read_text()
        self.assertIn("GRAPHICS_BUDGET stage=", source)
        for stage in overlay.LUA_CALL_STAGES:
            self.assertIn('logGraphicsBudget("' + stage + '")', source)
        self.assertIn('logGraphicsBudget("sample-" .. n)', source)

    def test_partial_apply_is_not_allowed(self):
        self.lua.write_text("broken test source", encoding="utf-8")
        originals = [p.read_bytes() for p in (self.sprite, self.generator, self.lua)]
        with self.assertRaisesRegex(ValueError, "FAIL CLOSED"):
            overlay.instrument(self.root, apply=True)
        self.assertEqual(originals,
                         [p.read_bytes() for p in (self.sprite, self.generator, self.lua)])

    def test_double_apply_fails_closed(self):
        overlay.instrument(self.root, apply=True)
        with self.assertRaisesRegex(ValueError, "FAIL CLOSED"):
            overlay.instrument(self.root, apply=True)


if __name__ == "__main__":
    unittest.main()
