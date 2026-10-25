"""P2: host-only replacements for ARM instructions do not alter GBA paths."""
import unittest
from tools.grandworld_native.arm_runtime_overlay import (
    RANDOM_START, RANDOM_END, MBOOT_START, MBOOT_END, M4A_ORIGINAL,
    transform_random, transform_multiboot, transform_m4a,
)


class ArmNativeFallbackTests(unittest.TestCase):
    def test_rng_uses_existing_sfc32_c_core(self):
        original = (
            RANDOM_START + '\n    asm(".thumb\\n\\\\n bx lr");\n}\n' +
            RANDOM_END + '\n    return Random32Core();\n}\n'
        )
        adapted = transform_random(original)
        self.assertIn('_SFC32_Next_Stream(&gRngValue, STREAM1)', adapted)
        self.assertIn('#else\n' + RANDOM_START, adapted)
        self.assertIn('asm(".thumb', adapted)
        with self.assertRaises(ValueError):
            transform_random(adapted)

    def test_multiboot_does_not_claim_supported_transport(self):
        original = (MBOOT_START + '\n    asm_unified("bx lr");\n}\n' +
                    MBOOT_END + '\n}\n')
        adapted = transform_multiboot(original)
        self.assertIn('MultiBootWaitCycles(u32 cycles)', adapted)
        self.assertIn('#else\n' + MBOOT_START, adapted)
        self.assertIn('asm_unified("bx lr")', adapted)
        with self.assertRaises(ValueError):
            transform_multiboot(adapted)

    def test_unused_gba_swi_remains_gba_only(self):
        adapted = transform_m4a(M4A_ORIGINAL)
        self.assertIn('#if !defined(GW_WORLD_NATIVE)', adapted)
        self.assertIn('asm("swi 0x2A");', adapted)
        with self.assertRaises(ValueError):
            transform_m4a(adapted)

    def test_missing_original_arm_sources_rejected(self):
        for transform in (transform_random, transform_multiboot, transform_m4a):
            with self.assertRaises(ValueError):
                transform('Source has changed')


if __name__ == '__main__':
    unittest.main()
