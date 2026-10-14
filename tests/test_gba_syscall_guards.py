"""Guard the legacy agbcc vs MODERN macro boundary for GBA BIOS calls.

Runs without building a ROM or opening personal saves. The GitHub CI
still runs an actual agbcc ROM compilation after this lightweight check.
"""
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "include" / "gba" / "syscall.h"
TEST_SOURCE = """\
typedef unsigned int u32;
typedef unsigned short u16;
typedef signed short s16;
typedef signed int s32;
struct BgAffineSrcData;
struct BgAffineDstData;
struct ObjAffineSrcData;
struct ObjAffineDstData;
struct MultiBootParam;
#include "gba/syscall.h"
void check_bios_calls(void) {
    u32 source = 0, target = 0;
    CpuSet(&source, &target, 0);
    CpuFastSet(&source, &target, 0);
}
"""


class GbaSyscallGuards(unittest.TestCase):
    def test_only_modern_nonportable_uses_alignment_assertions(self):
        text = HEADER.read_text(encoding="utf-8")
        guard = "#if defined(MODERN) && MODERN && !defined(PORTABLE)"
        self.assertEqual(text.count(guard), 2)
        self.assertNotIn("#if defined MODERN && !defined PORTABLE", text)

    def test_legacy_and_modern_header_compilation(self):
        cc = os.environ.get("CC", "cc")
        if not shutil.which(cc):
            self.skipTest("No host C compiler; full agbcc verification belongs to CI.")
        for name, flags, std in (
            ("legacy_agbcc_mode", ["-DMODERN=0"], "gnu89"),
            ("modern_gba_mode", ["-DMODERN=1"], "gnu11"),
            ("modern_portable_mode", ["-DMODERN=1", "-DPORTABLE=1"], "gnu11"),
        ):
            with self.subTest(name=name):
                command = [cc, "-x", "c", "-fsyntax-only", "-Werror",
                           "-std=" + std, "-I", str(ROOT / "include"),
                           *flags, "-"]
                completed = subprocess.run(
                    command, cwd=ROOT, input=TEST_SOURCE,
                    capture_output=True, text=True, timeout=15, check=False
                )
                self.assertEqual(completed.returncode, 0,
                                 completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
