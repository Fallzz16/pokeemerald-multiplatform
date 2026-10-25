import hashlib
import io
import json
import os
import tempfile
import unittest
import zipfile

from tools.grandworld_native.modpacks import PackError, validate_zip


def make_pack(path, name="assets/sprites/pikachu.png", body=b"PNG TEST"):
    manifest = {"api": 1, "id": "sample-pack", "version": "1.0.0",
                "assets": [{"id": "pokemon/pikachu/idle", "path": name,
                            "sha256": hashlib.sha256(body).hexdigest()}]}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest))
        z.writestr(name, body)


class PackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "pack.zip")

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_data_pack(self):
        make_pack(self.path)
        info = validate_zip(self.path)
        self.assertTrue(info["validated"])
        self.assertEqual(info["asset_count"], 1)
        self.assertFalse(info["code_execution_supported"])

    def test_path_traversal_rejected(self):
        make_pack(self.path, "../evil.py")
        with self.assertRaises(PackError):
            validate_zip(self.path)

    def test_code_plugins_rejected(self):
        make_pack(self.path, "assets/sprites/code.py")
        with self.assertRaises(PackError):
            validate_zip(self.path)

    def test_unlisted_file_rejected(self):
        make_pack(self.path)
        with zipfile.ZipFile(self.path, "a") as z:
            z.writestr("assets/sprites/unlisted.png", b"x")
        with self.assertRaises(PackError):
            validate_zip(self.path)

    def test_checksum_rejected(self):
        make_pack(self.path)
        with zipfile.ZipFile(self.path, "r") as z:
            manifest = json.loads(z.read("manifest.json"))
            body = z.read("assets/sprites/pikachu.png")
        manifest["assets"][0]["sha256"] = "0" * 64
        with zipfile.ZipFile(self.path, "w") as z:
            z.writestr("manifest.json", json.dumps(manifest))
            z.writestr("assets/sprites/pikachu.png", body)
        with self.assertRaises(PackError):
            validate_zip(self.path)

    def test_duplicate_case_paths(self):
        make_pack(self.path)
        with zipfile.ZipFile(self.path, "a") as z:
            z.writestr("Assets/Sprites/Pikachu.png", b"x")
        with self.assertRaises(PackError):
            validate_zip(self.path)


if __name__ == "__main__":
    unittest.main()
