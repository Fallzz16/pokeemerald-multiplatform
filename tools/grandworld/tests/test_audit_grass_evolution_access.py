"""Fail-closed source analysis for conditional level evolution of grass-only risks."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

p=Path(__file__).resolve().parents[1]/"audit_grass_evolution_access.py"
spec=importlib.util.spec_from_file_location("evolution_access",p)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class GrassEvolutionAccessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        d=Path(self.temp.name)
        self.wild=d/"wild.json"
        self.access=d/"access.json"
        self.plan=d/"plan.json"
        self.species=d/"gen_1_families.h"
        self.entries=[{
            "map":"MAP_ROUTE1",
            "land_mons":{"encounter_rate":20,"mons":[{"species":"SPECIES_SLUGMA"}]},
        }]+[{"map":f"MAP_TEST_{n}"} for n in range(301)]
        self.access_names=["SPECIES_MAGCARGO","SPECIES_GYARADOS","SPECIES_LAPRAS","SPECIES_MAGIKARP"]
        self.family="""
[SPECIES_SLUGMA] = {
  .evolutions = EVOLUTION({EVO_LEVEL, 38, SPECIES_MAGCARGO}),
},
[SPECIES_MAGIKARP] = {
  .evolutions = EVOLUTION({EVO_LEVEL, 20, SPECIES_GYARADOS}),
},
[SPECIES_LAPRAS] = {
  .evolutions = EVOLUTION({EVO_ITEM, ITEM_WATER_STONE, SPECIES_CLAMPERL}),
},
"""
        self.save()

    def save(self):
        self.wild.write_text(json.dumps({"wild_encounter_groups":[{
            "label":"gWildMonHeaders","for_maps":True,"encounters":self.entries}]}))
        self.access.write_text(json.dumps({
            "species_for_review":[{"species":s} for s in self.access_names],
            "disabled_method_species_not_in_any_land_table_count":len(self.access_names),
        }))
        self.plan.write_text(json.dumps({
            "proposals":[{"species":"SPECIES_MAGIKARP"}],
            "proposed_count":1,"needs_manual_design_count":3,
        }))
        self.species.write_text(self.family)

    def run_audit(self):
        return module.audit(self.wild,self.access,self.plan,[self.species])

    def test_classifies_existing_candidate_and_unexplained_separately(self):
        out=self.run_audit()
        self.assertEqual(out["at_risk_species"],4)
        self.assertEqual(out["candidate_land_species"],1)
        self.assertEqual(out["already_in_land_level_evolution"][0]["species"],"SPECIES_MAGCARGO")
        self.assertEqual(out["conditional_on_candidate_level_evolution"][0]["species"],"SPECIES_GYARADOS")
        self.assertEqual(out["not_explained_by_direct_level_evolution"][0]["species"],"SPECIES_LAPRAS")
        self.assertFalse(out["release_approved"])
        self.assertFalse(out["compiled_evolution_flags_verified"])
        self.assertFalse(out["wild_capture_verified_by_this_tool"])

    def test_never_confuses_item_evolution_with_level(self):
        edges,_=module.extract_level_edges([self.species])
        self.assertNotIn("SPECIES_CLAMPERL",edges)

    def test_invalid_candidate_set_fails_closed(self):
        self.plan.write_text(json.dumps({
            "proposals":[{"species":"SPECIES_NOT_IN_RISK"}],
            "proposed_count":1,"needs_manual_design_count":3,
        }))
        with self.assertRaisesRegex(ValueError,"unreconciled"):
            self.run_audit()

    def test_candidate_already_in_land_fails_closed(self):
        self.entries[0]["land_mons"]["mons"].append({"species":"SPECIES_MAGIKARP"})
        self.save()
        with self.assertRaisesRegex(ValueError,"unreconciled"):
            self.run_audit()

    def test_empty_species_family_fails_closed(self):
        self.species.write_text("/* empty */")
        with self.assertRaisesRegex(ValueError,"no species definitions"):
            self.run_audit()


if __name__=="__main__":
    unittest.main()
