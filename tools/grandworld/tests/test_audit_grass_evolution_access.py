"""Fail-closed tests for source-declared, NON-certified GBA evolution paths."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"audit_grass_evolution_access.py"
spec=importlib.util.spec_from_file_location("evoaccess",SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class EvolutionSourceAudit(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.orig=self.root/"orig.json"
        self.candidate=self.root/"candidate.json"
        self.data_dir=self.root/"species"
        self.data_dir.mkdir()
        for p in mod.METADATA_FILES:
            f=self.data_dir/p
            f.parent.mkdir(exist_ok=True,parents=True)
            f.write_text("")
        source="""
    [SPECIES_MAGIKARP] =
    {
        .speciesName = _("Magikarp"),
        .evolutions = EVOLUTION({EVO_LEVEL, 20, SPECIES_GYARADOS}),
    },
    [SPECIES_GYARADOS] =
    {
        .speciesName = _("Gyarados"),
        .evolutions = EVOLUTION({EVO_ITEM, ITEM_TEST, SPECIES_GYARADOS_MEGA}),
    },
    [SPECIES_CARVANHA] =
    {
        .evolutions = EVOLUTION({EVO_LEVEL, 30, SPECIES_SHARPEDO}),
    },
    [SPECIES_CLAMPERL] =
    {
        .categoryName = _("Shell"),
        .teachableLearnset = SPECIES_SHARPEDO,
    },
    """
        (self.data_dir/mod.METADATA_FILES[1]).write_text(source)
        self.put_land(self.orig, ["SPECIES_RATTATA","SPECIES_CARVANHA"])
        self.put_land(self.candidate, ["SPECIES_RATTATA","SPECIES_CARVANHA","SPECIES_MAGIKARP"])

    def put_land(self,path,land):
        maps=[{"map":f"MAP_ROUTE{i}"} for i in range(303)]
        maps[0]["land_mons"]={"encounter_rate":20,
                              "mons":[{"species":s} for s in land]}
        maps[1]["water_mons"]={"encounter_rate":10,
                              "mons":[{"species":s} for s in (
                                  "SPECIES_MAGIKARP","SPECIES_GYARADOS","SPECIES_SHARPEDO",
                                  "SPECIES_CLAMPERL")]}
        path.write_text(json.dumps({"wild_encounter_groups":[
            {"label":"gWildMonHeaders","for_maps":True,"encounters":maps}]}))

    def test_explicit_level_evolutions_only(self):
        result=mod.edges_from_text((self.data_dir/mod.METADATA_FILES[1]).read_text())
        self.assertIn(("SPECIES_MAGIKARP","SPECIES_GYARADOS","EVO_LEVEL"),result)
        self.assertIn(("SPECIES_CARVANHA","SPECIES_SHARPEDO","EVO_LEVEL"),result)
        self.assertFalse(any(a=="SPECIES_CLAMPERL" for a,_,_ in result))

    def test_original_vs_experiment_dependent(self):
        d=mod.inspect(self.orig,self.candidate,self.data_dir)
        rows={r["species"]:r for r in d["species"]}
        self.assertEqual(d["original_species_at_risk"],4)
        self.assertEqual(d["direct_new_land_species"],1)
        self.assertEqual(rows["SPECIES_MAGIKARP"]["status"],"experimental_direct_land_slot")
        self.assertEqual(rows["SPECIES_GYARADOS"]["status"],"source_evolution_dependent_on_experiment")
        self.assertEqual(rows["SPECIES_CLAMPERL"]["status"],"no_identified_land_or_evolution_path")
        self.assertFalse(d["evolutions_usable_in_playthrough_confirmed"])
        self.assertFalse(d["release_approved"])

    def test_existing_land_evolution_is_not_claimed_globally_catchable(self):
        d=mod.inspect(self.orig,self.candidate,self.data_dir)
        sharpedo=next(x for x in d["species"] if x["species"]=="SPECIES_SHARPEDO")
        self.assertEqual(sharpedo["status"],"source_evolution_from_original_land")
        self.assertEqual(sharpedo["original_land_evolution_chain"][0]["method"],"EVO_LEVEL")
        self.assertFalse(sharpedo["spawn_or_evolution_in_emulator_verified"])

    def test_no_loss_of_land_species(self):
        self.put_land(self.candidate,["SPECIES_MAGIKARP"])
        with self.assertRaisesRegex(ValueError,"lost an existing species"):
            mod.inspect(self.orig,self.candidate,self.data_dir)

    def test_missing_species_info_fail_closed(self):
        (self.data_dir/mod.METADATA_FILES[2]).unlink()
        with self.assertRaisesRegex(ValueError,"missing pinned World"):
            mod.inspect(self.orig,self.candidate,self.data_dir)

    def test_unbalanced_evolution_expression_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"unbalanced evolution"):
            mod.edges_from_text("[SPECIES_A] = { .evolutions = EVOLUTION({EVO_LEVEL, 2, SPECIES_B},")

    def test_truncated_encounter_maps_fail_closed(self):
        self.orig.write_text('{"wild_encounter_groups":[]}')
        with self.assertRaisesRegex(ValueError,"full World"):
            mod.inspect(self.orig,self.candidate,self.data_dir)


if __name__=="__main__":
    unittest.main()
