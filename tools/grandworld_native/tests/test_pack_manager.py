import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.grandworld_native import pack_manager
from tools.grandworld_native.modpacks import PackError


def make_zip(path):
    payload = b"not a copyrighted sprite"
    name = "assets/sprites/test.png"
    manifest = {"api": 1, "id": "my-safe-pack", "version": "1.0.0",
                "assets": [{"id": "test/demo", "path": name,
                            "sha256": hashlib.sha256(payload).hexdigest()}]}
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("manifest.json", json.dumps(manifest))
        z.writestr(name, payload)


class PackManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.zip = Path(self.temp.name) / "pack.zip"
        self.root = Path(self.temp.name) / "modpacks"
        make_zip(self.zip)

    def tearDown(self):
        self.temp.cleanup()

    def test_install_toggle_and_list(self):
        pack_manager.install(self.zip, self.root)
        self.assertEqual(pack_manager.list_packs(self.root)[0]["enabled"], False)
        pack_manager.toggle(self.root, "my-safe-pack", True)
        self.assertEqual(pack_manager.list_packs(self.root)[0]["enabled"], True)
        pack_manager.toggle(self.root, "my-safe-pack", False)
        self.assertEqual(pack_manager.list_packs(self.root)[0]["enabled"], False)
        self.assertTrue((self.root / "my-safe-pack" / "manifest.json").is_file())

    def test_refuses_existing_pack_and_does_not_delete_it(self):
        pack_manager.install(self.zip, self.root)
        with self.assertRaises(PackError):
            pack_manager.install(self.zip, self.root)
        self.assertTrue((self.root / "my-safe-pack" / "assets/sprites/test.png").is_file())

    def test_refuses_uninstalled_pack(self):
        with self.assertRaises(PackError):
            pack_manager.toggle(self.root, "my-safe-pack", True)

    def test_refuses_traversal(self):
        with self.assertRaises(PackError):
            pack_manager.toggle(self.root, "../outside", True)

    def test_disabled_by_default_and_no_saves_created(self):
        pack_manager.install(self.zip, self.root)
        self.assertFalse((self.root / "enabled.json").exists())
        self.assertFalse(any(self.root.rglob("*.sav")))


if __name__ == "__main__":
    unittest.main()
