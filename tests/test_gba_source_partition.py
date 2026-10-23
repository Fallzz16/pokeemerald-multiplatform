"""Guard the GBA/desktop source split without compiling ROMs or touching saves."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GbaSourcePartition(unittest.TestCase):
    def test_gba_makefile_filters_native_platform_bios(self):
        source = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn(
            "C_SRCS_IN := $(filter-out $(GBA_NATIVE_ONLY_C),",
            source,
            "Desktop BIOS and POSIX save profiles must not appear in GBA source objects")
        for excluded in (
            "$(C_SUBDIR)/platform/%.c",
            "$(C_SUBDIR)/profile/%.c",
            "$(C_SUBDIR)/lnet/%.c",
            "$(C_SUBDIR)/sound_mixer.c",
            "$(C_SUBDIR)/stub.c",
        ):
            with self.subTest(excluded=excluded):
                self.assertIn(excluded, source)
        self.assertIn("$(C_SUBDIR)/*/*/*.c)", source)
        self.assertIn("C_ASM_SRCS := $(wildcard", source)
        self.assertIn("$(C_SUBDIR)/*.s", source)

    def test_desktop_makefile_still_compiles_portable_platform(self):
        source = (ROOT / "Makefile_pc").read_text(encoding="utf-8")
        self.assertIn(
            "C_SRCS_IN := $(wildcard $(C_SUBDIR)/*.c $(C_SUBDIR)/*/*.c",
            source,
            "The native port needs the desktop BIOS simulator")
        self.assertNotIn(
            "C_SRCS_IN := $(filter-out $(C_SUBDIR)/platform/",
            source)

    def test_mp2k_gba_uses_assembly_for_conflicting_symbols(self):
        source = (ROOT / "src/music_player.c").read_text(encoding="utf-8")
        for name in (
            "umul3232H32", "SoundMainBTM", "MPlayJumpTableCopy",
            "TrackStop", "m4aSoundVSync",
        ):
            with self.subTest(symbol=name):
                self.assertIn(" " + name + "(", source)
        self.assertEqual(source.count("#endif // PORTABLE: GBA has this symbol"), 5)
        self.assertIn("void MP2KPlayerMain(void *voidPtrPlayer)", source)
        self.assertIn("#ifdef PORTABLE\\nfloat audioBuffer", source)
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertNotIn("GBA_NATIVE_ONLY_C += $(C_SUBDIR)/music_player.c", makefile)

    def test_audio_rules_have_fallback_assembler_filter(self):
        source = (ROOT / "audio_rules.mk").read_text(encoding="utf-8")
        self.assertIn("ASM_PSEUDO_OP_CONV ?= cat", source)
        self.assertIn("FIX_UNDERSCORE ?= true", source)
        self.assertIn("$(ASM_PSEUDO_OP_CONV) $< | $(AS)", source)

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
