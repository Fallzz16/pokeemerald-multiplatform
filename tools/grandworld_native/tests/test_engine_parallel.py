"""Parallel real-World compile orchestration, deterministic failure handling.

The fixtures create fake translation units ONLY for testing the build system;
the production probe always compiles original World/M8 source files.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.grandworld_native import engine_probe


class WorldCompilerSchedulingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "world"
        self.objects = Path(self.temp.name) / "obj"
        (self.root / "src").mkdir(parents=True)
        (self.root / "include").mkdir()
        for name in ("z.c", "b.c", "a.c"):
            (self.root / "src" / name).write_text("int fixture(void) { return 0; }\n",
                                                  encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def fake_compile(self, _compiler, _world, src, obj, _flags, _preproc):
        obj.write_bytes(b"fake-test-object")
        if src.name == "b.c":
            return subprocess.CompletedProcess([], 1, b"", b"test failure: broken symbol")
        return subprocess.CompletedProcess([], 0, b"", b"")

    def test_parallel_preserves_order_and_removes_failed_object(self):
        self.objects.mkdir()
        # A failed build must never reuse an older compiled symbol.
        (self.objects / "b.o").write_bytes(b"stale")
        with patch.object(engine_probe, "SOURCES", ("z.c", "b.c", "a.c")), \
             patch.object(engine_probe, "_native_compile", side_effect=self.fake_compile), \
             patch.object(engine_probe.shutil, "which", return_value="/usr/bin/gcc"):
            report = engine_probe.compile_engine(self.root, self.objects, jobs=3)
        self.assertEqual([e["source"] for e in report["objects"]],
                         ["src/z.c", "src/b.c", "src/a.c"])
        self.assertEqual(report["compiled"], 2)
        self.assertEqual(report["requested"], 3)
        self.assertEqual(report["compiler_jobs"], 3)
        self.assertFalse((self.objects / "b.o").exists())
        self.assertTrue((self.objects / "z.o").exists())
        self.assertTrue((self.objects / "a.o").exists())
        self.assertEqual(report["objects"][1]["bytes"], 0)

    def test_single_worker_same_deterministic_results(self):
        with patch.object(engine_probe, "SOURCES", ("z.c", "b.c", "a.c")), \
             patch.object(engine_probe, "_native_compile", side_effect=self.fake_compile), \
             patch.object(engine_probe.shutil, "which", return_value="/usr/bin/gcc"):
            report = engine_probe.compile_engine(self.root, self.objects, jobs=1)
        self.assertEqual(report["compiled"], 2)
        self.assertEqual(report["objects"][1]["status"], "failed")
        self.assertFalse((self.objects / "b.o").exists())

    def test_worker_bounds_and_duplicate_sources_are_refused(self):
        for count in (-1, 0, 9):
            with self.subTest(count=count), self.assertRaises(ValueError):
                engine_probe.compile_engine(self.root, self.objects, jobs=count)
        with patch.object(engine_probe, "SOURCES", ("z.c", "z.c")), \
             self.assertRaises(ValueError):
            engine_probe.compile_engine(self.root, self.objects, jobs=2)

    def test_missing_source_removes_stale_object(self):
        self.objects.mkdir()
        (self.objects / "missing.o").write_bytes(b"old-code")
        with patch.object(engine_probe, "SOURCES", ("missing.c",)), \
             patch.object(engine_probe.shutil, "which", return_value="/usr/bin/gcc"):
            report = engine_probe.compile_engine(self.root, self.objects, jobs=2)
        self.assertEqual(report["objects"][0]["status"], "source_missing")
        self.assertFalse((self.objects / "missing.o").exists())


if __name__ == "__main__":
    unittest.main()
