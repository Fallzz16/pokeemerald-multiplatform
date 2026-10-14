#ifdef PORTABLE
#include "lnet_presence.h"
#include "lnet_net.h"
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#endif

#define PRESENCE_SEND_INTERVAL_MS 100UL
#define PRESENCE_STALE_MS 3000UL
#define PRESENCE_CONNECT_TIMEOUT_MS 12000UL
#define PRESENCE_MAGIC_0 'L'
#define PRESENCE_MAGIC_1 'A'
#define PRESENCE_MAGIC_2 'N'
#define PRESENCE_MAGIC_3 'P'

struct LNetPresence
{
    LNetSock *listener;
    LNetSock *socket;
    LNetSock *pending;
    char host[64];
    unsigned short port;
    unsigned char wireOut[LNET_PRESENCE_PACKET_SIZE];
    unsigned char wireIn[LNET_PRESENCE_PACKET_SIZE];
    size_t sent;
    size_t received;
    unsigned long beginAt;
    unsigned long lastSentAt;
    unsigned long lastReceivedAt;
    uint16_t nextSeq;
    LNetPose remote;
    int isHost;
    int receivedPose;
    int failed;
};

static unsigned long presence_now(void)
{
#ifdef _WIN32
    return (unsigned long)GetTickCount();
#else
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0)
        return 0;
    return (unsigned long)(ts.tv_sec * 1000UL + ts.tv_nsec / 1000000UL);
#endif
}

static void put16(unsigned char *p, uint16_t n)
{
    p[0] = (unsigned char)(n >> 8);
    p[1] = (unsigned char)n;
}

static uint16_t get16(const unsigned char *p)
{
    return ((uint16_t)p[0] << 8) | p[1];
}

/* Reject data from incompatible builds and invalid positions before any
 * game map or sprite state is touched by the caller. */
int lnet_presence_pack(const LNetPose *p, unsigned char out[LNET_PRESENCE_PACKET_SIZE])
{
    if (!p || !out || p->active > 1 || p->direction > 4 ||
        p->gender > 1 || p->x > 2047 || p->y > 2047 || p->elevation > 15)
        return -1;
    memset(out, 0, LNET_PRESENCE_PACKET_SIZE);
    out[0] = PRESENCE_MAGIC_0;
    out[1] = PRESENCE_MAGIC_1;
    out[2] = PRESENCE_MAGIC_2;
    out[3] = PRESENCE_MAGIC_3;
    out[4] = 1; /* Presence protocol v1; separate from Cable Club. */
    out[5] = p->active;
    put16(out + 6, p->seq);
    out[8] = p->mapGroup;
    out[9] = p->mapNum;
    put16(out + 10, p->x);
    put16(out + 12, p->y);
    out[14] = p->direction;
    out[15] = p->gender;
    out[16] = p->elevation;
    return 0;
}

int lnet_presence_unpack(const unsigned char in[LNET_PRESENCE_PACKET_SIZE], LNetPose *p)
{
    LNetPose value;
    if (!in || !p || in[0] != PRESENCE_MAGIC_0 ||
        in[1] != PRESENCE_MAGIC_1 || in[2] != PRESENCE_MAGIC_2 ||
        in[3] != PRESENCE_MAGIC_3 || in[4] != 1 || in[17] != 0)
        return -1;
    memset(&value, 0, sizeof(value));
    value.active = in[5];
    value.seq = get16(in + 6);
    value.mapGroup = in[8];
    value.mapNum = in[9];
    value.x = get16(in + 10);
    value.y = get16(in + 12);
    value.direction = in[14];
    value.gender = in[15];
    value.elevation = in[16];
    if (value.active > 1 || value.direction > 4 ||
        value.gender > 1 || value.x > 2047 || value.y > 2047 ||
        value.elevation > 15 || (value.active && value.direction == 0))
        return -1;
    *p = value;
    return 0;
}

LNetPresence *lnet_presence_host(unsigned short port, int *err)
{
    LNetPresence *s;
    LNetSock *listenSocket = lnet_net_listen(port, err);
    if (!listenSocket)
        return NULL;
    s = (LNetPresence *)calloc(1, sizeof(*s));
    if (!s)
    {
        lnet_net_close(listenSocket);
        return NULL;
    }
    s->listener = listenSocket;
    s->isHost = 1;
    s->port = port;
    s->beginAt = presence_now();
    return s;
}

LNetPresence *lnet_presence_join(const char *host, unsigned short port, int *err)
{
    LNetPresence *s;
    if (err)
        *err = LNET_ERR_OK;
    if (!host || !*host || strlen(host) >= 64 || port == 0)
    {
        if (err)
            *err = LNET_ERR_CONNECT;
        return NULL;
    }
    s = (LNetPresence *)calloc(1, sizeof(*s));
    if (!s)
        return NULL;
    strcpy(s->host, host);
    s->port = port;
    s->beginAt = presence_now();
    return s;
}

