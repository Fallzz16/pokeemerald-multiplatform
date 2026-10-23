"""Tests generated V0.19 data against the pinned FireRed revision.

Run after import_exteriors.py, not against a repository without generated maps.
No saves are opened or modified.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = (("Robin", "LASS"), ("Sally", "LASS"),
         ("Janice", "LASS"), ("Calvin", "YOUNGSTER"))


class TestRoute3V19(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def read(path):
            return (ROOT / path).read_text(encoding="utf-8")
        cls.report = json.loads(read("kanto-exteriors-import.json"))
        cls.source = json.loads(read("firered-source/data/maps/Route3/map.json"))
        cls.target = json.loads(read("data/maps/Kanto_Route3/map.json"))
        cls.opponents = read("include/constants/opponents.h")
        cls.flags = read("include/constants/flags.h")
        cls.battle = read("src/battle_setup.c")
        cls.trainers = read("src/data/trainers.h")
        cls.parties = read("src/data/trainer_parties.h")
        cls.original_parties = read("firered-source/src/data/trainer_parties.h")
        cls.scripts = read("data/maps/Kanto_Route3/scripts.inc")

    def test_original_actors_parties_and_scripts(self):
        rows = self.report["v19_route3_trainers"]
        self.assertEqual(self.report["v19_trainer_battles"], 4)
        self.assertEqual(self.report["trainer_battles_ported"], 22 + self.report.get("v20_trainer_battles", 0) + self.report.get("v21_nugget_bridge_rocket", {}).get("count", 0) + self.report.get("v22_moon_rocket", {}).get("count", 0))
        self.assertEqual(self.report["original_npcs_ported"], 22 + self.report.get("v20_trainer_battles", 0) + self.report.get("v21_nugget_bridge_rocket", {}).get("count", 0) + self.report.get("v22_moon_rocket", {}).get("count", 0))
        self.assertEqual([(r["name"], r["category"]) for r in rows], list(NAMES))
        for index, (name, klass) in enumerate(NAMES):
            row = rows[index]
            self.assertEqual(row["trainer_id"], 873 + index)
            expected = [o for o in self.source["object_events"]
                        if o["script"] == f"Route3_EventScript_{name}"]
            actual = [o for o in self.target["object_events"]
                      if o["script"] == row["event"]]
            self.assertEqual(len(expected), 1)
            self.assertEqual(len(actual), 1)
            for key in ("x", "y", "elevation", "graphics_id", "movement_type",
                        "movement_range_x", "movement_range_y", "trainer_type",
                        "trainer_sight_or_berry_tree_id"):
                self.assertEqual(expected[0][key], actual[0][key], (name, key))
            self.assertIn("trainerbattle_single " + row["symbol"], self.scripts)
            self.assertIn("[" + row["symbol"] + "]", self.trainers)
            prefix = "Lass" if klass == "LASS" else "Youngster"
            old = f"sParty_{prefix}{name}"
            new = f"sParty_KantoV19{prefix}{name}"
            pattern = r"static const struct TrainerMonNoItemDefaultMoves\s+{}\[\]\s*=\s*\{{([\s\S]*?)\n\}};"
            x = re.search(pattern.format(old), self.original_parties)
            y = re.search(pattern.format(new), self.parties)
            self.assertIsNotNone(x, old)
            self.assertIsNotNone(y, new)
            self.assertEqual(x.group(1), y.group(1))

    def test_reserved_victory_flags_are_unique(self):
        self.assertIn("#define TRAINERS_COUNT                      " + str(877 + self.report.get("v20_trainer_battles", 0) + self.report.get("v21_nugget_bridge_rocket", {}).get("count", 0) + self.report.get("v22_moon_rocket", {}).get("count", 0)), self.opponents)
        self.assertIn("#define MAX_TRAINERS_COUNT                  864", self.opponents)
        self.assertEqual(self.battle.count("TRAINER_FLAGS_START + trainerId"), 1)
        report = self.report
        used = [r["flag_value"] for k in ("visible_item_flags",
                "hidden_item_flags", "v13_new_item_flags") for r in report[k]]
        for r in report["v16_gym_leaders"]:
            used.extend((r["badge_flag_value"], r["tm_flag_value"]))
        for r in report["v17_remaining_gym_leaders"]:
            used.extend((r["trainer_flag_value"], r["badge_flag_value"],
                         r["tm_flag_value"]))
        used.extend(r["flag_value"] for r in report["v18_route_and_moon_trainers"])
        self.assertEqual(len(used), 185)
        for r in report["v19_route3_trainers"]:
            used.append(r["flag_value"])
            self.assertIn("case " + r["symbol"] + ":", self.battle)
            self.assertIn("return " + r["flag"] + ";", self.battle)
            self.assertIn("#define " + r["flag"], self.flags)
            self.assertIn(f"FLAG_UNUSED_0x{r['flag_value']:03X}", self.flags)
        self.assertEqual(len(used), 189)
        self.assertEqual(len(used), len(set(used)))
        positions = [(o["x"], o["y"]) for o in self.target["object_events"]]
        self.assertEqual(len(positions), len(set(positions)))


if __name__ == "__main__":
    unittest.main()
