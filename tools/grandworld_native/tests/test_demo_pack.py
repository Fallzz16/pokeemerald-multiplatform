"""Reproducibility tests for our own (not third-party) graphics demo."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.grandworld_native import demo_pack
from tools.grandworld_native.modpacks import validate_zip


class DemoPackTests(unittest.TestCase):
    def test_eight_poses_and_base_are_present(self):
        with tempfile.TemporaryDirectory() as root:
            report = demo_pack.create(Path(root))
            info = validate_zip(report["path"])
            self.assertEqual(info["asset_count"], 10)
            with zipfile.ZipFile(report["path"]) as z:
                manifest = json.loads(z.read("manifest.json"))
                identifiers = {a["id"] for a in manifest["assets"]}
                self.assertIn("menus/background", identifiers)
                self.assertIn("sprites/follower", identifiers)
                poses = ("n", "ne", "e", "se", "s", "sw", "w", "nw")
                for pose in poses:
                    self.assertIn("sprites/follower/" + pose, identifiers)
                hashes = {
                    a["sha256"] for a in manifest["assets"]
                    if a["id"].startswith("sprites/follower/")
                }
                self.assertEqual(len(hashes), 8, "each facing should have its own PNG frame")

    def test_all_generated_pictures_are_real_png_files(self):
        with tempfile.TemporaryDirectory() as root:
            report = demo_pack.create(Path(root))
            with zipfile.ZipFile(report["path"]) as z:
                for name in z.namelist():
                    if name.endswith(".png"):
                        self.assertTrue(z.read(name).startswith(b"\x89PNG\r\n\x1a\n"))

if __name__ == "__main__":
    unittest.main()
