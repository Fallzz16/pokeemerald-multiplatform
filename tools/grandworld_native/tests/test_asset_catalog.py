import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.grandworld_native.asset_catalog import generate_catalog
from tools.grandworld_native import pack_manager
from tools.grandworld_native.modpacks import PackError

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "mods"
        self.zip = Path(self.tmp.name) / "test.zip"
        self.bytes = b"BM data fake but checksum-valid"
        rel = "assets/menus/background.bmp"
        self.manifest = {"api":1,"id":"demo.theme","version":"1.0.0",
                         "assets":[{"id":"menus/background", "path":rel,
                                    "sha256":hashlib.sha256(self.bytes).hexdigest()}]}
        with zipfile.ZipFile(self.zip,"w") as z:
            z.writestr("manifest.json",json.dumps(self.manifest))
            z.writestr(rel,self.bytes)
        pack_manager.install(self.zip,self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_disabled_empty_catalog(self):
        r=generate_catalog(self.root)
        self.assertEqual(r["assets"],0)

    def test_toggle_updates_catalog_explicitly(self):
        pack_manager.toggle(self.root,"demo.theme",True)
        r=generate_catalog(self.root)
        self.assertEqual(r["assets"],1)
        lines=(self.root/"runtime-assets.tsv").read_text().splitlines()
        self.assertEqual(lines[0],"GW_ASSETS_V1")
        self.assertEqual(lines[1],"menus\tdemo.theme\tmenus/background\tdemo.theme/assets/menus/background.bmp")

    def test_modified_asset_rejected_without_overwriting_good_index(self):
        pack_manager.toggle(self.root,"demo.theme",True)
        generate_catalog(self.root)
        original=(self.root/"runtime-assets.tsv").read_bytes()
        (self.root/"demo.theme/assets/menus/background.bmp").write_bytes(b"modified")
        with self.assertRaises(PackError):
            generate_catalog(self.root)
        self.assertEqual((self.root/"runtime-assets.tsv").read_bytes(),original)

    def test_manifest_path_escape_rejected(self):
        pack_manager.toggle(self.root,"demo.theme",True)
        mfile=self.root/"demo.theme/manifest.json"
        m=json.loads(mfile.read_text())
        m["assets"][0]["path"]="../bypass.bmp"
        mfile.write_text(json.dumps(m))
        with self.assertRaises(PackError):
            generate_catalog(self.root)

    def test_no_save_files(self):
        generate_catalog(self.root)
        self.assertFalse(list(self.root.rglob("*.sav")))

if __name__ == "__main__":
    unittest.main()
