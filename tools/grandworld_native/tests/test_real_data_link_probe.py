import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.grandworld_native.real_data_link_probe import analyze


@unittest.skipUnless(shutil.which("gcc") and shutil.which("nm"),
                     "requires GCC and nm")
class OriginalDataLinkProbeTests(unittest.TestCase):
    def test_genuine_data_resolves_code_dependency_but_is_not_executable(self):
        with tempfile.TemporaryDirectory() as root:
            parent = Path(root)
            code = parent / "code"
            data = parent / "data"
            code.mkdir()
            data.mkdir()
            (parent / "engine.c").write_text(
                "extern const unsigned char gGameText[];\n"
                "unsigned char GwReadActualData(void) {return gGameText[0];}\n",
                encoding="utf-8")
            (parent / "original.s").write_text(
                ".section .rodata\n.globl gGameText\ngGameText:\n.byte 88,89\n",
                encoding="utf-8")
            for cmd in (
                ["gcc", "-m32", "-c", str(parent / "engine.c"),
                 "-o", str(code / "engine.o")],
                ["gcc", "-m32", "-c", str(parent / "original.s"),
                 "-o", str(data / "original.o")],
            ):
                subprocess.run(cmd, check=True, capture_output=True)
            result = analyze(code, data, parent / "link.json")
            self.assertTrue(result["partial_linked"], result.get("diagnostics"))
            self.assertIn("gGameText", result["resolved_by_original_data"])
            self.assertFalse(result["game_executable_linked"])
            self.assertFalse(result["gameplay_verified"])
            self.assertTrue(result["all_objects_from_real_source"])
            self.assertFalse(result["dummy_symbols_inserted"])

    def test_missing_real_data_never_claims_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "code").mkdir()
            (root / "data").mkdir()
            result = analyze(root / "code", root / "data", root / "report.json")
            self.assertFalse(result["partial_linked"])
            self.assertFalse(result["game_executable_linked"])
            self.assertIn("No native engine", result["error"])


if __name__ == "__main__":
    unittest.main()
