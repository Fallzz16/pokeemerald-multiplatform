"""P2 final link gate tests: never mistake partial or failed links for gameplay."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
import subprocess

from tools.grandworld_native.final_link_probe import (
    attempt, attach_coverage, verify_compiled_objects, require_complete_input_coverage,
)


class RealGameLinkGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.code = self.root / "code"
        self.data = self.root / "data"
        self.platform = self.root / "platform"
        for folder in (self.code, self.data, self.platform):
            folder.mkdir()
        self.frontend = self.root / "main.o"
        self.report = self.root / "report.json"

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_actual_objects_fail_without_linking(self):
        with patch("tools.grandworld_native.final_link_probe.subprocess.run") as runner:
            info = attempt(self.code, self.data, self.platform,
                           self.frontend, self.report)
        self.assertFalse(info["link_succeeded"])
        self.assertFalse(info["gameplay_verified"])
        self.assertFalse(info["game_boot_verified"])
        runner.assert_not_called()

    def test_link_failure_reports_real_unresolved_symbols(self):
        for folder in (self.code, self.data, self.platform):
            (folder / "real.o").write_bytes(b"object-test-placeholder")
        self.frontend.write_bytes(b"frontend-placeholder")
        diagnostics = (
            "ld: main.o: undefined reference to `gGameData'\n"
            "ld: main.o: undefined reference to `gGameData'\n"
            "ld: script.o: undefined reference to `Script_Example'\n"
            "collect2: error: ld returned 1 exit status\n"
        )
        with patch("tools.grandworld_native.final_link_probe.shutil.which",
                   return_value="/usr/bin/gcc"), patch(
                       "tools.grandworld_native.final_link_probe.subprocess.run",
                       return_value=subprocess.CompletedProcess(
                           ["gcc"], 1, "", diagnostics)) as runner:
            info = attempt(self.code, self.data, self.platform,
                           self.frontend, self.report)
        self.assertFalse(info["link_succeeded"])
        self.assertEqual(info["undefined_unique_count"], 2)
        self.assertEqual(info["undefined_reference_examples"][0]["symbol"], "gGameData")
        self.assertEqual(info["undefined_reference_examples"][0]["occurrences"], 2)
        args = runner.call_args.args[0]
        self.assertIn("-Wl,--no-undefined", args)
        self.assertNotIn("--unresolved-symbols=ignore-all", " ".join(args))
        self.assertFalse((self.root / "grandworld-WORLD-NOT-BOOT-VERIFIED").exists())

    def test_link_report_never_implies_complete_game_when_sources_fail(self):
        source = self.root / "source.json"
        data = self.root / "data.json"
        source.write_text(json.dumps({"compiled": 402, "requested": 405}), encoding="utf-8")
        data.write_text(json.dumps({"native_objects": 13, "original_source_files": 14}),
                        encoding="utf-8")
        result = attach_coverage({
            "link_succeeded": False, "gameplay_verified": False,
        }, source, data)
        self.assertFalse(result["game_sources_all_compiled"])
        self.assertFalse(result["game_data_all_compiled"])
        self.assertFalse(result["ready_for_distribution"])
        self.assertEqual(result["source_compiled"], 402)
        self.assertEqual(result["data_compiled"], 13)

    def test_compiled_objects_must_match_real_source_and_asset_audits(self):
        (self.code / "main.o").write_bytes(b"genuine-test-compiled-source")
        (self.data / "event_scripts.o").write_bytes(b"genuine-test-assembled-data")
        source = self.root / "full-source-audit.json"
        asset = self.root / "full-data-audit.json"
        source.write_text(json.dumps({
            "compiled": 1, "requested": 1,
            "objects": [{"source": "src/main.c", "object": "main.o",
                         "status": "object_compiled"}],
        }), encoding="utf-8")
        asset.write_text(json.dumps({
            "native_objects": 1, "original_source_files": 1,
            "results": [{"source": "data/event_scripts.s",
                         "native_object": True}],
        }), encoding="utf-8")
        good = verify_compiled_objects(source, asset, self.code, self.data)
        self.assertTrue(good["source_object_set_verified"])
        self.assertTrue(good["data_object_set_verified"])
        (self.code / "ghost.o").write_bytes(b"leftover-from-failed-compile")
        (self.data / "event_scripts.o").unlink()
        bad = verify_compiled_objects(source, asset, self.code, self.data)
        self.assertFalse(bad["source_object_set_verified"])
        self.assertFalse(bad["data_object_set_verified"])
        self.assertEqual(bad["source_stale_object_files"], ["ghost.o"])
        self.assertEqual(bad["data_missing_object_files"], ["event_scripts.o"])

    def test_duplicated_asm_object_names_are_rejected(self):
        source = self.root / "source.json"
        data = self.root / "data.json"
        source.write_text(json.dumps({
            "objects": [{"object": "main.o", "status": "object_compiled"}],
        }), encoding="utf-8")
        data.write_text(json.dumps({
            "results": [
                {"source": "data/a.s", "native_object": True},
                {"source": "sound/a.s", "native_object": True},
            ],
        }), encoding="utf-8")
        with self.assertRaises(ValueError):
            verify_compiled_objects(source, data, self.code, self.data)

    def test_link_success_requires_every_original_C_and_ASM_file(self):
        # The on-disk files can match a partial compiler report exactly.
        # That does NOT mean the complete original game was compiled.
        candidate = self.root / "grandworld-WORLD-NOT-BOOT-VERIFIED"
        candidate.write_bytes(b"an incomplete build must be deleted")
        status = {
            "link_succeeded": True,
            "source_object_set_verified": True,
            "data_object_set_verified": True,
            "game_sources_all_compiled": False,
            "game_data_all_compiled": True,
        }
        verified = require_complete_input_coverage(status, self.report)
        self.assertFalse(verified["link_succeeded"])
        self.assertFalse(verified["full_input_inventory_verified"])
        self.assertEqual(verified["input_coverage_failed_gates"],
                         ["game_sources_all_compiled"])
        self.assertFalse(candidate.exists())

        candidate.write_bytes(b"data missing")
        status.update(link_succeeded=True, game_sources_all_compiled=True,
                      game_data_all_compiled=False)
        verified = require_complete_input_coverage(status, self.report)
        self.assertFalse(verified["link_succeeded"])
        self.assertEqual(verified["input_coverage_failed_gates"],
                         ["game_data_all_compiled"])
        self.assertFalse(candidate.exists())

    def test_full_input_inventory_does_not_claim_gameplay(self):
        status = {
            "link_succeeded": True,
            "game_boot_verified": False,
            "gameplay_verified": False,
            "source_object_set_verified": True,
            "data_object_set_verified": True,
            "game_sources_all_compiled": True,
            "game_data_all_compiled": True,
        }
        verified = require_complete_input_coverage(status, self.report)
        self.assertTrue(verified["link_succeeded"])
        self.assertTrue(verified["full_input_inventory_verified"])
        self.assertFalse(verified["game_boot_verified"])
        self.assertFalse(verified["gameplay_verified"])

    def test_even_a_successful_link_is_not_a_boot_test(self):
        for folder in (self.code, self.data, self.platform):
            (folder / "real.o").write_bytes(b"object-test-placeholder")
        self.frontend.write_bytes(b"frontend-placeholder")
        target = self.root / "grandworld-WORLD-NOT-BOOT-VERIFIED"
        def fake_link(args, **kwargs):
            target.write_bytes(b"ELF test placeholder")
            return subprocess.CompletedProcess(args, 0, "", "")
        with patch("tools.grandworld_native.final_link_probe.shutil.which",
                   return_value="/usr/bin/gcc"), patch(
                       "tools.grandworld_native.final_link_probe.subprocess.run",
                       side_effect=fake_link):
            info = attempt(self.code, self.data, self.platform,
                           self.frontend, self.report)
        self.assertTrue(info["link_succeeded"])
        self.assertFalse(info["game_boot_verified"])
        self.assertFalse(info["gameplay_verified"])
        self.assertFalse(info["windows_executable_created"])


if __name__ == "__main__":
    unittest.main()
