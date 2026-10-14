#ifdef PORTABLE
/* EHL8 native client: no SDL dependencies; once-per-frame nonblocking poll.
 * EHL8 is NOT the original Cable Club/SIO stream. Avoid mixing protocols.
 */
#include "lnet_session_client.h"
#include "lnet_session_v1.h"
#include "lnet_net.h"
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <arpa/inet.h>
#endif

#define EHL_CONNECT_TIMEOUT_MS 12000UL
#define EHL_AUTH_TIMEOUT_MS 20000UL
#define EHL_STALE_MS 3000UL
#define EHL_POSE_INTERVAL_MS 100UL
#define EHL_HEARTBEAT_INTERVAL_MS 10000UL

struct LNetSessionClient
{
    LNetSock *socket;
    LNetSock *pending;
    char host[64];
    char pin[7];
    char profile[49];
    unsigned short port;
    int state;
    uint64_t session;
    unsigned long began, lastRx, lastTx, lastPose, lastRemote;
    uint16_t localSeq, lastRemoteSeq;
    uint8_t haveRemoteSeq, haveRemote;
    LNetPose remote;
    EhlSessionDecoder decoder;
    unsigned char tx[EHL_SESSION_MAX_FRAME];
    size_t txLength, txOffset;
};

static unsigned long now_ms(void)
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

static void close_failed(LNetSessionClient *c)
{
    lnet_net_close(c->socket);
    lnet_net_close(c->pending);
    c->socket = NULL;
    c->pending = NULL;
    c->state = EHL_CLIENT_FAILED;
    c->haveRemote = 0;
    c->txLength = c->txOffset = 0;
}

static int queue(LNetSessionClient *c, uint16_t type,
                 const unsigned char *payload, size_t size)
{
    EhlSessionFrame frame;
    if (c->txLength != c->txOffset || size > EHL_SESSION_MAX_PAYLOAD)
        return 0;
    memset(&frame, 0, sizeof(frame));
    frame.type = type;
    frame.session_id = c->session;
    frame.payload_size = (uint16_t)size;
    if (size)
        memcpy(frame.payload, payload, size);
    if (ehl_session_encode(&frame, c->tx, sizeof(c->tx), &c->txLength) < 0)
        return 0;
    c->txOffset = 0;
    return 1;
}

LNetSessionClient *lnet_session_client_new(const char *host, unsigned short port,
                                           const char *pin, const char *profile)
{
    LNetSessionClient *c;
    size_t n;
    int i;
    if (host == NULL || pin == NULL || profile == NULL ||
        !port || strlen(host) >= 64 || strlen(pin) != 6)
        return NULL;
    n = strlen(profile);
    if (!n || n >= 49)
        return NULL;
    for (i = 0; i < 6; i++)
        if (pin[i] < '0' || pin[i] > '9')
            return NULL;
    for (i = 0; i < (int)n; i++)
        if (!((profile[i] >= 'a' && profile[i] <= 'z') ||
              (profile[i] >= 'A' && profile[i] <= 'Z') ||
              (profile[i] >= '0' && profile[i] <= '9') ||
              profile[i] == '_' || profile[i] == '-'))
            return NULL;
    /* inet_pton is shared with the native transport: no blocking DNS. */
    {
        struct in_addr parsed;
        if (inet_pton(AF_INET, host, &parsed) != 1)
            return NULL;
    }
    c = (LNetSessionClient *)calloc(1, sizeof(*c));
    if (!c)
        return NULL;
    strcpy(c->host, host);
    strcpy(c->pin, pin);
    strcpy(c->profile, profile);
    c->port = port;
    c->state = EHL_CLIENT_CONNECTING;
    c->began = now_ms();
    ehl_session_decoder_init(&c->decoder);
    return c;
}

void lnet_session_client_close(LNetSessionClient *c)
{
    if (!c)
        return;
    lnet_net_close(c->socket);
    lnet_net_close(c->pending);
    /* Never retain a live PIN in freed memory. */
    memset(c->pin, 0, sizeof(c->pin));
    free(c);
}

