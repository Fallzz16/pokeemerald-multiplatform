"""Static non-regression checks for the isolated Kanto landing pier.

These checks do NOT replace compiling or physically testing the gameplay.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class KantoGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups = load_json("data/maps/map_groups.json")
        cls.kanto = load_json("data/maps/Kanto_Harbor/map.json")
        cls.slateport = load_json("data/maps/SlateportCity_Harbor/map.json")
        cls.events = (ROOT / "data/event_scripts.s").read_text(encoding="utf-8")
        cls.slate_scripts = (ROOT / "data/maps/SlateportCity_Harbor/scripts.inc").read_text(encoding="utf-8")
        cls.kanto_scripts = (ROOT / "data/maps/Kanto_Harbor/scripts.inc").read_text(encoding="utf-8")

    def test_new_group_appended_without_shifting_old_groups(self):
        self.assertEqual(self.groups["group_order"][-1], "gMapGroup_Kanto")
        self.assertEqual(self.groups["gMapGroup_Kanto"], ["Kanto_Harbor"])
        self.assertEqual(len(self.groups["group_order"]), 35)

    def test_kanto_map_has_valid_starter_metadata(self):
        self.assertEqual(self.kanto["id"], "MAP_KANTO_HARBOR")
        self.assertEqual(self.kanto["layout"], "LAYOUT_ISLAND_HARBOR")
        self.assertEqual(self.kanto["region_map_section"], "MAPSEC_NONE")
        self.assertEqual(self.kanto["warp_events"], [])
        self.assertTrue(any(obj["script"] == "Kanto_Harbor_EventScript_ReturnFerry"
                            for obj in self.kanto["object_events"]))

    def test_bidirectional_travel_has_refusal_paths(self):
        self.assertIn("warp MAP_KANTO_HARBOR, 8, 4", self.slate_scripts)
        self.assertIn("warp MAP_SLATEPORT_CITY_HARBOR, 13, 12", self.kanto_scripts)
        self.assertIn("goto_if_eq VAR_RESULT, NO,", self.slate_scripts)
        self.assertIn("goto_if_eq VAR_RESULT, NO,", self.kanto_scripts)

    def test_new_ferry_is_separate_from_existing_sailor(self):
        scripts = [o["script"] for o in self.slateport["object_events"]]
        self.assertIn("SlateportCity_Harbor_EventScript_KantoFerry", scripts)
        self.assertIn("SlateportCity_Harbor_EventScript_Sailor", scripts)
        self.assertIn("SlateportCity_Harbor_EventScript_FerryAttendant", scripts)
        self.assertIn('data/maps/Kanto_Harbor/scripts.inc', self.events)
        self.assertIn("MAP_KANTO_HARBOR", self.slate_scripts)
        self.assertIn("MAP_SLATEPORT_CITY_HARBOR", self.kanto_scripts)


if __name__ == "__main__":
    unittest.main()
