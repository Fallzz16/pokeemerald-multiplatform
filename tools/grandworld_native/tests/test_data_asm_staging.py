"""P2: preserve original World data during charmap/preproc before host ASM."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools.grandworld_native.data_asm_staging import prepare, assemble, MANIFEST


@unittest.skipUnless(shutil.which("gcc"), "GNU C preprocessor/assembler required")
class OriginalGameDataStagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.world = Path(self.tmp.name) / "world"
        self.output = Path(self.tmp.name) / "host"
        (self.world / "tools/preproc").mkdir(parents=True)
        (self.world / "data").mkdir()
        (self.world / "charmap.txt").write_text("A = 0x41\n", encoding="utf-8")
        fake_preproc = self.world / "tools/preproc/preproc"
        # Test-only passthrough: the real pipeline ALWAYS invokes the pinned
        # World preprocessor binary, not this minimal fixture.
        fake_preproc.write_text(
            '#!/bin/sh\nif [ "$1" = "-s" ]; then cat "$2"; else cat; fi\n',
            encoding="utf-8")
        fake_preproc.chmod(0o755)
        self.original = self.world / "data/original.s"
        self.assembly = (".section .rodata\n.byte 0xA5\n"
                         ".align 3\n.word 0x12345678\n")
        self.original.write_text(self.assembly, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_original_preprocessor_runs_before_abi_conversion(self):
        staged = prepare(self.world, self.output)
        self.assertEqual(staged["prepared"], 1)
        self.assertEqual(self.original.read_text(), self.assembly)
        compiled = assemble(self.world, self.output)
        self.assertEqual(compiled["native_objects"], 1)
        self.assertTrue((self.output / "original.o").is_file())
        self.assertEqual(self.original.read_text(), self.assembly)
        self.assertFalse(compiled["game_data_fabricated"])

    def test_tampering_with_staged_original_is_rejected(self):
        prepare(self.world, self.output)
        original = self.output / "_original_preproc/original.s"
        original.write_bytes(original.read_bytes() + b".byte 0\n")
        with self.assertRaises(ValueError):
            assemble(self.world, self.output)

    def test_manifest_path_traversal_is_rejected(self):
        prepare(self.world, self.output)
        path = self.output / MANIFEST
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["records"][0]["source"] = "data/../out.s"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(ValueError):
            assemble(self.world, self.output)


if __name__ == "__main__":
    unittest.main()
