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
extern u32 sampleRate;

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

    /* GBA BIOS RLE: first 4 bytes are header, then byte-wise packets.
     * These samples detect accidentally advancing the compressed cursor in
     * 32-bit words (which can corrupt tiles and other game resources). */
    {
        const u8 literal[] __attribute__((aligned(4))) =
            {0x30, 0x04, 0x00, 0x00, 0x03, 'A', 'B', 'C', 'D'};
        const u8 repeated[] __attribute__((aligned(4))) =
            {0x30, 0x04, 0x00, 0x00, 0x81, 'Z'};
        u8 wram_out[8] __attribute__((aligned(4))) = {0};
        u8 vram_out[8] __attribute__((aligned(4))) = {0};
        RLUnCompWram((const u32 *)literal, wram_out);
        if (memcmp(wram_out, "ABCD", 4) != 0)
            return failed(17, "RLE WRAM literal decoding skipped input bytes");
        RLUnCompVram((const u32 *)literal, vram_out);
        if (memcmp(vram_out, "ABCD", 4) != 0)
            return failed(18, "RLE VRAM literal decoding skipped input bytes");
        memset(wram_out, 0, sizeof(wram_out));
        RLUnCompWram((const u32 *)repeated, wram_out);
        if (memcmp(wram_out, "ZZZZ", 4) != 0)
            return failed(19, "RLE WRAM repeated-byte decoding incorrect");
    }

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

    /* 16-bit DMA from fixed source must fill every destination halfword. */
    {
        u16 value = 0xA53Fu;
        u16 result[8] = {0};
        DmaSet(3, &value, result,
               ((DMA_ENABLE | DMA_START_NOW | DMA_SRC_FIXED | DMA_DEST_INC) << 16) | 8);
        for (i = 0; i < 8; ++i)
            if (result[i] != value)
                return failed(11, "fixed-source 16-bit DMA fill incorrect");
    }

    /* Repeated VBlank DMA increments source and reloads the destination. */
    {
        u32 repeat_src[8] = {101,102,103,104,201,202,203,204};
        u32 repeat_dst[4] = {0};
        DmaSet(3, repeat_src, repeat_dst,
               ((DMA_ENABLE | DMA_REPEAT | DMA_START_VBLANK |
                 DMA_32BIT | DMA_SRC_INC | DMA_DEST_RELOAD) << 16) | 4);
        RunDMAs(DMA_VBLANK);
        if (repeat_dst[0] != 101 || repeat_dst[3] != 104)
            return failed(12, "first repeating DMA event incorrect");
        RunDMAs(DMA_VBLANK);
        if (repeat_dst[0] != 201 || repeat_dst[3] != 204)
            return failed(13, "DMA repeat did not reload destination");
    }

    /* Invalid DMA index must fail closed without copying or touching I/O. */
    memset(dma_dst, 0, sizeof(dma_dst));
    GwNativeDmaSet(-1, src, dma_dst, (DMA_ENABLE << 16) | 4);
    if (dma_dst[0] != 0)
        return failed(14, "negative DMA index affected memory");

    /* Each wave byte stores two amplitude nibbles; test the first and last. */
    cgb_audio_init(44100);
    for (i = 0; i < 16; ++i)
        GW_REG_BASE[REG_OFFSET_WAVE_RAM0 + i] = (u8)(0xF0u | (i & 0xF));
    cgb_set_wavram();
    if (gb.WAVRAM[0] < 0.99f || gb.WAVRAM[1] > -0.99f)
        return failed(9, "wave RAM nibble decoding incorrect");
    if (gb.WAVRAM[31] < 0.99f)
        return failed(10, "wave RAM final nibble decoding incorrect");
    cgb_audio_init(0);
    if (sampleRate == 0)
        return failed(15, "zero audio sample rate not normalized");
    gb.outBuffer[0] = 123.5f;
    cgb_audio_generate(MIXED_AUDIO_BUFFER_SIZE + 1);
    if (gb.outBuffer[0] != 123.5f)
        return failed(16, "oversized audio callback wrote outside validated range");


    puts("PASS: World BIOS RLE/memcopy, event/fill/repeat DMA, emulated I/O, wave/audio bounds");
    return 0;
}
