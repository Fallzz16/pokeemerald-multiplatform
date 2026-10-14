#ifndef GUARD_LNET_PRESENCE_H
#define GUARD_LNET_PRESENCE_H
/* Secondary TCP stream for two-player overworld presence; NEVER mix with GBA
 * serial words on the Cable Club stream. These types do not touch save data. */
#include <stdint.h>
#define LNET_PRESENCE_PACKET_SIZE 18
typedef struct LNetPresence LNetPresence;

typedef struct
{
    uint16_t seq;
    uint8_t active;
    uint8_t mapGroup, mapNum;
    uint16_t x, y;                /* absolute map tile coordinates */
    uint8_t direction;            /* Emerald DIR_SOUTH/NORTH/WEST/EAST */
    uint8_t gender;               /* 0 Brendan, 1 May */
    uint8_t elevation;
} LNetPose;

int lnet_presence_pack(const LNetPose *p, unsigned char out[LNET_PRESENCE_PACKET_SIZE]);
int lnet_presence_unpack(const unsigned char in[LNET_PRESENCE_PACKET_SIZE], LNetPose *p);
LNetPresence *lnet_presence_host(unsigned short port, int *err);
LNetPresence *lnet_presence_join(const char *host, unsigned short port, int *err);
void lnet_presence_close(LNetPresence *s);
/* Must run on game thread once per frame, nonblocking. */
void lnet_presence_poll(LNetPresence *s, const LNetPose *local);
int lnet_presence_is_connected(const LNetPresence *s);
int lnet_presence_get_remote(const LNetPresence *s, LNetPose *out);
#endif
