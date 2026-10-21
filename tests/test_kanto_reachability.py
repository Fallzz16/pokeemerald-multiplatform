"""Synthetic tests for Kanto map-graph audit."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"/"kanto"))
from reachability import inspect


class GraphTests(unittest.TestCase):
    def test_directional_reachability_and_bad_warp_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            groups=root/"data/maps/map_groups.json"
            groups.parent.mkdir(parents=True)
            groups.write_text(json.dumps({"gMapGroup_Kanto":["Kanto_VermilionCity","Kanto_Route11","Kanto_Isolated"]}))
            payloads={
                "Kanto_VermilionCity":{"id":"MAP_KANTO_VERMILIONCITY",
                    "connections":[{"map":"MAP_KANTO_ROUTE11"}],"warp_events":[]},
                "Kanto_Route11":{"id":"MAP_KANTO_ROUTE11",
                    "connections":[],"warp_events":[]},
                "Kanto_Isolated":{"id":"MAP_KANTO_ISOLATED",
                    "connections":[],"warp_events":[]},
            }
            for name,data in payloads.items():
                path=root/"data/maps"/name/"map.json"
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(data))
            r=inspect(root)
            self.assertEqual((r["total_maps"],r["reachable_count"]), (3,2))
            self.assertEqual(r["unreachable_maps"],["Kanto_Isolated"])
            self.assertFalse(r["gameplay_verified"])
            payloads["Kanto_Route11"]["warp_events"]=[{
                "dest_map":"MAP_KANTO_MISSING","dest_warp_id":"0"}]
            (root/"data/maps/Kanto_Route11/map.json").write_text(
                json.dumps(payloads["Kanto_Route11"])
            )
            with self.assertRaisesRegex(ValueError,"missing Kanto warp"):
                inspect(root)


if __name__=="__main__":
    unittest.main()
