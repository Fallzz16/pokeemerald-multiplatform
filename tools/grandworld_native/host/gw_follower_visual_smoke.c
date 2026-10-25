#include "gw_follower_visual.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    assert(gw_follower_look_at(0, -40, GW_FACE_S, 4) == GW_FACE_N);
    assert(gw_follower_look_at(30, -25, GW_FACE_S, 4) == GW_FACE_NE);
    assert(gw_follower_look_at(40, 0, GW_FACE_S, 4) == GW_FACE_E);
    assert(gw_follower_look_at(20, 20, GW_FACE_S, 4) == GW_FACE_SE);
    assert(gw_follower_look_at(0, 40, GW_FACE_N, 4) == GW_FACE_S);
    assert(gw_follower_look_at(-20, 20, GW_FACE_S, 4) == GW_FACE_SW);
    assert(gw_follower_look_at(-40, 0, GW_FACE_S, 4) == GW_FACE_W);
    assert(gw_follower_look_at(-20, -20, GW_FACE_S, 4) == GW_FACE_NW);
    assert(gw_follower_look_at(2, -2, GW_FACE_E, 4) == GW_FACE_E);
    assert(gw_follower_look_at(0, 0, (GWFace8)100, 4) == GW_FACE_S);
    assert(gw_follower_look_at(-2147483647, -2147483647, GW_FACE_S, 4) == GW_FACE_NW);
    puts("PASS: four-axis follower movement compatible with eight visual facings");
    return 0;
}
