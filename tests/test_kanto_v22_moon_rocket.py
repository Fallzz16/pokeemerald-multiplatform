"""QA for four V0.22 FireRed Rocket battles on Mt. Moon B2F.

Only read pinned FireRed/converted files after import_exteriors.py.
No synthetic or player save files are opened.
"""
import json
import re
import unittest
from pathlib import Path

from tools.kanto.v22_rocket_moon import ROSTER, FIRST_TRAINER_ID, FIRST_FLAG, FIELD_GRAPHIC

ROOT = Path(__file__).resolve().parents[1]


def read(p):
    return (ROOT / p).read_text(encoding="utf-8")


class V22MoonRocketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(read("kanto-exteriors-import.json"))
        cls.rows = cls.report["v22_moon_rocket"]["trainers"]
        cls.source = json.loads(read("firered-source/data/maps/MtMoon_B2F/map.json"))
        cls.dest = json.loads(read("data/maps/Kanto_MtMoon_B2F/map.json"))
        cls.original_parties = read("firered-source/src/data/trainer_parties.h")
        cls.parties = read("src/data/trainer_parties.h")
        cls.battle = read("src/battle_setup.c")
        cls.opponents = read("include/constants/opponents.h")
        cls.flags = read("include/constants/flags.h")
        cls.scripts = read("data/maps/Kanto_MtMoon_B2F/scripts.inc")
        cls.trainers = read("src/data/trainers.h")

    def test_four_real_fire_red_rocket_battles(self):
        self.assertEqual(len(self.rows), len(ROSTER) == 4 and 4)
        self.assertEqual(self.report["trainer_battles_ported"], 49)
        self.assertEqual(self.report["original_npcs_ported"], 49)
        self.assertEqual(self.report["v22_moon_rocket"]["count"], 4)
        for idx, (name, source_id, old_party) in enumerate(ROSTER):
            row = self.rows[idx]
            self.assertEqual((row["name"], row["source_trainer"],
                              row["source_party"]), (name, source_id, old_party))
            self.assertEqual(row["trainer_id"], FIRST_TRAINER_ID + idx)
            self.assertEqual(row["flag_value"], FIRST_FLAG + idx)
            original = [o for o in self.source["object_events"]
                        if o.get("script") == f"MtMoon_B2F_EventScript_{name}"]
            actual = [o for o in self.dest["object_events"]
                      if o.get("script") == row["script"]]
            self.assertEqual(len(original), 1)
            self.assertEqual(len(actual), 1)
            for key in ("x", "y", "elevation", "movement_type",
                        "movement_range_x", "movement_range_y",
                        "trainer_type", "trainer_sight_or_berry_tree_id"):
                self.assertEqual(actual[0][key], original[0][key], (name, key))
            self.assertEqual(row["position"], [original[0]["x"], original[0]["y"]])
            self.assertEqual(original[0]["graphics_id"], "OBJ_EVENT_GFX_ROCKET_M")
            self.assertEqual(actual[0]["graphics_id"], FIELD_GRAPHIC)
            self.assertTrue(row["art_temporary"])
            self.assertIn("trainerbattle_single " + row["symbol"], self.scripts)
            self.assertIn("[" + row["symbol"] + "]", self.trainers)
            self.assertIn("case " + row["symbol"] + ":", self.battle)
            self.assertIn("return " + row["flag"] + ";", self.battle)
            self.assertIn("#define " + row["flag"], self.flags)

    def test_source_party_payload_byte_for_byte(self):
        template = r"static const struct TrainerMonNoItemDefaultMoves\s+{}\[\]\s*=\s*\{{([\s\S]*?)\n\}};"
        for row in self.rows:
            old = re.search(template.format(re.escape(row["source_party"])),
                            self.original_parties)
            new = re.search(template.format(re.escape(row["party"])),
                            self.parties)
            self.assertIsNotNone(old, row["source_party"])
            self.assertIsNotNone(new, row["party"])
            self.assertEqual(old.group(1), new.group(1), row["name"])

    def test_stable_save_flags_and_no_npc_collision(self):
        self.assertIn("#define TRAINERS_COUNT                      904", self.opponents)
        self.assertIn("#define MAX_TRAINERS_COUNT                  864", self.opponents)
        self.assertIn("#define FLAGS_COUNT (DAILY_FLAGS_END + 1)", self.flags)
        self.assertEqual(self.battle.count("TRAINER_FLAGS_START + trainerId"), 1)
        old = [r["flag_value"] for key in
               ("visible_item_flags", "hidden_item_flags", "v13_new_item_flags")
               for r in self.report[key]]
        for r in self.report["v16_gym_leaders"]:
            old.extend((r["badge_flag_value"], r["tm_flag_value"]))
        for r in self.report["v17_remaining_gym_leaders"]:
            old.extend((r["trainer_flag_value"], r["badge_flag_value"],
                        r["tm_flag_value"]))
        old.extend(r["flag_value"] for r in self.report["v18_route_and_moon_trainers"])
        old.extend(r["flag_value"] for r in self.report["v19_route3_trainers"])
        old.extend(r["flag_value"] for r in self.report["v20_trainers"])
        rocket = self.report["v21_nugget_bridge_rocket"]
        old.extend((rocket["trainer_flag_value"], rocket["reward_flag_value"]))
        self.assertEqual(len(old), 213)
        combined = old + [r["flag_value"] for r in self.rows]
        self.assertEqual(len(combined), len(set(combined)))
        self.assertEqual(len(combined), 217)
        self.assertEqual(self.report["v22_moon_rocket"]
                         ["remaining_permanent_system_flags"], 20)
        self.assertTrue(all(value < 0x920 for value in combined[-4:]))
        positions = [(o["x"], o["y"]) for o in self.dest["object_events"]]
        self.assertEqual(len(positions), len(set(positions)))


if __name__ == "__main__":
    unittest.main()
