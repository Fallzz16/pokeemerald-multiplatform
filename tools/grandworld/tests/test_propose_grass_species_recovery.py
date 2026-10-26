"""Reversible source-data tests for proposed M8 grass-only species recovery."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

P=Path(__file__).resolve().parents[1]/"propose_grass_species_recovery.py"
spec=importlib.util.spec_from_file_location("recovery",P)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def slot(species,lv=8):
    return {"min_level":lv,"max_level":lv+1,"species":"SPECIES_"+species}


def field(species, n=12):
    return {"encounter_rate":20,"mons":[slot(species) for _ in range(n)]}


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"source.json"
        self.a={"map":"MAP_ROUTE30",
                "land_mons":field("RATTATA"),
                "water_mons":field("BUIZEL",5)}
        self.b={"map":"MAP_ROUTE31",
                "land_mons":field("PIDGEY"),
                "fishing_mons":field("MAGIKARP",10)}
        self.filler=[{"map":f"MAP_BUILDING_{i}"} for i in range(302)]
        self.data={"wild_encounter_groups":[
            {"label":"gWildMonHeaders","for_maps":True,
             "encounters":[self.a,self.b,*self.filler]}]}
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.data),encoding="utf-8")

    def test_plan_preserves_source_and_reports_manual_gates(self):
        before=self.path.read_bytes()
        _,r=mod.propose(self.path)
        self.assertEqual(r["proposed_count"],2)
        self.assertEqual(r["disabled_method_species_without_land"],2)
        self.assertEqual({x["species"] for x in r["proposals"]},
                         {"SPECIES_BUIZEL","SPECIES_MAGIKARP"})
        self.assertEqual(len({x["map"] for x in r["proposals"]}),2)
        self.assertFalse(r["grass_tiles_verified"])
        self.assertFalse(r["rom_emulator_verified"])
        self.assertEqual(before,self.path.read_bytes())

    def test_reversible_candidate_not_production_mutation(self):
        out=Path(self.tmp.name)/"draft-only.json"
        before=self.path.read_bytes()
        r=mod.make_experimental_table(self.path,out)
        self.assertEqual(before,self.path.read_bytes())
        self.assertTrue(out.exists())
        changed=json.loads(out.read_text())
        group=changed["wild_encounter_groups"][0]["encounters"]
        a,b=group[:2]
        self.assertIn("SPECIES_BUIZEL",[x["species"] for x in a["land_mons"]["mons"]])
        self.assertIn("SPECIES_MAGIKARP",[x["species"] for x in b["land_mons"]["mons"]])
        self.assertIn("SPECIES_RATTATA",[x["species"] for x in a["land_mons"]["mons"]])
        self.assertIn("SPECIES_PIDGEY",[x["species"] for x in b["land_mons"]["mons"]])
        self.assertEqual(len(a["land_mons"]["mons"]),12)
        self.assertEqual(r["net_new_land_species_count"],2)
        self.assertFalse(r["release_approved"])

    def test_new_entries_keep_old_slot_level_curve(self):
        out=Path(self.tmp.name)/"candidate.json"
        mod.make_experimental_table(self.path,out)
        src=json.loads(self.path.read_text())["wild_encounter_groups"][0]["encounters"]
        dst=json.loads(out.read_text())["wild_encounter_groups"][0]["encounters"]
        for a,b in zip(src,dst):
            if "land_mons" not in a:continue
            for old,new in zip(a["land_mons"]["mons"],b["land_mons"]["mons"]):
                self.assertEqual(old["min_level"],new["min_level"])
                self.assertEqual(old["max_level"],new["max_level"])

    def test_fails_if_same_route_has_unique_land_slots(self):
        self.a["land_mons"]["mons"]=[slot("P"+str(i)) for i in range(12)]
        self.save()
        _,r=mod.propose(self.path)
        self.assertEqual(r["proposed_count"],1)
        self.assertIn("SPECIES_BUIZEL",[x["species"] for x in r["blocked"]])

    def test_fails_closed_on_duplicate_map_entries(self):
        self.data["wild_encounter_groups"][0]["encounters"].append(dict(self.a))
        self.save()
        _,r=mod.propose(self.path)
        self.assertEqual(r["proposed_count"],1)
        self.assertIn("SPECIES_BUIZEL",[x["species"] for x in r["blocked"]])

    def test_cannot_overwrite_source_or_existing_candidate(self):
        with self.assertRaisesRegex(ValueError,"refusing to overwrite"):
            mod.make_experimental_table(self.path,self.path)
        out=Path(self.tmp.name)/"candidate.json"
        mod.make_experimental_table(self.path,out)
        with self.assertRaisesRegex(ValueError,"already exists"):
            mod.make_experimental_table(self.path,out)

    def test_ocean_route_not_proposed_as_walkable_grass(self):
        maps = Path(self.tmp.name) / "maps"
        for route, kind in [("Route30", "MAP_TYPE_OCEAN_ROUTE"),
                            ("Route31", "MAP_TYPE_ROUTE")]:
            d = maps / route
            d.mkdir(parents=True)
            (d / "map.json").write_text(json.dumps({
                "id": "MAP_" + route.upper(),
                "map_type": kind,
            }))
        _, plan = mod.propose(self.path, maps_dir=maps)
        self.assertEqual(plan["proposed_count"], 1)
        self.assertTrue(plan["ocean_routes_excluded"])
        self.assertTrue(plan["route_map_types_checked"])
        self.assertEqual(plan["proposals"][0]["species"], "SPECIES_MAGIKARP")
        self.assertIn("SPECIES_BUIZEL", [v["species"] for v in plan["blocked"]])

    def test_missing_route_metadata_fails_closed(self):
        maps = Path(self.tmp.name) / "missing-maps"
        maps.mkdir()
        with self.assertRaisesRegex(ValueError, "missing or invalid route map"):
            mod.propose(self.path, maps_dir=maps)

    def test_actual_gba_evidence_blocks_zero_grass_route(self):
        maps=Path(self.tmp.name)/"maps"
        for name in ("Route30","Route31"):
            p=maps/name
            p.mkdir(parents=True)
            (p/"map.json").write_text(json.dumps({
                "id":"MAP_"+name.upper(),"map_type":"MAP_TYPE_ROUTE"}))
        evidence=Path(self.tmp.name)/"real_emulator_tiles.json"
        evidence.write_text(json.dumps({
            "schema":1,
            "pinned_engine_sha":"15d3888b0d81322a04d3c71b0bce18948761ee44",
            "metatile_behavior":2,
            "map_coordinates_exclude_border":True,
            "workflow_run_url":"https://example.invalid/rom-proof",
            "verified_map_tall_grass_counts":{"MAP_ROUTE30":0,"MAP_ROUTE31":15},
        }))
        _,out=mod.propose(self.path,maps_dir=maps,grass_evidence=evidence)
        self.assertEqual(out["proposed_count"],1)
        self.assertTrue(out["real_emulator_grass_gate_applied"])
        self.assertEqual(out["proposals"][0]["map"],"MAP_ROUTE31")
        self.assertEqual(out["proposals"][0]["species"],"SPECIES_MAGIKARP")
        self.assertIn("SPECIES_BUIZEL",[q["species"] for q in out["blocked"]])

    def test_unverified_route_never_defaults_to_grass(self):
        maps=Path(self.tmp.name)/"maps"
        for name in ("Route30","Route31"):
            p=maps/name
            p.mkdir(parents=True)
            (p/"map.json").write_text(json.dumps({
                "id":"MAP_"+name.upper(),"map_type":"MAP_TYPE_ROUTE"}))
        evidence=Path(self.tmp.name)/"partial_map_evidence.json"
        evidence.write_text(json.dumps({
            "schema":1,"pinned_engine_sha":"15d3888b0d81322a04d3c71b0bce18948761ee44",
            "metatile_behavior":2,"map_coordinates_exclude_border":True,
            "verified_map_tall_grass_counts":{"MAP_ROUTE31":20},
        }))
        _,out=mod.propose(self.path,maps_dir=maps,grass_evidence=evidence)
        self.assertEqual(out["proposed_count"],1)
        self.assertEqual(out["proposals"][0]["map"],"MAP_ROUTE31")

    def test_corrupt_emulator_proof_rejected(self):
        invalid=Path(self.tmp.name)/"not_verifiable.json"
        invalid.write_text(json.dumps({"schema":1,"verified_map_tall_grass_counts":{"MAP_ROUTE30":2}}))
        with self.assertRaisesRegex(ValueError,"untrusted or incomplete"):
            mod.propose(self.path,maps_dir=Path(self.tmp.name),grass_evidence=invalid)

    def test_rejects_truncated_table(self):
        self.data["wild_encounter_groups"][0]["encounters"]=[self.a]
        self.save()
        with self.assertRaisesRegex(ValueError,"missing full"):
            mod.propose(self.path)


if __name__=="__main__":
    unittest.main()
