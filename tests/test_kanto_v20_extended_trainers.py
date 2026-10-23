"""Structural QA of Kanto V0.20 generated trainers and save-stable flags.

Run after import_exteriors.py, with the pinned FireRed checkout in place.
Do not run on real savefiles; this suite only reads source/generated code.
"""
import json
import re
import unittest
from pathlib import Path

from tools.kanto.v20_trainers import ROSTER, BASE_ID, FLAG_START, FLAG_STOP

ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class V20TrainerImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(read("kanto-exteriors-import.json"))
        cls.opponents = read("include/constants/opponents.h")
        cls.flags = read("include/constants/flags.h")
        cls.battles = read("src/battle_setup.c")
        cls.trainers = read("src/data/trainers.h")
        cls.parties = read("src/data/trainer_parties.h")
        cls.orig_trainers = read("firered-source/src/data/trainers.h")
        cls.orig_parties = read("firered-source/src/data/trainer_parties.h")

    def test_roster_and_exact_original_events(self):
        rows = self.report["v20_trainers"]
        self.assertEqual(len(ROSTER), 22)
        self.assertEqual(self.report["v20_trainer_battles"], 22)
        self.assertEqual(self.report["trainer_battles_ported"], 44 + self.report.get("v21_nugget_bridge_rocket", {}).get("count", 0) + self.report.get("v22_moon_rocket", {}).get("count", 0) + self.report.get("v23_moon_fossils", {}).get("count", 0))
        self.assertEqual(self.report["original_npcs_ported"], 44 + self.report.get("v21_nugget_bridge_rocket", {}).get("count", 0) + self.report.get("v22_moon_rocket", {}).get("count", 0) + self.report.get("v23_moon_fossils", {}).get("count", 0))
        self.assertEqual(
            [(r["map"].removeprefix("Kanto_"), r["name"], r["category"])
             for r in rows], list(ROSTER))
        for i, (area, name, category) in enumerate(ROSTER):
            row = rows[i]
            self.assertEqual(row["trainer_id"], BASE_ID + i)
            original = json.loads(read(f"firered-source/data/maps/{area}/map.json"))
            generated = json.loads(read(f"data/maps/Kanto_{area}/map.json"))
            source_events = [o for o in original["object_events"]
                             if o.get("script") == f"{area}_EventScript_{name}"]
            dest_events = [o for o in generated["object_events"]
                           if o.get("script") == row["event"]]
            self.assertEqual(len(source_events), 1, (area, name))
            self.assertEqual(len(dest_events), 1, (area, name))
            for key in ("x", "y", "graphics_id", "elevation", "movement_type",
                        "movement_range_x", "movement_range_y", "trainer_type",
                        "trainer_sight_or_berry_tree_id"):
                self.assertEqual(dest_events[0][key], source_events[0][key],
                                 (area, name, key))
            scripts = read(f"data/maps/Kanto_{area}/scripts.inc")
            self.assertIn(f"trainerbattle_single {row['symbol']}", scripts)
            self.assertIn(f"[{row['symbol']}]", self.trainers)
            self.assertIn(row["party"], self.parties)

    def test_teams_exactly_match_pinned_firered(self):
        for r in self.report["v20_trainers"]:
            source_record = re.search(
                r"\[" + re.escape(r["source_trainer"])
                + r"\]\s*=\s*\{([\s\S]*?)\n\s*\},",
                self.orig_trainers)
            target_record = re.search(
                r"\[" + re.escape(r["symbol"])
                + r"\]\s*=\s*\{([\s\S]*?)\n\s*\},",
                self.trainers)
            self.assertIsNotNone(source_record, r["name"])
            self.assertIsNotNone(target_record, r["name"])
            for key in ("trainerClass", "trainerPic", "encounterMusic_gender",
                        "trainerName", "doubleBattle", "aiFlags"):
                pat = r"\." + key + r"\s*=\s*([^,\n]+)"
                original_value = re.search(pat, source_record.group(1))
                generated_value = re.search(pat, target_record.group(1))
                self.assertIsNotNone(original_value, (r["name"], key))
                self.assertIsNotNone(generated_value, (r["name"], key))
                self.assertEqual(
                    original_value.group(1).strip(),
                    generated_value.group(1).strip(),
                    (r["name"], key))
            regex = (
                r"static const struct TrainerMonNoItemDefaultMoves\s+"
                + r"{}\[\]\s*=\s*\{{([\s\S]*?)\n\}};")
            source_party = re.search(
                regex.format(re.escape(r["source_party"])), self.orig_parties)
            dest_party = re.search(
                regex.format(re.escape(r["party"])), self.parties)
            self.assertIsNotNone(source_party, r["source_party"])
            self.assertIsNotNone(dest_party, r["party"])
            self.assertEqual(
                source_party.group(1), dest_party.group(1), r["name"])

    def test_persistent_flags_no_aliases_or_save_growth(self):
        self.assertIn("#define TRAINERS_COUNT                      " + str(899 + self.report.get("v21_nugget_bridge_rocket", {}).get("count", 0) + self.report.get("v22_moon_rocket", {}).get("count", 0) + self.report.get("v23_moon_fossils", {}).get("count", 0)), self.opponents)
        self.assertIn("#define MAX_TRAINERS_COUNT                  864", self.opponents)
        self.assertIn("#define FLAGS_COUNT (DAILY_FLAGS_END + 1)", self.flags)
        self.assertIn("gSaveBlock1Ptr->flags[DAILY_FLAGS_START / 8]",
                      read("src/event_data.c"))
        self.assertEqual(self.battles.count("TRAINER_FLAGS_START + trainerId"), 1)
        old = [r["flag_value"] for key in
               ("visible_item_flags", "hidden_item_flags", "v13_new_item_flags")
               for r in self.report[key]]
        for r in self.report["v16_gym_leaders"]:
            old.extend((r["badge_flag_value"], r["tm_flag_value"]))
        for r in self.report["v17_remaining_gym_leaders"]:
            old.extend((r["trainer_flag_value"], r["badge_flag_value"],
                        r["tm_flag_value"]))
        old.extend(r["flag_value"]
                   for r in self.report["v18_route_and_moon_trainers"])
        old.extend(r["flag_value"] for r in self.report["v19_route3_trainers"])
        self.assertEqual(len(old), 189)
        new = self.report["v20_trainers"]
        self.assertEqual([r["flag_value"] for r in new],
                         list(range(FLAG_START, FLAG_STOP)))
        self.assertEqual(self.report["v20_saved_flag_lane_remaining"],
                         0x920 - FLAG_STOP)
        combined = old + [r["flag_value"] for r in new]
        self.assertEqual(len(combined), 211)
        self.assertEqual(len(set(combined)), 211)
        for r in new:
            self.assertLess(r["flag_value"], 0x920)
            self.assertGreaterEqual(r["flag_value"], 0x8F0)
            self.assertIn(
                f"#define {r['flag']}", self.flags)
            self.assertIn(
                f"FLAG_UNUSED_0x{r['flag_value']:03X}", self.flags)
            self.assertRegex(
                self.battles, r"case " + re.escape(r["symbol"])
                + r":\s*return " + re.escape(r["flag"]) + r";")

    def test_no_duplicate_actor_positions(self):
        for area in set(r[0] for r in ROSTER):
            obj = json.loads(read(f"data/maps/Kanto_{area}/map.json"))
            positions = [(o["x"], o["y"]) for o in obj["object_events"]]
            self.assertEqual(
                len(positions), len(set(positions)), area)


if __name__ == "__main__":
    unittest.main()
