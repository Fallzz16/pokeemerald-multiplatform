"""Kanto V0.21 Nugget Bridge Rocket: source, victory, reward and save guards."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


class NuggetBridgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(read("kanto-exteriors-import.json"))
        cls.event = cls.report["v21_nugget_bridge_rocket"]
        cls.map = json.loads(read("data/maps/Kanto_Route24/map.json"))
        cls.src_map = json.loads(read("firered-source/data/maps/Route24/map.json"))
        cls.script = read("data/maps/Kanto_Route24/scripts.inc")
        cls.flags = read("include/constants/flags.h")
        cls.opponents = read("include/constants/opponents.h")
        cls.battles = read("src/battle_setup.c")
        cls.trainers = read("src/data/trainers.h")
        cls.parties = read("src/data/trainer_parties.h")

    def test_original_actor_and_exact_firered_party(self):
        original = [o for o in self.src_map["object_events"]
                    if o.get("script") == "Route24_EventScript_Rocket"]
        dest = [o for o in self.map["object_events"]
                if o.get("script") == self.event["event"]]
        self.assertEqual(len(original), 1)
        self.assertEqual(len(dest), 1)
        for key in ("x", "y", "elevation", "movement_type",
                    "movement_range_x", "movement_range_y",
                    "trainer_sight_or_berry_tree_id"):
            self.assertEqual(original[0][key], dest[0][key], key)
        self.assertEqual(original[0]["graphics_id"], "OBJ_EVENT_GFX_MAN")
        self.assertEqual(dest[0]["graphics_id"], "OBJ_EVENT_GFX_MAN_1")
        self.assertTrue(self.event["field_sprite_temporary"])
        self.assertEqual(self.event["source_graphics_id"], original[0]["graphics_id"])
        self.assertEqual(self.event["field_graphics_id"], dest[0]["graphics_id"])
        self.assertEqual(dest[0]["flag"], "0")
        self.assertEqual(self.event["position"], [original[0]["x"], original[0]["y"]])
        self.assertEqual(self.event["source_trainer"], "TRAINER_TEAM_ROCKET_GRUNT_6")
        self.assertTrue(self.event["battle_sprite_temporary"])
        orig_party = read("firered-source/src/data/trainer_parties.h")
        regex = r"static const struct TrainerMonNoItemDefaultMoves\s+{}\[\]\s*=\s*\{{([\s\S]*?)\n\}};"
        before = re.search(regex.format(self.event["source_party"]), orig_party)
        after = re.search(regex.format("sParty_KantoV21BridgeRocket"), self.parties)
        self.assertIsNotNone(before)
        self.assertIsNotNone(after)
        self.assertEqual(before.group(1), after.group(1))

    def test_one_reward_only_and_full_bag_retry(self):
        script = self.script
        events = [
            f"trainerbattle_single TRAINER_KANTO_V21_BRIDGE_ROCKET",
            f"goto_if_set {self.event['reward_flag']}, Kanto_Route24_EventScript_V21RocketAfter",
            "giveitem ITEM_NUGGET",
            "goto_if_eq VAR_RESULT, FALSE, Kanto_Route24_EventScript_V21RocketFullBag",
            f"setflag {self.event['reward_flag']}",
        ]
        positions = [script.find(word) for word in events]
        self.assertTrue(all(pos >= 0 for pos in positions))
        self.assertEqual(positions, sorted(positions), "Nugget may be granted more than once")
        self.assertEqual(script.count("giveitem ITEM_NUGGET"), 1)
        self.assertEqual(script.count("setflag " + self.event["reward_flag"]), 1)
        self.assertEqual(self.event["reward_item"], "ITEM_NUGGET")

    def test_save_layout_and_id_allocator(self):
        self.assertEqual(self.report["trainer_battles_ported"], 45 + self.report.get("v22_moon_rocket", {}).get("count", 0) + self.report.get("v23_moon_fossils", {}).get("count", 0))
        self.assertEqual(self.report["original_npcs_ported"], 45 + self.report.get("v22_moon_rocket", {}).get("count", 0) + self.report.get("v23_moon_fossils", {}).get("count", 0))
        self.assertEqual(self.event["trainer_id"], 899)
        self.assertIn("#define TRAINERS_COUNT                      " + str(900 + self.report.get("v22_moon_rocket", {}).get("count", 0) + self.report.get("v23_moon_fossils", {}).get("count", 0)), self.opponents)
        self.assertIn("#define MAX_TRAINERS_COUNT                  864", self.opponents)
        self.assertIn("case TRAINER_KANTO_V21_BRIDGE_ROCKET:", self.battles)
        self.assertIn(f"return {self.event['trainer_flag']};", self.battles)
        self.assertEqual(self.battles.count("TRAINER_FLAGS_START + trainerId"), 1)
        self.assertEqual(self.event["trainer_flag_value"], 0x906)
        self.assertEqual(self.event["reward_flag_value"], 0x907)
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
        self.assertEqual(len(old), 211)
        combined = old + [self.event["trainer_flag_value"],
                          self.event["reward_flag_value"]]
        self.assertEqual(len(combined), len(set(combined)))
        self.assertEqual(len(combined), 213)
        for field in ("trainer_flag", "reward_flag"):
            self.assertIn("#define " + self.event[field], self.flags)
        self.assertIn("FLAG_UNUSED_0x906", self.flags)
        self.assertIn("FLAG_UNUSED_0x907", self.flags)
        self.assertLess(0x907, 0x920)
        self.assertIn("gSaveBlock1Ptr->flags[DAILY_FLAGS_START / 8]",
                      read("src/event_data.c"))


if __name__ == "__main__":
    unittest.main()
