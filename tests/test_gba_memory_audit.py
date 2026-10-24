"""Unit-test ARM memory report parsing without requiring cross-compilers."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "kanto"))
import gba_memory_audit


class GbaMemoryAuditTests(unittest.TestCase):
    def test_extract_bss_and_common_only(self):
        data = (
            "build/modern/src/main.o:00000000 00000128 B gSaveBuffer\n"
            "build/modern/src/music_player.o:00000000 00000512 b sAudioState\n"
            "build/modern/src/other.o:00000000 00000064 C gStaticCommon\n"
            "build/modern/src/test.o:00000000 00001234 T testFunc\n"
            "build/modern/src/test.o:00000000 00000000 B empty\n"
        )
        rows = gba_memory_audit.parse_nm(data)
        self.assertEqual([r["bytes"] for r in rows], [128, 512, 64])
        self.assertEqual([r["kind"] for r in rows], ["B", "B", "C"])
        self.assertEqual(rows[0]["symbol"], "gSaveBuffer")

    def test_no_objects_is_honest(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            report = gba_memory_audit.inspect(temp, "does-not-need-to-exist")
            self.assertEqual(report["objects_scanned"], 0)
            self.assertEqual(report["sum_bss_and_common_symbol_bytes"], 0)
            self.assertEqual(report["largest"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
