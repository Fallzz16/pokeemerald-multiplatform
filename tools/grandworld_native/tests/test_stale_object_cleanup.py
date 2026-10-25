"""P2: link diagnostics must never silently use a stale native game object."""
from pathlib import Path
import tempfile
import unittest

from tools.grandworld_native import engine_probe, data_asm_probe


class NativeObjectFreshnessTests(unittest.TestCase):
    def test_failed_engine_translation_unit_cannot_leave_old_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src/main.c").write_text("int broken( = 0;\n", encoding="utf-8")
            output = root / "native"
            output.mkdir()
            (output / "main.o").write_bytes(b"STALE LINK OBJECT")
            (output / "main.s").write_text("STALE ASSEMBLY", encoding="utf-8")
            data = engine_probe.compile_engine(
                root, output, compiler="missing-gw-test-compiler",
                use_preproc=False, all_sources=True)
            self.assertEqual(data["compiled"], 0)
            self.assertFalse((output / "main.o").exists())
            self.assertFalse((output / "main.s").exists())

    def test_failed_original_asset_preproc_cannot_leave_old_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tools/preproc").mkdir(parents=True)
            preproc = root / "tools/preproc/preproc"
            preproc.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            preproc.chmod(0o755)
            (root / "charmap.txt").write_text("A = 0x41\n", encoding="utf-8")
            (root / "data").mkdir()
            (root / "data/real.s").write_text(".byte 4\n", encoding="utf-8")
            output = root / "native"
            output.mkdir()
            (output / "real.o").write_bytes(b"STALE ASSET OBJECT")
            result = data_asm_probe.inspect(root, output, limit=1)
            self.assertEqual(result["native_objects"], 0)
            self.assertEqual(result["results"][0]["status"], "charmap_stage1_failed")
            self.assertFalse((output / "real.o").exists())


if __name__ == "__main__":
    unittest.main()
