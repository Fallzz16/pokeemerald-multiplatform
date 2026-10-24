"""Regression tests for the strict M8 ROM evidence contract."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "qa_acceptance.py"
spec = importlib.util.spec_from_file_location("grandworld_qa", MODULE_PATH)
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)

SHA = "a" * 64
SIZE = 33554432
MEM = {"ROM": 25000000, "EWRAM": 230000, "IWRAM": 30000}


class EvidenceContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "evidence.json"
        self.valid = {"sha": SHA, "rom_size": SIZE, "memory": MEM}

    def write(self, obj):
        self.path.write_text(json.dumps(obj), encoding="utf-8")

    def test_matching_sha_size_and_memory(self):
        self.write(self.valid)
        self.assertEqual(qa.load_memory_proof(self.path, SHA, SIZE), MEM)

    def test_missing_or_incorrect_size(self):
        for obj in ({**self.valid, "rom_size": SIZE - 1},
                    {k: v for k, v in self.valid.items() if k != "rom_size"},
                    {**self.valid, "rom_size": str(SIZE)}):
            with self.subTest(obj=obj):
                self.write(obj)
                with self.assertRaisesRegex(ValueError, "different ROM"):
                    qa.load_memory_proof(self.path, SHA, SIZE)

    def test_divergent_hash(self):
        self.write({**self.valid, "sha": "b" * 64})
        with self.assertRaisesRegex(ValueError, "different ROM"):
            qa.load_memory_proof(self.path, SHA, SIZE)

    def test_legacy_size_evidence_rejected(self):
        self.write({"sha": SHA, "size": SIZE, "memory": MEM})
        with self.assertRaisesRegex(ValueError, "different ROM"):
            qa.load_memory_proof(self.path, SHA, SIZE)

    def test_invalid_json_and_invalid_results(self):
        for data in ("{invalid", "[]", "null", json.dumps({**self.valid, "memory": []})):
            with self.subTest(data=data):
                self.path.write_text(data, encoding="utf-8")
                with self.assertRaises(ValueError):
                    qa.load_memory_proof(self.path, SHA, SIZE)
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, "invalid memory evidence file"):
            qa.load_memory_proof(self.path, SHA, SIZE)


    def test_gameplay_suite_evidence_requires_exact_rom_md5_and_count(self):
        world = Path(self.temp.name)
        witness = world / "_pwtest"
        witness.mkdir()
        good_md5 = "A" * 32
        stamp = witness / "GrandWorldHeroSave.PASS"
        stamp.write_text(
            "PASS 37/37 rom=" + good_md5
            + " at=2026-10-24T05:12:00Z suite=GrandWorldHeroSave\n"
        )
        result = qa.load_suite_proof(world, "GrandWorldHeroSave", good_md5, 37)
        self.assertEqual(result["passed"], 37)
        self.assertEqual(result["rom_md5"], good_md5)
        for md5, checks in (("B" * 32, 37), (good_md5, 36)):
            with self.subTest(md5=md5, checks=checks):
                with self.assertRaisesRegex(ValueError, "incomplete"):
                    qa.load_suite_proof(world, "GrandWorldHeroSave", md5, checks)

    def test_advisory_absence_and_failure_stay_pending(self):
        world = Path(self.temp.name)
        stamps = world / "_pwtest"
        stamps.mkdir()
        self.assertIsNone(qa.load_suite_proof(world, "GrandWorldHubParty", "A" * 32, 94))
        (stamps / "GrandWorldHubParty.FAIL").write_text("FAIL 1/94")
        self.assertIsNone(qa.load_suite_proof(world, "GrandWorldHubParty", "A" * 32, 94))
        with self.assertRaisesRegex(ValueError, "failed"):
            qa.load_suite_proof(world, "GrandWorldHubParty", "A" * 32, 94, required=True)

    def test_stale_malformed_and_conflicting_stamps_fail_closed(self):
        world = Path(self.temp.name)
        stamps = world / "_pwtest"
        stamps.mkdir()
        path = stamps / "SSAquaKantoCrossing.PASS"
        for content in (
            "PASS 20/20 rom=" + "A" * 32 + " at=now suite=SSAquaKantoCrossing",
            "PASS 94/95 rom=" + "A" * 32 + " at=now suite=SSAquaKantoCrossing",
            "PASS 94/94 rom=" + "A" * 32 + " at=now suite=WrongSuite",
            "PASS 94/94 rom=" + "not-a-hash" + " at=now suite=SSAquaKantoCrossing",
        ):
            with self.subTest(content=content):
                path.write_text(content)
                with self.assertRaisesRegex(ValueError, "incomplete"):
                    qa.load_suite_proof(world, "SSAquaKantoCrossing", "A" * 32, 94)
        path.write_text("PASS 94/94 rom=" + "A" * 32 + " at=now suite=SSAquaKantoCrossing")
        (stamps / "SSAquaKantoCrossing.FAIL").write_text("FAIL")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            qa.load_suite_proof(world, "SSAquaKantoCrossing", "A" * 32, 94)

    def test_exact_six_travel_cases_require_single_complete_suite(self):
        from copy import deepcopy
        data = {
            "source": "headless mGBA Lua",
            "suite": "GrandWorldSixRoutes",
            "passed": 167,
            "rom_md5": "A" * 32,
        }
        seen = {"performance.memory": {"source": "linker"}}
        qa.register_six_route_proofs(seen, None)
        self.assertEqual(set(seen), {"performance.memory"})
        qa.register_six_route_proofs(seen, data)
        keys = {case for case in seen if case.startswith("travel.")}
        self.assertEqual(len(keys), 6)
        self.assertEqual(keys, {case for case in qa.manifest()
                                if case.startswith("travel.")})
        self.assertEqual(len(seen), 7)
        for case in keys:
            self.assertIn(seen[case]["proven_real_gate"], case)
            self.assertEqual(seen[case]["rom_md5"], "A" * 32)
            self.assertEqual(seen[case]["passed"], 167)
        self.assertNotIn("proven_real_gate", data)
        seen["travel.hoenn_to_kanto"]["passed"] = 0
        self.assertEqual(seen["travel.kanto_to_johto"]["passed"], 167)



    def test_save_migration_requires_all_three_actual_fixture_suites(self):
        world = Path(self.temp.name)
        output = world / "_pwtest"
        output.mkdir()
        md5 = "B" * 32
        cases = [("VerifyV7Migrate", 14), ("MigrateFixtures", 7),
                 ("VerifyMapRenumber", 4)]
        def proof():
            return qa.load_suite_group_proof(
                world, md5, "save.migration", cases, "tracked historical saves")
        self.assertIsNone(proof())
        for name, count in cases:
            (output / (name + ".PASS")).write_text(
                f"PASS {count}/{count} rom={md5} at=2026-10-24T06:31:54Z suite={name}")
        got = proof()
        self.assertEqual(len(got["suites"]), 3)
        self.assertTrue(all(x["rom_md5"] == md5 for x in got["suites"]))
        (output / "VerifyV7Migrate.PASS").unlink()
        self.assertIsNone(proof())
        (output / "VerifyV7Migrate.PASS").write_text(
            f"PASS 13/13 rom={md5} at=now suite=VerifyV7Migrate")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            proof()

    def test_group_rejects_bad_later_stamps_even_if_first_suite_missing(self):
        world = Path(self.temp.name)
        stamps = world / "_pwtest"
        stamps.mkdir()
        md5 = "A" * 32
        group = [("VerifyV7Migrate", 14), ("MigrateFixtures", 7),
                 ("VerifyMapRenumber", 4)]
        # First suite has not run, but the second has contradictory verdicts.
        (stamps / "MigrateFixtures.PASS").write_text(
            f"PASS 7/7 rom={md5} at=now suite=MigrateFixtures")
        (stamps / "MigrateFixtures.FAIL").write_text("FAIL")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            qa.load_suite_group_proof(world, md5, "save.migration",
                                      group, "migration")
        (stamps / "MigrateFixtures.FAIL").unlink()
        (stamps / "MigrateFixtures.PASS").write_text(
            f"PASS 7/7 rom={'B' * 32} at=now suite=MigrateFixtures")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            qa.load_suite_group_proof(world, md5, "save.migration",
                                      group, "migration")
        (stamps / "MigrateFixtures.PASS").unlink()
        self.assertIsNone(qa.load_suite_group_proof(
            world, md5, "save.migration", group, "migration"))

    def test_group_rejects_unexpected_cases_conflicts_and_duplicate_suites(self):
        world = Path(self.temp.name)
        output = world / "_pwtest"
        output.mkdir()
        md5 = "A" * 32
        with self.assertRaisesRegex(ValueError, "unknown"):
            qa.load_suite_group_proof(world, md5, "save.imaginary",
                                      [("StoryProgress", 31)], "none")
        with self.assertRaisesRegex(ValueError, "independent"):
            qa.load_suite_group_proof(world, md5, "save.migration",
                                      [("StoryProgress", 31), ("StoryProgress", 31)], "none")
        stamp = output / "DayNightTint.PASS"
        stamp.write_text(f"PASS 32/32 rom={md5} at=now suite=DayNightTint")
        (output / "DayNightTint.FAIL").write_text("FAIL")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            qa.load_suite_group_proof(world, md5, "graphics.palettes",
                                      [("DayNightTint", 32)], "day/night palette")

    def test_group_missing_one_partner_never_proves_audio(self):
        world = Path(self.temp.name)
        output = world / "_pwtest"
        output.mkdir()
        md5 = "A" * 32
        (output / "JohtoMusicPass.PASS").write_text(
            f"PASS 18/18 rom={md5} at=now suite=JohtoMusicPass")
        group = [("JohtoMusicPass", 18), ("Route41SurfBgm", 11)]
        self.assertIsNone(
            qa.load_suite_group_proof(world, md5, "audio.bgm", group, "Johto music"))
        (output / "Route41SurfBgm.PASS").write_text(
            f"PASS 11/11 rom={md5} at=now suite=Route41SurfBgm")
        proof = qa.load_suite_group_proof(world, md5, "audio.bgm", group, "Johto music")
        self.assertEqual(len(proof["suites"]), 2)


    def test_cross_region_battery_save_requires_complete_independent_verdict(self):
        world = Path(self.temp.name)
        out = world / "_pwtest"
        out.mkdir()
        md5 = "C" * 32
        self.assertIsNone(
            qa.load_suite_proof(world, "GrandWorldCrossRegionSave", md5, 176))
        witness = out / "GrandWorldCrossRegionSave.PASS"
        witness.write_text(
            f"PASS 175/175 rom={md5} at=now suite=GrandWorldCrossRegionSave")
        with self.assertRaisesRegex(ValueError, "incomplete"):
            qa.load_suite_proof(world, "GrandWorldCrossRegionSave", md5, 176)
        witness.write_text(
            f"PASS 176/176 rom={md5} at=now suite=GrandWorldCrossRegionSave")
        proof = qa.load_suite_proof(world, "GrandWorldCrossRegionSave", md5, 176)
        self.assertEqual(proof["passed"], 176)
        self.assertEqual(proof["rom_md5"], md5)


if __name__ == "__main__":
    unittest.main()
