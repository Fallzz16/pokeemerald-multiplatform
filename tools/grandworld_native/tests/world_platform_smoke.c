/* Executable World-native BIOS/DMA/audio and memory smoke tests.
 * Compile against the patched World headers in CI (after the GBA baseline).
 * NO game save file is opened; neither an emulator nor gameplay is implied.
 */
#include "global.h"
#include "platform/dma.h"
#include "cgb_audio.h"
#include <stdio.h>
#include <string.h>

/* The legacy CGB audio implementation owns this state; the test observes it. */
extern struct AudioCGB gb;

static int failed(int code, const char *message)
{
    fprintf(stderr, "FAIL %d: %s\n", code, message);
    return code;
}

int main(void)
{
    u32 src[8] = {0x12345678u, 0x9abcdef0u, 3, 4, 5, 6, 7, 8};
    u32 dst[8] = {0};
    u32 dma_dst[8] = {0};
    u16 fill_src = 0xb33f;
    u16 fill_dst[4] = {0};
    u32 fast_dst[8] = {0};
    unsigned i;

    /* Real World memory-mapped registers are virtual buffers on the host. */
    if (sizeof(GW_REG_BASE) != 0x400 ||
        sizeof(GW_PLTT) != PLTT_SIZE ||
        sizeof(VRAM_) != VRAM_SIZE ||
        sizeof(GW_OAM) != OAM_SIZE)
        return failed(1, "incorrect host register/VRAM/OAM/palette capacity");
    GW_REG_BASE[REG_OFFSET_WAVE_RAM0] = 0xF0;
    if (*(volatile u8 *)(uintptr_t)REG_ADDR_WAVE_RAM0 != 0xF0)
        return failed(2, "wave register address not mapped");

    CpuSet(src, dst, CPU_SET_32BIT | 8);
    if (memcmp(src, dst, sizeof(src)) != 0)
        return failed(3, "CpuSet 32-bit copy incorrect");
    CpuSet(&fill_src, fill_dst, CPU_SET_SRC_FIXED | 4);
    for (i = 0; i < 4; i++)
        if (fill_dst[i] != fill_src)
            return failed(4, "CpuSet 16-bit fill incorrect");
    CpuFastSet(src, fast_dst, 8);
    if (memcmp(src, fast_dst, sizeof(src)) != 0)
        return failed(5, "CpuFastSet 32-byte copy incorrect");

    /* Calls the unchanged World-checked DmaSet macro; the portable adapter
     * routes it to the native implementation instead of unhandled registers. */
    DmaSet(3, src, dma_dst,
           ((DMA_ENABLE | DMA_START_NOW | DMA_32BIT | DMA_SRC_INC | DMA_DEST_INC) << 16) | 8);
    if (memcmp(src, dma_dst, sizeof(src)) != 0)
        return failed(6, "DMA immediate 32-bit transfer not performed");
    memset(dma_dst, 0, sizeof(dma_dst));
    DmaSet(3, src, dma_dst,
           ((DMA_ENABLE | DMA_START_VBLANK | DMA_32BIT | DMA_SRC_INC | DMA_DEST_INC) << 16) | 8);
    if (dma_dst[0] != 0)
        return failed(7, "VBlank DMA executed before event");
    RunDMAs(DMA_VBLANK);
    if (memcmp(src, dma_dst, sizeof(src)) != 0)
        return failed(8, "VBlank DMA failed");

    /* Each wave byte stores two amplitude nibbles; test the first and last. */
    cgb_audio_init(44100);
    for (i = 0; i < 16; ++i)
        GW_REG_BASE[REG_OFFSET_WAVE_RAM0 + i] = (u8)(0xF0u | (i & 0xF));
    cgb_set_wavram();
    if (gb.WAVRAM[0] < 0.99f || gb.WAVRAM[1] > -0.99f)
        return failed(9, "wave RAM nibble decoding incorrect");
    if (gb.WAVRAM[31] < 0.99f)
        return failed(10, "wave RAM final nibble decoding incorrect");

    puts("PASS: World portable BIOS, DMA NOW/VBlank, 4 hardware buffers, wave RAM");
    return 0;
}
