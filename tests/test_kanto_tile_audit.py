"""Pure unit tests for the conservative V0.24 tile-accessibility QA tool."""
import json
import struct
import tempfile
import unittest
from pathlib import Path

from tools.kanto.tile_audit import (
    audit_layout, collision_grid, connected_components,
    adjacent_components, inspect,
)


def blockdata(values):
    return b"".join(struct.pack("<H", value) for value in values)


class TileAuditTests(unittest.TestCase):
    def setUp(self):
        # Two nominally passable columns, separated by a blocked strip.
        self.tiles = blockdata((0, 0x0C00, 0, 0, 0x0C00, 0))
        self.layout = {
            "id": "LAYOUT_KANTO_QA",
            "width": 3, "height": 2,
            "blockdata_filepath": "data/layouts/QA/map.bin",
        }
        self.map = {
            "id": "MAP_KANTO_QA", "name": "Kanto_QA",
            "layout": "LAYOUT_KANTO_QA",
            "warp_events": [
                {"x": 0, "y": 0}, {"x": 2, "y": 1},
            ],
            "object_events": [
                {"x": 1, "y": 0, "script": "QA_Sign"},
            ],
        }

    def test_collision_mask_is_conservative(self):
        data = collision_grid(self.tiles, 3, 2)
        self.assertEqual(data, [True, False, True, True, False, True])
        self.assertEqual(sum(data), 4)
        with self.assertRaises(ValueError):
            collision_grid(self.tiles[:-1], 3, 2)
        with self.assertRaises(ValueError):
            collision_grid(b"", 0, 2)

    def test_components_distinguish_separated_regions(self):
        open_tiles = collision_grid(self.tiles, 3, 2)
        labels, sizes = connected_components(open_tiles, 3, 2)
        self.assertEqual(sizes, [2, 2])
        self.assertEqual(labels[0], labels[3])
        self.assertEqual(labels[2], labels[5])
        self.assertNotEqual(labels[0], labels[2])
        self.assertEqual(labels[1], -1)
        self.assertEqual(adjacent_components(1, 0, 3, 2, labels), {0, 1})
        self.assertEqual(adjacent_components(-1, 0, 3, 2, labels), set())

    def test_map_reports_disconnected_warps_without_claiming_gameplay(self):
        row = audit_layout("Kanto_QA", self.map, self.layout, self.tiles)
        self.assertEqual(row["nominally_walkable_tiles"], 4)
        self.assertEqual(row["nominally_blocked_tiles"], 2)
        self.assertEqual(row["walkable_components"], 2)
        self.assertEqual(row["disconnected_warp_pairs"], [[0, 1]])
        self.assertEqual(row["npc_count"], 1)
        self.assertTrue(row["warnings"])

    def test_out_of_bounds_is_a_diagnostic_not_a_fake_warp(self):
        m = dict(self.map)
        m["warp_events"] = [{"x": 99, "y": 0}]
        row = audit_layout("Kanto_QA", m, self.layout, self.tiles)
        self.assertEqual(row["out_of_bounds"][0]["index"], 0)
        self.assertEqual(row["out_of_bounds"][0]["type"], "warp")
        self.assertTrue(row["warnings"])

    def test_on_disk_fixture_is_read_only_and_explicitly_not_runtime_qa(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "data/maps/Kanto_QA").mkdir(parents=True)
            (root / "data/layouts/QA").mkdir(parents=True)
            (root / "data/layouts/QA/map.bin").write_bytes(self.tiles)
            (root / "data/maps/map_groups.json").write_text(
                json.dumps({"group_order": ["gMapGroup_Kanto"],
                            "gMapGroup_Kanto": ["Kanto_QA"]}),
                encoding="utf-8")
            (root / "data/layouts/layouts.json").write_text(
                json.dumps({"layouts": [self.layout]}), encoding="utf-8")
            (root / "data/maps/Kanto_QA/map.json").write_text(
                json.dumps(self.map), encoding="utf-8")
            report = inspect(root)
            self.assertEqual(report["maps_audited"], 1)
            self.assertEqual(report["maps_with_disconnected_warp_pairs"], 1)
            self.assertEqual(report["maps_with_warnings"], 1)
            self.assertFalse(report["gameplay_verified"])
            self.assertFalse(report["save_reload_verified"])
            self.assertFalse(report["elevation_verified"])
            self.assertFalse(report["supports_surf_or_puzzles"])


if __name__ == "__main__":
    unittest.main()
