#include "lnet_culling.h"
#include <assert.h>
#include <stdio.h>

#define VW 240
#define VH 160

int main(void)
{
    /* Overlapping, partially outside, exactly on viewport edges. */
    assert(lnet_culling_intersects(0, 0, 16, 32, VW, VH, 0));
    assert(lnet_culling_intersects(224, 130, 16, 32, VW, VH, 0));
    assert(lnet_culling_intersects(-15, -31, 16, 32, VW, VH, 0));
    assert(!lnet_culling_intersects(-16, 0, 16, 32, VW, VH, 0));
    assert(!lnet_culling_intersects(240, 0, 16, 32, VW, VH, 0));
    assert(!lnet_culling_intersects(0, -32, 16, 32, VW, VH, 0));
    assert(!lnet_culling_intersects(0, 160, 16, 32, VW, VH, 0));

    /* Preload near the camera while keeping the sprite invisible. */
    assert(lnet_culling_intersects(-40, 40, 16, 32, VW, VH, 32));
    assert(!lnet_culling_intersects(-49, 40, 16, 32, VW, VH, 32));
    assert(lnet_culling_intersects(260, 60, 16, 32, VW, VH, 32));
    assert(!lnet_culling_intersects(272, 60, 16, 32, VW, VH, 32));

    /* Retention band > preload band (hysteresis) avoids repeated allocation. */
    assert(lnet_culling_intersects(-63, 40, 16, 32, VW, VH, 48));
    assert(!lnet_culling_intersects(-65, 40, 16, 32, VW, VH, 48));

    /* Input validation: malformed sprite and viewport geometries. */
    assert(!lnet_culling_intersects(0, 0, 0, 32, VW, VH, 0));
    assert(!lnet_culling_intersects(0, 0, 16, -3, VW, VH, 0));
    assert(!lnet_culling_intersects(0, 0, 16, 32, 0, VH, 0));
    assert(!lnet_culling_intersects(0, 0, 16, 32, VW, VH, -1));
    puts("passed: pixel-exact viewport culling and 32/48 px hysteresis");
    return 0;
}
