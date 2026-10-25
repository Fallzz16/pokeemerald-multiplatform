#include "global.h"
#include "platform/dma.h"
#include <stdio.h>
#include <string.h>

#if defined(GW_WORLD_NATIVE)
/* The modern World header's DmaSet macro directly writes GBA registers.
 * This backend provides the function which also records host pointers. */
#ifdef DmaSet
#undef DmaSet
#endif
#ifndef DMA_DEST_MASK
#define DMA_DEST_MASK (DMA_DEST_DEC | DMA_DEST_FIXED)
#endif
#ifndef DMA_SRC_MASK
#define DMA_SRC_MASK (DMA_SRC_DEC | DMA_SRC_FIXED)
#endif
#ifndef DBGPRINTF
#define DBGPRINTF(...) fprintf(stderr, __VA_ARGS__)
#endif
#endif

struct DMATransfer {
    union {
        const void *src;
        const u16 *src16;
        const u32 *src32;
    };
    union {
        void *dst;
        vu16 *dst16;
        vu32 *dst32;
    };
    u32 size;
    u16 control;
} DMAList[DMA_COUNT];

void RunDMAs(u32 type)
{
    for (int dmaNum = 0; dmaNum < DMA_COUNT; dmaNum++)
    {
        struct DMATransfer *dma = &DMAList[dmaNum];
        u32 dmaCntReg = (&REG_DMA0CNT)[dmaNum * 3];
        if (!((dmaCntReg >> 16) & DMA_ENABLE))
        {
            dma->control &= ~DMA_ENABLE;
        }
        
        if ( (dma->control & DMA_ENABLE) &&
           (((dma->control & DMA_START_MASK) >> 12) == type))
        {
            //printf("DMA%d src=%p, dest=%p, control=%d\n", dmaNum, dma->src, dma->dest, dma->control);
            for (int i = 0; i < (dma->size); i++)
            {
                if ((dma->control) & DMA_32BIT)
                     *dma->dst32 = *dma->src32;
                else *dma->dst16 = *dma->src16;

                // process destination pointer changes
                if (((dma->control) & DMA_DEST_MASK) == DMA_DEST_INC)
                {
                    if ((dma->control) & DMA_32BIT)
                            dma->dst32++;
                    else    dma->dst16++;
                }
                else if (((dma->control) & DMA_DEST_MASK) == DMA_DEST_DEC)
                {
                    if ((dma->control) & DMA_32BIT)
                            dma->dst32--;
                    else    dma->dst16--;
                }
                else if (((dma->control) & DMA_DEST_MASK) == DMA_DEST_RELOAD) // TODO
                {
                    if ((dma->control) & DMA_32BIT)
                            dma->dst32++;
                    else    dma->dst16++;
                }

                // process source pointer changes
                if (((dma->control) & DMA_SRC_MASK) == DMA_SRC_INC)
                {
                    if ((dma->control) & DMA_32BIT)
                            dma->src32++;
                    else    dma->src16++;
                }
                else if (((dma->control) & DMA_SRC_MASK) == DMA_SRC_DEC)
                {
                    if ((dma->control) & DMA_32BIT)
                            dma->src32--;
                    else    dma->src16--;
                }
            }

            if (dma->control & DMA_REPEAT)
            {
                dma->size = ((&REG_DMA0CNT)[dmaNum * 3] & 0x1FFFF);
                if (((dma->control) & DMA_DEST_MASK) == DMA_DEST_RELOAD)
                {
                    dma->dst = (void *)(uintptr_t)((&REG_DMA0DAD)[dmaNum * 3]);
                }
            }
            else
            {
                dma->control &= ~DMA_ENABLE;
            }
        }
    }
}

void DmaSet(int dmaNum, const void *src, void *dest, u32 control)
{
    if (dmaNum < 0 || dmaNum >= DMA_COUNT)
    {
        DBGPRINTF("DmaSet with invalid DMA number: dmaNum=%d, src=%p, dest=%p, control=%d\n", dmaNum, src, dest, control);
        return;
    }

    (&REG_DMA0SAD)[dmaNum * 3] = (vu32)(uintptr_t)src;
    (&REG_DMA0DAD)[dmaNum * 3] = (vu32)(uintptr_t)dest;
    (&REG_DMA0CNT)[dmaNum * 3] = control;

    struct DMATransfer *dma = &DMAList[dmaNum];
    dma->src = src;
    dma->dst = dest;
    dma->size = control & 0x1ffff;
    dma->control = control >> 16;

    RunDMAs(DMA_NOW);
}
#if defined(GW_WORLD_NATIVE)
/* World MODERN's checked DmaSet macro routes through this symbol when the
 * disposable native-only header overlay is enabled. The original GBA macro
 * and its alignment assertions remain unchanged for GBA builds. */
void GwNativeDmaSet(int dmaNum, const void *src, void *dest, u32 control)
{
    DmaSet(dmaNum, src, dest, control);
}
#endif
