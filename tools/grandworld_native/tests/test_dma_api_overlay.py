import unittest

from tools.grandworld_native.dma_api_overlay import transform

SAMPLE = (
    '#ifndef GUARD_GBA_MACRO_H\n#define GUARD_GBA_MACRO_H\n'
    '#define DmaSetUnchecked(dmaNum, src, dest, control) \\\n'
    '{ \\\n'
    '    vu32 *dmaRegs = (vu32 *)REG_ADDR_DMA##dmaNum; \\\n'
    '    dmaRegs[2] = (vu32)(control); \\\n'
    '    dmaRegs[2]; \\\n'
    '}'
    '\n\n#if MODERN\n// NOTE: Assumes 16-bit DMAs.'
    '\n#define DmaSet(dmaNum, src, dest, control) checked\n'
)

class DmaOverlayTests(unittest.TestCase):
    def test_only_world_native_overrides_macro(self):
        out = transform(SAMPLE)
        self.assertIn('#if defined(GW_WORLD_NATIVE)', out)
        self.assertIn('#define DMA_ENABLE 0x8000u', out)
        self.assertIn('GwNativeDmaSet((dmaNum), (const volatile void *)(uintptr_t)(src), (volatile void *)(uintptr_t)(dest), (control))', out)
        self.assertIn('#else\n#define DmaSetUnchecked', out)
        self.assertIn('#if MODERN\n// NOTE: Assumes 16-bit DMAs.', out)

    def test_anchor_drift_refused(self):
        with self.assertRaises(ValueError):
            transform(SAMPLE.replace('REG_ADDR_DMA##dmaNum', 'BROKEN'))
        with self.assertRaises(ValueError):
            transform(transform(SAMPLE))
        with self.assertRaises(ValueError):
            transform('missing implementation')

if __name__ == '__main__':
    unittest.main()
