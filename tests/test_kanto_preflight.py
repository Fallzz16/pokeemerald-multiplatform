"""Read-only Kanto preflight regression tests (offline fixtures)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "kanto"))
from preflight import PreflightError, exterior_names, inspect  # noqa: E402


def put_json(root, rel, payload):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class PreflightTests(unittest.TestCase):
    def test_exterior_selection_and_sevii_exclusion(self):
        self.assertEqual(
            exterior_names(["PalletTown", "OneIsland", "Route1", "Route21_North",
                            "SevenIsland", "VermilionCity", "ViridianForest"]),
            ["PalletTown", "Route1", "Route21_North", "VermilionCity"]
        )
        with self.assertRaises(PreflightError):
            exterior_names(["Route1", "Route1"])

    def test_preflight_uses_source_bytes_without_mutating_target(self):
        with tempfile.TemporaryDirectory() as directory:
            fr, em = Path(directory) / "fr", Path(directory) / "em"
            names = ["PalletTown", "VermilionCity", "Route1"]
            layout = {
                "id": "LAYOUT_KANTO_FAKE", "width": 2, "height": 2,
                "primary_tileset": "gTileset_General",
                "secondary_tileset": "gTileset_PalletTown",
                "blockdata_filepath": "data/layouts/demo/map.bin",
                "border_filepath": "data/layouts/demo/border.bin",
            }
            put_json(fr, "data/maps/map_groups.json", {"gMapGroup_TownsAndRoutes": names})
            put_json(fr, "data/layouts/layouts.json", {"layouts": [layout]})
            for n in names:
                put_json(fr, f"data/maps/{n}/map.json", {
                    "name": n, "id": "MAP_" + n.upper(),
                    "layout": "LAYOUT_KANTO_FAKE",
                    "object_events": [], "warp_events": [], "connections": None,
                })
            put_json(em, "data/maps/map_groups.json", {
                "group_order": ["gMapGroup_Hoenn"], "gMapGroup_Hoenn": ["LittlerootTown"]
            })
            put_json(em, "data/layouts/layouts.json", {"layouts": []})
            dest = fr / "data/layouts/demo"
            dest.mkdir(parents=True)
            (dest / "map.bin").write_bytes(b"\0" * 8)
            (dest / "border.bin").write_bytes(b"\0" * 8)
            initial = sorted(str(p.relative_to(em)) for p in em.rglob("*"))
            report = inspect(fr, em, minimum=3, required=frozenset(names))
            self.assertEqual(sorted(str(p.relative_to(em)) for p in em.rglob("*")), initial)
            self.assertEqual(report["imported_map_count"], 0)
            self.assertEqual(report["exterior_count"], 3)
            self.assertFalse(report["playable"])
            self.assertTrue(all(not q["playable"] for q in report["maps"]))
            (dest / "map.bin").write_bytes(b"\0" * 2)
            with self.assertRaises(PreflightError):
                inspect(fr, em, minimum=3, required=frozenset(names))


if __name__ == "__main__":
    unittest.main()
