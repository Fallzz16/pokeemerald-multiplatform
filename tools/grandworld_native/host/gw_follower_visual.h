#ifndef GW_FOLLOWER_VISUAL_H
#define GW_FOLLOWER_VISUAL_H

typedef enum {
    GW_FACE_N, GW_FACE_NE, GW_FACE_E, GW_FACE_SE,
    GW_FACE_S, GW_FACE_SW, GW_FACE_W, GW_FACE_NW,
    GW_FACE_COUNT
} GWFace8;

/* Screen-coordinate deltas: +x right, +y down.
 * Does not modify grid movement or collision.
 * Last valid direction is preserved near the player to prevent flicker.
 */
GWFace8 gw_follower_look_at(int dx, int dy, GWFace8 previous, int deadzone);
const char *gw_follower_direction_name(GWFace8 facing);

#endif
