"""Headless coverage of the graphical pack manager's shared backend."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.grandworld_native import pack_manager, plugin_ui
from tools.grandworld_native.modpacks import PackError


class GUIBackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "mods"
        self.zip = Path(self.tmp.name) / "style.zip"
        self.menu = b"PNG-mock"
        self.mon = b"sprite-mock"
        assets = {
            "assets/menus/background.png": self.menu,
            "assets/sprites/follower.png": self.mon,
        }
        manifest = {
            "api": 1, "id": "style-test", "version": "1.0.0",
            "assets": [
                {"id": "menus/background", "path": "assets/menus/background.png",
                 "sha256": hashlib.sha256(self.menu).hexdigest()},
                {"id": "sprites/follower", "path": "assets/sprites/follower.png",
                 "sha256": hashlib.sha256(self.mon).hexdigest()},
            ],
        }
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr("manifest.json", json.dumps(manifest))
            for name, data in assets.items():
                z.writestr(name, data)
        pack_manager.install(self.zip, self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_classic_disabled(self):
        self.assertEqual(plugin_ui.available_styles(self.root, "menus"), ["classic"])
        self.assertEqual(plugin_ui.available_styles(self.root, "sprites"), ["classic"])
        self.assertEqual(plugin_ui.read_selection(self.root),
                         {"menus": "classic", "sprites": "classic"})

    def test_enabled_pack_changes_both_categories(self):
        pack_manager.toggle(self.root, "style-test", True)
        self.assertEqual(plugin_ui.available_styles(self.root, "menus"),
                         ["classic", "style-test"])
        self.assertEqual(plugin_ui.available_styles(self.root, "sprites"),
                         ["classic", "style-test"])
        prefs = plugin_ui.write_selection(self.root, "style-test", "style-test")
        self.assertEqual(plugin_ui.read_selection(self.root), prefs)
        self.assertTrue((self.root / "runtime-assets.tsv").exists())

    def test_disabled_pack_falls_back_and_never_touches_saves(self):
        pack_manager.toggle(self.root, "style-test", True)
        plugin_ui.write_selection(self.root, "style-test", "style-test")
        pack_manager.toggle(self.root, "style-test", False)
        self.assertEqual(plugin_ui.read_selection(self.root),
                         {"menus": "classic", "sprites": "classic"})
        self.assertFalse(list(self.root.rglob("*.sav")))

    def test_disabled_pack_not_selectable(self):
        with self.assertRaises(PackError):
            plugin_ui.write_selection(self.root, "style-test", "classic")
        self.assertFalse((self.root / "style-settings.ini").exists())

    def test_bad_or_malformed_setting_rejected(self):
        (self.root / "style-settings.ini").write_text("no header\nmenus=foo\n", encoding="utf-8")
        with self.assertRaises(PackError):
            plugin_ui.read_selection(self.root)


if __name__ == "__main__":
    unittest.main()
