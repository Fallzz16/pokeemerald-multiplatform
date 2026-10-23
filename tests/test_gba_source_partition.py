"""Guard the GBA/desktop source split without compiling ROMs or touching saves."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GbaSourcePartition(unittest.TestCase):
    def test_gba_makefile_filters_native_platform_bios(self):
        source = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn(
            "C_SRCS_IN := $(filter-out $(C_SUBDIR)/platform/%.c $(C_SUBDIR)/profile/%.c,",
            source,
            "Desktop BIOS and POSIX save profiles must not appear in GBA source objects")
        self.assertIn("$(C_SUBDIR)/*/*/*.c)", source)

    def test_desktop_makefile_still_compiles_portable_platform(self):
        source = (ROOT / "Makefile_pc").read_text(encoding="utf-8")
        self.assertIn(
            "C_SRCS_IN := $(wildcard $(C_SUBDIR)/*.c $(C_SUBDIR)/*/*.c",
            source,
            "The native port needs the desktop BIOS simulator")
        self.assertNotIn(
            "C_SRCS_IN := $(filter-out $(C_SUBDIR)/platform/",
            source)

    def test_native_profile_uses_host_filesystem_api(self):
        source = (ROOT / "src/profile/save_profiles.c").read_text(encoding="utf-8")
        self.assertIn("#include <dirent.h>", source)
        self.assertIn("flock(", source)

    def test_bios_is_desktop_only_implementation(self):
        bios = (ROOT / "src/platform/bios.c").read_text(encoding="utf-8")
        self.assertIn("u16 INTR_CHECK;", bios)
        self.assertIn("void CpuSet(", bios)
        self.assertIn("void CpuFastSet(", bios)


if __name__ == "__main__":
    unittest.main(verbosity=2)
