import tempfile
import unittest
from pathlib import Path
from tools.grandworld_native.build_pack import build_pack
from tools.grandworld_native.modpacks import PackError, validate_zip

class PackBuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.assets = self.root / "assets"
        (self.assets / "sprites").mkdir(parents=True)
        (self.assets / "sprites" / "demo.png").write_bytes(b"sample generated resource")
        self.output = self.root / "pack.zip"

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_and_validate(self):
        info = build_pack(self.assets, "example-pack", "1.0.0", self.output)
        self.assertTrue(info["validated"])
        self.assertEqual(validate_zip(self.output)["asset_count"], 1)

    def test_does_not_replace_existing_output(self):
        build_pack(self.assets, "example-pack", "1.0.0", self.output)
        saved = self.output.read_bytes()
        with self.assertRaises(PackError):
            build_pack(self.assets, "example-pack", "1.0.0", self.output)
        self.assertEqual(self.output.read_bytes(), saved)

    def test_rejects_code_file(self):
        (self.assets / "sprites" / "evil.py").write_text("print('no')")
        with self.assertRaises(PackError):
            build_pack(self.assets, "example-pack", "1.0.0", self.output)

    def test_rejects_wrong_folder(self):
        with self.assertRaises(PackError):
            build_pack(self.root, "example-pack", "1.0.0", self.output)

if __name__ == "__main__":
    unittest.main()
