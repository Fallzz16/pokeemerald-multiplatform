"""Adversarial cases discovered during Grand World Native P0/P1 audit.

Only creates disposable original test packs and folders. No ROM/save changes.
"""
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from tools.grandworld_native import asset_catalog

from tools.grandworld_native.modpacks import PackError, validate_zip
from tools.grandworld_native.pack_manager import install, toggle, list_packs
from tools.grandworld_native.plugin_ui import available_styles


def write_pack(zip_path, *, pack_id="audit-safe", version="1.0.0",
               logical="menus/background", image=b"BM-safe-demo",
               pathname="assets/menus/background.bmp", extras=()):
    manifest = {
        "api": 1, "id": pack_id, "version": version,
        "assets": [{"id": logical, "path": pathname,
                    "sha256": hashlib.sha256(image).hexdigest()}]
    }
    with zipfile.ZipFile(zip_path, "w") as pack:
        pack.writestr("manifest.json", json.dumps(manifest))
        pack.writestr(pathname, image)
        for extra in extras:
            if isinstance(extra, tuple):
                pack.writestr(*extra)
            else:
                pack.writestr(extra, b"")


class AuditRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "mods"
        self.zip = Path(self.temp.name) / "sample.zip"

    def tearDown(self):
        self.temp.cleanup()

    def test_reject_zip_path_traversal_hidden_in_directory_entry(self):
        write_pack(self.zip, extras=["../escape/"])
        with self.assertRaises(PackError):
            validate_zip(self.zip)

    def test_reject_directory_symlink_even_if_not_extracted(self):
        link = zipfile.ZipInfo("assets/menus/redirect/")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        write_pack(self.zip, extras=[(link, b"")])
        with self.assertRaises(PackError):
            validate_zip(self.zip)

    def test_reject_malformed_semver(self):
        write_pack(self.zip, version="1..3")
        with self.assertRaises(PackError):
            validate_zip(self.zip)

    def test_reject_native_incompatible_filenames(self):
        for invalid in (
            "assets/menus/Loud.PNG",
            "assets/menus/injected\\nname.bmp",
            "assets/menus/injected\\tname.bmp",
            "assets/menus/two..dots.bmp",
            "assets/menus/space name.bmp",
        ):
            with self.subTest(path=invalid):
                write_pack(self.zip, pathname=invalid)
                with self.assertRaises(PackError):
                    validate_zip(self.zip)


    def test_reject_malformed_logical_asset_id(self):
        write_pack(self.zip, logical="menus//background")
        with self.assertRaises(PackError):
            validate_zip(self.zip)

    def test_install_rolls_back_if_catalog_broken(self):
        self.root.mkdir(parents=True)
        (self.root / "enabled.json").write_text("not-json", encoding="utf-8")
        write_pack(self.zip)
        with self.assertRaises((PackError, ValueError)):
            install(self.zip, self.root)
        self.assertFalse((self.root / "audit-safe").exists())
        self.assertEqual(list(self.root.glob(".pack-*")), [])
        self.assertEqual((self.root / "enabled.json").read_text(), "not-json")

    def test_invalid_enabled_pack_id_fails_closed(self):
        write_pack(self.zip)
        install(self.zip, self.root)
        (self.root / "enabled.json").write_text(
            '{"schema":1,"enabled":["NOT-LOWERCASE"]}', encoding="utf-8")
        with self.assertRaises(PackError):
            list_packs(self.root)

    def test_broken_manifest_does_not_crash_gui_catalog(self):
        write_pack(self.zip)
        install(self.zip, self.root)
        toggle(self.root, "audit-safe", True)
        manifest = self.root / "audit-safe/manifest.json"
        manifest.write_text('{"api":1,"id":"audit-safe","assets":"broken"}', encoding="utf-8")
        self.assertEqual(available_styles(self.root, "menus"), ["classic"])
        manifest.write_text('{"api":1,"id":"audit-safe","assets":[{"id":"menus/background","path":null}]}',
                            encoding="utf-8")
        self.assertEqual(available_styles(self.root, "menus"), ["classic"])

    def test_builtin_classic_name_is_reserved(self):
        write_pack(self.zip, pack_id="classic")
        with self.assertRaises(PackError):
            validate_zip(self.zip)

    def test_excess_resources_rollback_enable_without_destroying_index(self):
        write_pack(self.zip)
        install(self.zip, self.root)
        previous_catalog = (self.root / "runtime-assets.tsv").read_bytes()
        with patch.object(asset_catalog, "MAX_CATALOG_ASSETS", 0):
            with self.assertRaises(PackError):
                toggle(self.root, "audit-safe", True)
        self.assertEqual((self.root / "runtime-assets.tsv").read_bytes(), previous_catalog)
        self.assertEqual(list_packs(self.root)[0]["enabled"], False)

    def test_malformed_metadata_does_not_crash_list(self):
        write_pack(self.zip)
        install(self.zip, self.root)
        (self.root / "audit-safe/manifest.json").write_text("[]", encoding="utf-8")
        self.assertEqual(list_packs(self.root), [])


if __name__ == "__main__":
    unittest.main()
