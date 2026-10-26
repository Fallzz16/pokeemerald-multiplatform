"""Source-data-only audit of species affected by Grand World grass-only settings."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "audit_grass_only_access.py"
spec = importlib.util.spec_from_file_location("wild_access", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def mon(name):
    return {"min_level": 5, "max_level": 5, "species": "SPECIES_" + name}


def field(name):
    return {"encounter_rate": 10, "mons": [mon(name)]}


class WildAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.src = Path(self.tmp.name) / "wild_encounters.json"
        self.maps = [
            {"map": "MAP_A", "land_mons": field("ODDISH"),
             "water_mons": field("MAGIKARP")},
            {"map": "MAP_B", "land_mons": field("MAGIKARP"),
             "fishing_mons": field("HORSEA")},
            {"map": "MAP_C", "rock_smash_mons": field("NOSEPASS"),
             "water_mons": field("HORSEA")},
        ]
        self.save()

    def save(self):
        self.src.write_text(json.dumps({"wild_encounter_groups": [
            {"label": "gWildMonHeaders", "for_maps": True, "encounters": self.maps},
            {"label": "gBattlePyramidWildMonHeaders", "for_maps": False,
             "encounters": [{"land_mons": field("LUGIA")}]}]}))

    def test_only_disabled_only_species_flagged_not_shared(self):
        before = self.src.read_bytes()
        result = module.inventory(self.src, min_maps=3)
        self.assertEqual(result["mapped_encounter_records"], 3)
        self.assertEqual(result["disabled_method_species_not_in_any_land_table_count"], 2)
        names = [row["species"] for row in result["species_for_review"]]
        self.assertEqual(names, ["SPECIES_HORSEA", "SPECIES_NOSEPASS"])
        self.assertEqual(result["species_count_by_original_method"]["land_mons"], 2)
        self.assertIn("water_mons",
                      result["species_for_review"][0]["disabled_encounter_methods"])
        self.assertIn("fishing_mons",
                      result["species_for_review"][0]["disabled_encounter_methods"])
        self.assertFalse(result["globally_unobtainable_species_proven"])
        self.assertFalse(result["map_grass_tiles_verified"])
        self.assertFalse(result["method_change_applied_by_this_script"])
        self.assertEqual(self.src.read_bytes(), before)

    def test_zero_rate_does_not_count_as_access(self):
        self.maps[1]["land_mons"]["encounter_rate"] = 0
        self.save()
        result = module.inventory(self.src, min_maps=3)
        names = [r["species"] for r in result["species_for_review"]]
        self.assertIn("SPECIES_MAGIKARP", names)

    def test_rejects_missing_mapped_group(self):
        self.src.write_text(json.dumps({"wild_encounter_groups": []}))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            module.inventory(self.src, min_maps=1)

    def test_rejects_cut_down_table(self):
        with self.assertRaisesRegex(ValueError, "incomplete World"):
            module.inventory(self.src)

    def test_rejects_corrupt_map_method(self):
        self.maps[0]["water_mons"]["mons"] = []
        self.save()
        with self.assertRaisesRegex(ValueError, "no slots"):
            module.inventory(self.src, min_maps=3)

    def test_rejects_invalid_species(self):
        self.maps[0]["land_mons"]["mons"][0]["species"] = "?"
        self.save()
        with self.assertRaisesRegex(ValueError, "malformed"):
            module.inventory(self.src, min_maps=3)

    def test_ignores_battle_facility_non_map_group(self):
        result = module.inventory(self.src, min_maps=3)
        self.assertNotIn("SPECIES_LUGIA",
                         [r["species"] for r in result["species_for_review"]])


if __name__ == "__main__":
    unittest.main()
