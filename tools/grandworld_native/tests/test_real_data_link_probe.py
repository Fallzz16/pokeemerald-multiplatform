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

    def test_real_original_midi_object_is_linked_without_fake_symbols(self):
        with tempfile.TemporaryDirectory() as root:
            parent = Path(root)
            code, data, songs = (parent / name for name in ("code", "data", "music"))
            for folder in (code, data, songs):
                folder.mkdir()
            (parent / "engine.c").write_text(
                "extern const unsigned char gGameText[], gOriginalSong[];\n"
                "int GwReadMusic(void) {return gGameText[0] + gOriginalSong[0];}\n",
                encoding="utf-8")
            (parent / "data.s").write_text(
                ".section .rodata\n.globl gGameText\ngGameText:\n.byte 1\n",
                encoding="utf-8")
            (parent / "song.s").write_text(
                ".section .rodata\n.globl gOriginalSong\ngOriginalSong:\n.byte 2\n",
                encoding="utf-8")
            for source, target in (
                ("engine.c", code / "engine.o"),
                ("data.s", data / "data.o"),
                ("song.s", songs / "song.o"),
            ):
                subprocess.run(["gcc", "-m32", "-c", str(parent / source),
                                "-o", str(target)], check=True, capture_output=True)
            result = analyze(code, data, parent / "music-link.json",
                             music_objects=songs)
            self.assertTrue(result["partial_linked"], result.get("diagnostics"))
            self.assertEqual(result["music_object_count"], 1)
            self.assertTrue(result["original_music_objects_supplied"])
            self.assertIn("gGameText", result["resolved_by_original_data"])
            self.assertIn("gOriginalSong", result["resolved_by_original_data"])
            self.assertFalse(result["game_executable_linked"])

    def test_music_requested_without_real_objects_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            parent = Path(root)
            for name in ("code", "data", "music"):
                (parent / name).mkdir()
            (parent / "code" / "main.o").write_bytes(b"unit-test-only")
            (parent / "data" / "scripts.o").write_bytes(b"unit-test-only")
            report = analyze(parent / "code", parent / "data",
                             parent / "report.json", music_objects=parent / "music")
            self.assertFalse(report["partial_linked"])
            self.assertEqual(report["error"], "No original MIDI objects successfully assembled")
            self.assertEqual(report["music_object_count"], 0)

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