static int handle_frame(LNetSessionClient *c, const EhlSessionFrame *frame)
{
    if (c->state == EHL_CLIENT_WAIT_WELCOME)
    {
        if (frame->type != EHL_WELCOME || frame->payload_size != 1 ||
            frame->payload[0] != 2 || frame->session_id == 0)
            return -1;
        c->session = frame->session_id;
        if (!queue(c, EHL_AUTH_PIN, (const unsigned char *)c->pin, 6))
            return -1;
        c->state = EHL_CLIENT_WAIT_AUTH;
        return 0;
    }
    if (frame->session_id != c->session || frame->type == EHL_KICK ||
        frame->type == EHL_INCOMPATIBLE || frame->type == EHL_SERVER_CLOSE)
        return -1;
    if (c->state == EHL_CLIENT_WAIT_AUTH)
    {
        if (frame->type != EHL_AUTH_PIN || frame->payload_size != 1 ||
            frame->payload[0] != 1)
            return -1;
        /* PIN is no longer needed after authentication. */
        if (!queue(c, EHL_JOIN, (const unsigned char *)c->profile,
                   strlen(c->profile)))
            return -1;
        memset(c->pin, 0, sizeof(c->pin));
        c->state = EHL_CLIENT_WAIT_JOIN;
        return 0;
    }
    if (c->state == EHL_CLIENT_WAIT_JOIN)
    {
        if (frame->type != EHL_JOIN || frame->payload_size != 1 ||
            frame->payload[0] < 1 || frame->payload[0] > 2)
            return -1;
        if (!queue(c, EHL_READY, (const unsigned char *)"\1", 1))
            return -1;
        c->state = EHL_CLIENT_WAIT_START;
        return 0;
    }
    if (frame->type == EHL_PLAYER_LIST || frame->type == EHL_HEARTBEAT)
        return 0;
    if (frame->type == EHL_START && c->state == EHL_CLIENT_WAIT_START &&
        frame->payload_size == 0)
    {
        c->state = EHL_CLIENT_PLAYING;
        return 0;
    }
    if (frame->type == EHL_LEAVE && frame->payload_size == 1)
    {
        c->haveRemote = 0;
        c->haveRemoteSeq = 0;
        return 0;
    }
    if (frame->type == EHL_POSE && c->state == EHL_CLIENT_PLAYING &&
        frame->payload_size == LNET_PRESENCE_PACKET_SIZE + 1 &&
        frame->payload[0] >= 1 && frame->payload[0] <= 2)
    {
        LNetPose pose;
        if (lnet_presence_unpack(frame->payload + 1, &pose) < 0)
            return -1;
        if (!c->haveRemoteSeq ||
            (int16_t)(pose.seq - c->lastRemoteSeq) > 0)
        {
            c->remote = pose;
            c->haveRemote = 1;
            c->haveRemoteSeq = 1;
            c->lastRemoteSeq = pose.seq;
            c->lastRemote = now_ms();
        }
        return 0;
    }
    return -1;
}

void lnet_session_client_poll(LNetSessionClient *c, const LNetPose *local)
{
    unsigned long now;
    int err, r, i;
    size_t moved;
    if (!c || c->state == EHL_CLIENT_FAILED)
        return;
    now = now_ms();
    if (c->state == EHL_CLIENT_CONNECTING)
    {
        if ((unsigned long)(now - c->began) > EHL_CONNECT_TIMEOUT_MS)
        {
            close_failed(c);
            return;
        }
        c->socket = lnet_net_connect_nb(c->host, c->port, &c->pending, &err);
        if (!c->socket)
        {
            if (err != LNET_ERR_AGAIN)
                close_failed(c);
            return;
        }
        c->pending = NULL;
        c->lastRx = c->lastTx = now;
        if (!queue(c, EHL_HELLO, NULL, 0))
        {
            close_failed(c);
            return;
        }
        c->state = EHL_CLIENT_WAIT_WELCOME;
    }
    if ((unsigned long)(now - c->lastRx) > EHL_AUTH_TIMEOUT_MS &&
        c->state != EHL_CLIENT_PLAYING)
    {
        close_failed(c);
        return;
    }
    if (c->txLength > c->txOffset)
    {
        moved = 0;
        r = lnet_net_send_nb(c->socket, c->tx + c->txOffset,
                             c->txLength - c->txOffset, &moved, &err);
        if (r < 0)
        {
            close_failed(c);
            return;
        }
        c->txOffset += moved;
        if (c->txOffset == c->txLength)
            c->txLength = c->txOffset = 0;
    }

    for (i = 0; i < 3; i++)
    {
        unsigned char bytes[EHL_SESSION_MAX_FRAME];
        EhlSessionFrame received;
        size_t consumed;
        size_t want = c->decoder.target - c->decoder.used;
        moved = 0;
        r = lnet_net_recv_nb(c->socket, bytes, want, &moved, &err);
        if (r < 0)
        {
            close_failed(c);
            return;
        }
        if (!moved)
            break;
        r = ehl_session_decoder_feed(&c->decoder, bytes, moved,
                                     &consumed, &received);
        if (r < 0 || consumed != moved)
        {
            close_failed(c);
            return;
        }
        c->lastRx = now;
        if (r == 1 && handle_frame(c, &received) < 0)
        {
            close_failed(c);
            return;
        }
    }

    /* Initial READY/HELLO/etc always takes precedence over pose updates. */
    if (c->txLength != c->txOffset)
        return;
    if (c->state == EHL_CLIENT_PLAYING &&
        (c->lastPose == 0 ||
         (unsigned long)(now - c->lastPose) >= EHL_POSE_INTERVAL_MS))
    {
        LNetPose value;
        unsigned char wire[LNET_PRESENCE_PACKET_SIZE];
        memset(&value, 0, sizeof(value));
        if (local)
            value = *local;
        value.seq = ++c->localSeq;
        if (lnet_presence_pack(&value, wire) < 0 ||
            !queue(c, EHL_POSE, wire, sizeof(wire)))
        {
            close_failed(c);
            return;
        }
        c->lastPose = now;
    }
    else if ((unsigned long)(now - c->lastTx) >= EHL_HEARTBEAT_INTERVAL_MS)
    {
        if (!queue(c, EHL_HEARTBEAT, NULL, 0))
        {
            close_failed(c);
            return;
        }
    }
    if (c->txLength != c->txOffset)
        c->lastTx = now;
}

int lnet_session_client_get_remote(const LNetSessionClient *c, LNetPose *out)
{
    if (!c || c->state != EHL_CLIENT_PLAYING || !c->haveRemote ||
        !c->remote.active ||
        (unsigned long)(now_ms() - c->lastRemote) > EHL_STALE_MS)
        return 0;
    if (out)
        *out = c->remote;
    return 1;
}

int lnet_session_client_state(const LNetSessionClient *c)
{
    return c ? c->state : EHL_CLIENT_FAILED;
}
#endif
