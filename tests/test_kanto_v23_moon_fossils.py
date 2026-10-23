"""Post-import V0.23 QA: FireRed Miguel and irreversible one-of-two fossils.

Operates exclusively on generated JSON/code and pinned FireRed inputs.
Does not read, modify or synthesize player .sav files.
"""
import json
import re
import unittest
from pathlib import Path

from tools.kanto.v23_moon_fossils import (
    FLAG_NAMES, MIGUEL_ID, MIGUEL_FLAG, DOME_CHOSEN_FLAG,
    HELIX_CHOSEN_FLAG, FOSSILS_TAKEN_FLAG,
)

ROOT = Path(__file__).resolve().parents[1]


def read(p):
    return (ROOT / p).read_text(encoding="utf-8")


class V23MtMoonFossilTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(read("kanto-exteriors-import.json"))
        cls.result = cls.report["v23_moon_fossils"]
        cls.original = json.loads(read("firered-source/data/maps/MtMoon_B2F/map.json"))
        cls.dest = json.loads(read("data/maps/Kanto_MtMoon_B2F/map.json"))
        cls.script = read("data/maps/Kanto_MtMoon_B2F/scripts.inc")
        cls.flags = read("include/constants/flags.h")
        cls.opponents = read("include/constants/opponents.h")
        cls.battle = read("src/battle_setup.c")

    def test_original_miguel_and_both_fossil_positions(self):
        expected = (
            ("Miguel", "MtMoon_B2F_EventScript_Miguel", "OBJ_EVENT_GFX_SCIENTIST_1"),
            ("Dome", "MtMoon_B2F_EventScript_DomeFossil", "OBJ_EVENT_GFX_FOSSIL"),
            ("Helix", "MtMoon_B2F_EventScript_HelixFossil", "OBJ_EVENT_GFX_FOSSIL"),
        )
        self.assertEqual([r["name"] for r in self.result["actors"]],
                         [r[0] for r in expected])
        for row, (name, source_script, graphic) in zip(self.result["actors"], expected):
            original = [o for o in self.original["object_events"]
                        if o.get("script") == source_script]
            actual = [o for o in self.dest["object_events"]
                      if o.get("script") == row["event"]]
            self.assertEqual(len(original), 1, name)
            self.assertEqual(len(actual), 1, name)
            for key in ("x", "y", "elevation", "movement_type",
                        "movement_range_x", "movement_range_y",
                        "trainer_type", "trainer_sight_or_berry_tree_id"):
                self.assertEqual(actual[0][key], original[0][key], (name, key))
            self.assertEqual(row["position"], [original[0]["x"], original[0]["y"]])
            self.assertEqual(actual[0]["graphics_id"], graphic)
            self.assertEqual(actual[0]["flag"],
                             "0" if name == "Miguel" else "FLAG_KANTO_V23_FOSSILS_TAKEN")
            self.assertIn(row["event"] + "::", self.script)
        positions = [(o["x"], o["y"]) for o in self.dest["object_events"]]
        self.assertEqual(len(positions), len(set(positions)))

    def test_original_party_and_trainer_flag(self):
        party_original = read("firered-source/src/data/trainer_parties.h")
        party_generated = read("src/data/trainer_parties.h")
        regex = r"static const struct TrainerMonNoItemDefaultMoves\s+{}\[\]\s*=\s*\{{([\s\S]*?)\n\}};"
        old = re.search(regex.format("sParty_SuperNerdMiguel"), party_original)
        new = re.search(regex.format(self.result["party"]), party_generated)
        self.assertIsNotNone(old)
        self.assertIsNotNone(new)
        self.assertEqual(old.group(1), new.group(1))
        self.assertEqual(self.result["trainer_id"], MIGUEL_ID)
        self.assertEqual(self.result["source_trainer"], "TRAINER_SUPER_NERD_MIGUEL")
        self.assertIn("case TRAINER_KANTO_V23_MIGUEL:", self.battle)
        self.assertIn("return FLAG_KANTO_V23_MIGUEL_DEFEATED;", self.battle)
        self.assertIn("trainerbattle_single TRAINER_KANTO_V23_MIGUEL", self.script)

    def test_single_fossil_choice_and_full_bag_retry(self):
        self.assertTrue(self.result["fossil_choice_is_exclusive"])
        self.assertEqual(self.script.count("giveitem ITEM_DOME_FOSSIL"), 1)
        self.assertEqual(self.script.count("giveitem ITEM_HELIX_FOSSIL"), 1)
        for choice in ("Dome", "Helix"):
            start = self.script.index("Kanto_MtMoon_B2F_EventScript_V23" + choice + "::")
            end = self.script.index("\nKanto_MtMoon_B2F_EventScript_V23", start + 1)
            script = self.script[start:end]
            self.assertIn("goto_if_unset FLAG_KANTO_V23_MIGUEL_DEFEATED", script)
            self.assertIn("goto_if_set FLAG_KANTO_V23_FOSSILS_TAKEN", script)
            self.assertIn("goto_if_eq VAR_RESULT, NO", script)
            self.assertIn("goto_if_eq VAR_RESULT, FALSE", script)
            self.assertIn("setflag FLAG_KANTO_V23_FOSSILS_TAKEN", script)
            self.assertIn("removeobject VAR_LAST_TALKED", script)
            grant_index = script.index("giveitem ITEM_" + choice.upper() + "_FOSSIL")
            checked_index = script.index("goto_if_eq VAR_RESULT, FALSE")
            saved_index = script.index("setflag FLAG_KANTO_V23_FOSSILS_TAKEN")
            self.assertLess(grant_index, checked_index)
            self.assertLess(checked_index, saved_index)
            self.assertIn("setflag FLAG_KANTO_V23_" + choice.upper() + "_CHOSEN", script)
        # Both actors share one hide flag, so return/reload cannot show either
        # once one choice has been successfully committed.
        self.assertEqual(
            [r["flag"] for r in self.result["actors"] if r["name"] != "Miguel"],
            ["FLAG_KANTO_V23_FOSSILS_TAKEN"] * 2)

    def test_stable_save_flags_and_map_registry(self):
        self.assertEqual(self.report["trainer_battles_ported"], 50)
        self.assertEqual(self.report["original_npcs_ported"], 50)
        self.assertIn("#define TRAINERS_COUNT                      905", self.opponents)
        self.assertIn("#define MAX_TRAINERS_COUNT                  864", self.opponents)
        self.assertEqual(self.battle.count("TRAINER_FLAGS_START + trainerId"), 1)
        self.assertEqual([(r["name"], r["flag_value"]) for r in self.result["flags"]],
                         list(FLAG_NAMES))
        self.assertEqual((MIGUEL_FLAG, FOSSILS_TAKEN_FLAG,
                          DOME_CHOSEN_FLAG, HELIX_CHOSEN_FLAG),
                         (0x90C, 0x90D, 0x90E, 0x90F))
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
        v21 = self.report["v21_nugget_bridge_rocket"]
        old.extend((v21["trainer_flag_value"], v21["reward_flag_value"]))
        old.extend(r["flag_value"] for r in self.report["v22_moon_rocket"]["trainers"])
        self.assertEqual(len(old), 217)
        combined = old + [r["flag_value"] for r in self.result["flags"]]
        self.assertEqual(len(combined), 221)
        self.assertEqual(len(set(combined)), 221)
        self.assertEqual(self.result["remaining_permanent_system_flags"], 16)
        for name, value in FLAG_NAMES:
            self.assertIn("#define " + name, self.flags)
            self.assertIn(f"FLAG_UNUSED_0x{value:03X}", self.flags)


if __name__ == "__main__":
    unittest.main()
