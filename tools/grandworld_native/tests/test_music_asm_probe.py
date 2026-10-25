"""P2: original generated MIDI data is required, never replaced by fake songs."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.grandworld_native import music_asm_probe


class NativeWorldMusicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.world = Path(self.tmp.name) / "world"
        self.folder = self.world / "sound/songs/midi"
        self.folder.mkdir(parents=True)
        self.outputs = Path(self.tmp.name) / "objects"
        (self.folder / "mus_a.mid").write_bytes(b"MThd fixture only")
        (self.folder / "mus_b.mid").write_bytes(b"MThd fixture only")

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_generated_song_is_never_silently_accepted(self):
        self.outputs.mkdir()
        (self.outputs / "mus_a.o").write_bytes(b"stale object")
        with patch.object(music_asm_probe.shutil, "which", return_value="gcc"), \
             patch.object(music_asm_probe.subprocess, "run") as runner:
            outcome = music_asm_probe.inspect(self.world, self.outputs, limit=1)
        self.assertEqual(outcome["compiled"], 0)
        self.assertEqual(outcome["results"][0]["status"],
                         "missing_generated_midi_assembly")
        self.assertFalse((self.outputs / "mus_a.o").exists())
        runner.assert_not_called()

    def test_authentic_asm_is_host_transformed_without_changing_midi(self):
        sample = ".section .rodata\n.align 2\n.globl mus_a\nmus_a:\n.word 0x12345678\n"
        (self.folder / "mus_a.s").write_text(sample, encoding="utf-8")
        untouched = (self.folder / "mus_a.mid").read_bytes()
        observed = []
        def fake_assemble(cmd, **kwargs):
            observed.append(kwargs["input"].decode())
            Path(cmd[-1]).write_bytes(b"fixture 32-bit object")
            return subprocess.CompletedProcess(cmd, 0, b"", b"")
        with patch.object(music_asm_probe.shutil, "which", return_value="gcc"), \
             patch.object(music_asm_probe.subprocess, "run", side_effect=fake_assemble):
            data = music_asm_probe.inspect(self.world, self.outputs, limit=1)
        self.assertEqual(data["compiled"], 1)
        self.assertTrue(data["results"][0]["native_object"])
        self.assertIn(".p2align 2", observed[0])
        self.assertIn(".4byte 0x12345678", observed[0])
        self.assertEqual((self.folder / "mus_a.mid").read_bytes(), untouched)
        self.assertEqual((self.folder / "mus_a.s").read_text(), sample)

    def test_invalid_request_size_fails_closed(self):
        for limit in (0, -1, 1001):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                music_asm_probe.inspect(self.world, self.outputs, limit=limit)


if __name__ == "__main__":
    unittest.main()
