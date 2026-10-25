"""P2 final link gate tests: never mistake partial or failed links for gameplay."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

from tools.grandworld_native.final_link_probe import attempt


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