void lnet_presence_close(LNetPresence *s)
{
    if (!s)
        return;
    lnet_net_close(s->listener);
    lnet_net_close(s->socket);
    lnet_net_close(s->pending);
    free(s);
}

int lnet_presence_is_connected(const LNetPresence *s)
{
    return s != NULL && s->socket != NULL && !s->failed;
}

int lnet_presence_get_remote(const LNetPresence *s, LNetPose *out)
{
    if (!lnet_presence_is_connected(s) || !s->receivedPose ||
        (unsigned long)(presence_now() - s->lastReceivedAt) > PRESENCE_STALE_MS ||
        !s->remote.active)
        return 0;
    if (out)
        *out = s->remote;
    return 1;
}

static void presence_drop(LNetPresence *s)
{
    lnet_net_close(s->socket);
    s->socket = NULL;
    lnet_net_close(s->pending);
    s->pending = NULL;
    lnet_net_close(s->listener);
    s->listener = NULL;
    s->receivedPose = 0;
    s->failed = 1;
}

void lnet_presence_poll(LNetPresence *s, const LNetPose *local)
{
    unsigned long now;
    int err = LNET_ERR_OK;
    int r;
    size_t count;
    int quota;

    if (!s || s->failed)
        return;
    now = presence_now();

    if (!s->socket)
    {
        if (!s->isHost &&
            (unsigned long)(now - s->beginAt) > PRESENCE_CONNECT_TIMEOUT_MS)
        {
            presence_drop(s);
            return;
        }
        if (s->isHost)
        {
            s->socket = lnet_net_accept_nb(s->listener, &err);
            if (!s->socket && err != LNET_ERR_AGAIN)
                presence_drop(s);
        }
        else
        {
            s->socket = lnet_net_connect_nb(s->host, s->port, &s->pending, &err);
            if (!s->socket && err != LNET_ERR_AGAIN)
                presence_drop(s);
        }
        if (!s->socket)
            return;
        lnet_net_close(s->listener);
        s->listener = NULL;
        s->pending = NULL;
        s->received = s->sent = 0;
        s->lastSentAt = 0;
    }

    /* Finish a partially sent packet before taking a fresh pose. All calls
     * are nonblocking, bounded to a single send syscall per game frame. */
    if (!s->sent &&
        (s->lastSentAt == 0 ||
         (unsigned long)(now - s->lastSentAt) >= PRESENCE_SEND_INTERVAL_MS))
    {
        LNetPose snapshot;
        memset(&snapshot, 0, sizeof(snapshot));
        if (local)
            snapshot = *local;
        snapshot.seq = ++s->nextSeq;
        if (lnet_presence_pack(&snapshot, s->wireOut) < 0)
        {
            presence_drop(s);
            return;
        }
        /* sent == 0 is both 'new packet' and 'no progress'; use -1 sentinel
         * for idle so the same bytes are never reinitialized on would-block. */
        s->sent = (size_t)-1;
    }
    if (s->sent != 0)
    {
        size_t offset = s->sent == (size_t)-1 ? 0 : s->sent - 1;
        count = 0;
        r = lnet_net_send_nb(s->socket, s->wireOut + offset,
                             LNET_PRESENCE_PACKET_SIZE - offset, &count, &err);
        if (r < 0)
        {
            presence_drop(s);
            return;
        }
        offset += count;
        if (offset == LNET_PRESENCE_PACKET_SIZE)
        {
            s->sent = 0;
            s->lastSentAt = now;
        }
        else
            s->sent = offset + 1;
    }

    /* A strict quota prevents a fast peer from starving the game loop. */
    for (quota = 0; quota < 3; quota++)
    {
        LNetPose decoded;
        count = 0;
        r = lnet_net_recv_nb(s->socket, s->wireIn + s->received,
                            LNET_PRESENCE_PACKET_SIZE - s->received, &count, &err);
        if (r < 0)
        {
            presence_drop(s);
            return;
        }
        if (!count)
            break;
        s->received += count;
        if (s->received < LNET_PRESENCE_PACKET_SIZE)
            continue;
        s->received = 0;
        if (lnet_presence_unpack(s->wireIn, &decoded) < 0)
        {
            presence_drop(s); /* protocol mismatch, never touch game state */
            return;
        }
        if (!s->receivedPose ||
            (int16_t)(decoded.seq - s->remote.seq) > 0)
        {
            s->remote = decoded;
            s->receivedPose = 1;
            s->lastReceivedAt = now;
        }
    }
}
#endif
