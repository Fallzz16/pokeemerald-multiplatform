"""No fake World gameplay is ever claimed as boot verification."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.grandworld_native import boot_smoke


class RealEngineBootGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.link = self.root / "link.json"
        self.exe = self.root / "grandworld-WORLD-NOT-BOOT-VERIFIED"

    def tearDown(self):
        self.tmp.cleanup()

    def test_never_attempt_boot_without_real_link(self):
        self.link.write_text('{"link_succeeded":false}', encoding="utf-8")
        with patch.object(boot_smoke.subprocess, "run") as run:
            result = boot_smoke.verify(self.link, self.exe)
        run.assert_not_called()
        self.assertFalse(result["attempted"])
        self.assertFalse(result["real_first_frame_presented"])

    def test_missing_executable_rejected_even_after_link(self):
        self.link.write_text('{"link_succeeded":true}', encoding="utf-8")
        result = boot_smoke.verify(self.link, self.exe)
        self.assertFalse(result["attempted"])
        self.assertFalse(result["real_first_frame_presented"])

    def test_actual_engine_markers_and_success_are_both_required(self):
        self.link.write_text('{"link_succeeded":true}', encoding="utf-8")
        self.exe.write_bytes(b"fixture executable never run")
        result_ok = subprocess.CompletedProcess([], 0, "\n".join(boot_smoke.MARKERS), "")
        with patch.object(boot_smoke.subprocess, "run", return_value=result_ok) as run:
            result = boot_smoke.verify(self.link, self.exe)
        self.assertTrue(result["real_first_frame_presented"])
        self.assertTrue(result["real_game_initialized"])
        self.assertIn("--smoke-test", run.call_args.args[0])
        self.assertEqual(run.call_args.kwargs["env"]["SDL_VIDEODRIVER"], "dummy")
        result_bad = subprocess.CompletedProcess([], 1, "\n".join(boot_smoke.MARKERS), "")
        with patch.object(boot_smoke.subprocess, "run", return_value=result_bad):
            result = boot_smoke.verify(self.link, self.exe)
        self.assertFalse(result["real_first_frame_presented"])

    def test_initialization_alone_does_not_count_as_rendered_frame(self):
        self.link.write_text('{"link_succeeded":true}', encoding="utf-8")
        self.exe.write_bytes(b"fixture")
        fake = subprocess.CompletedProcess([], 0, boot_smoke.MARKERS[0], "")
        with patch.object(boot_smoke.subprocess, "run", return_value=fake):
            result = boot_smoke.verify(self.link, self.exe)
        self.assertTrue(result["real_game_initialized"])
        self.assertFalse(result["real_first_frame_presented"])


if __name__ == "__main__":
    unittest.main()
