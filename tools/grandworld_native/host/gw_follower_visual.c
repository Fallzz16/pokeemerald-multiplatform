#include "gw_follower_visual.h"
#include <stdint.h>

static int64_t magnitude(int x)
{
    return x < 0 ? -(int64_t)x : (int64_t)x;
}

GWFace8 gw_follower_look_at(int dx, int dy, GWFace8 previous, int deadzone)
{
    const int64_t x = magnitude(dx);
    const int64_t y = magnitude(dy);
    if (previous < GW_FACE_N || previous >= GW_FACE_COUNT)
        previous = GW_FACE_S;
    if (deadzone < 0)
        deadzone = 0;
    if (x <= deadzone && y <= deadzone)
        return previous;
    if (x * 2 <= y)
        return dy < 0 ? GW_FACE_N : GW_FACE_S;
    if (y * 2 <= x)
        return dx < 0 ? GW_FACE_W : GW_FACE_E;
    if (dy < 0)
        return dx < 0 ? GW_FACE_NW : GW_FACE_NE;
    return dx < 0 ? GW_FACE_SW : GW_FACE_SE;
}

const char *gw_follower_direction_name(GWFace8 facing)
{
    static const char *const names[] = {"N", "NE", "E", "SE", "S", "SW", "W", "NW"};
    return facing >= 0 && facing < GW_FACE_COUNT ? names[facing] : "S";
}
