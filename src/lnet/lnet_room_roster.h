#ifndef GUARD_LNET_ROOM_ROSTER_H
#define GUARD_LNET_ROOM_ROSTER_H
/* Strict decoder for EHL8 PLAYER_LIST, reusing the EXISTING wire format.
 * Never persists trainer identities, names or saves. A malformed frame is
 * rejected instead of driving a misleading 2/2 ready UI.
 *
 * PLAYER_LIST: count:u8, then [slot:u8, ready:u8, length:u8, id:bytes].
 * The host currently supports exactly two slots. This module is pure C.
 */
#include <stddef.h>
#include <stdint.h>

typedef struct
{
    uint8_t players;
    uint8_t ready;
} LNetRoomRoster;

static inline int lnet_room_roster_parse(const uint8_t *src, size_t size,
                                         LNetRoomRoster *out)
{
    size_t offset = 1;
    uint8_t count, ready = 0, used = 0;
    unsigned int i, k;

    if (!src || !out || size < 1 || size > 1 + 2 * (3 + 48))
        return -1;
    count = src[0];
    if (count > 2)
        return -1;
    for (i = 0; i < count; i++)
    {
        uint8_t slot, value, length;
        if (offset + 3 > size)
            return -1;
        slot = src[offset++];
        value = src[offset++];
        length = src[offset++];
        if (slot < 1 || slot > 2 || used & (1u << slot) ||
            value > 1 || length < 1 || length > 48 ||
            offset + length > size)
            return -1;
        used |= (uint8_t)(1u << slot);
        ready += value;
        for (k = 0; k < length; k++)
        {
            uint8_t ch = src[offset + k];
            if (!((ch >= 'A' && ch <= 'Z') ||
                  (ch >= 'a' && ch <= 'z') ||
                  (ch >= '0' && ch <= '9') || ch == '_' || ch == '-'))
                return -1;
        }
        offset += length;
    }
    if (offset != size)
        return -1;
    out->players = count;
    out->ready = ready;
    return 0;
}
#endif
