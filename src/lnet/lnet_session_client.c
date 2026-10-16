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
#ifdef EHL_DEBUG_HANDSHAKE
#include <stdio.h>
#endif
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#else
#include <arpa/inet.h>
#endif

#define EHL_CONNECT_TIMEOUT_MS 12000UL
#define EHL_AUTH_TIMEOUT_MS 20000UL
#define EHL_STALE_MS 3000UL
#define EHL_POSE_INTERVAL_MS 100UL
#ifndef EHL_HEARTBEAT_INTERVAL_MS
#define EHL_HEARTBEAT_INTERVAL_MS 10000UL
#endif
#define EHL_PLAYING_SILENCE_MS 25000UL
#define EHL_RESUME_TOKEN_SIZE 32u
#define EHL_RECONNECT_WINDOW_MS 60000UL
#define EHL_RECONNECT_DELAY_MS 500UL
#define EHL_RECONNECT_RETRY_DELAY_MS 1500UL


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
    unsigned long began, lastRx, lastTx, lastPose, lastRemote, lastHeartbeat;
    uint16_t localSeq, lastRemoteSeq;
    uint8_t haveRemoteSeq, haveRemote;
    uint8_t haveResumeToken, resumeInFlight;
    unsigned char resumeToken[EHL_RESUME_TOKEN_SIZE];
    unsigned long reconnectSince, retryAt;
    unsigned int reconnectAttempts;
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

/* Only an authenticated session that actually received type-18 capability
 * may attempt resume. This is never enabled for legacy EHL8 servers. */
static void close_failed(LNetSessionClient *c)
{
    unsigned long now = now_ms();
#ifdef EHL_DEBUG_HANDSHAKE
    fprintf(stderr, "close_failed state=%d token=%u retry=%u\\n", c->state, c->haveResumeToken, c->resumeInFlight);
#endif
    int mayRetry = c->haveResumeToken &&
        (c->state == EHL_CLIENT_PLAYING || c->resumeInFlight);
    lnet_net_close(c->socket);
    lnet_net_close(c->pending);
    c->socket = NULL;
    c->pending = NULL;
    c->haveRemote = 0;
    c->haveRemoteSeq = 0;
    c->txLength = c->txOffset = 0;
    ehl_session_decoder_init(&c->decoder);
    if (mayRetry)
    {
        if (!c->resumeInFlight)
        {
            c->reconnectSince = now ? now : 1;
            c->reconnectAttempts = 0;
        }
        if ((unsigned long)(now - c->reconnectSince) < EHL_RECONNECT_WINDOW_MS)
        {
            c->resumeInFlight = 1;
            c->reconnectAttempts++;
            c->retryAt = now +
                (c->reconnectAttempts <= 1 ? EHL_RECONNECT_DELAY_MS :
                                               EHL_RECONNECT_RETRY_DELAY_MS);
            c->state = EHL_CLIENT_RECONNECTING;
            return;
        }
    }
    c->state = EHL_CLIENT_FAILED;
    c->resumeInFlight = c->haveResumeToken = 0;
    memset(c->pin, 0, sizeof(c->pin));
    memset(c->resumeToken, 0, sizeof(c->resumeToken));
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
    /* Clock starts with first in-game network pump, NOT launcher startup.
     * Intro/story loading may delay the first frame by many seconds. */
    c->began = 0;
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
    memset(c->resumeToken, 0, sizeof(c->resumeToken));
    free(c);
}

static int handle_frame(LNetSessionClient *c, const EhlSessionFrame *frame)
{
#ifdef EHL_DEBUG_HANDSHAKE
    fprintf(stderr, "frame state=%d kind=%u size=%u\\n", c->state, frame->type, frame->payload_size);
#endif
    if (c->state == EHL_CLIENT_WAIT_WELCOME)
    {
        if (frame->type != EHL_WELCOME || frame->payload_size != 1 ||
            frame->payload[0] != 2 || frame->session_id == 0)
            return -1;
        /* A replacement server has no reservation for this token. */
        if (c->resumeInFlight && frame->session_id != c->session)
        {
            c->haveResumeToken = 0;
            return -1;
        }
        c->session = frame->session_id;
        if (!queue(c, EHL_AUTH_PIN, (const unsigned char *)c->pin, 6))
            return -1;
        c->state = EHL_CLIENT_WAIT_AUTH;
        return 0;
    }
    if (frame->type == EHL_KICK || frame->type == EHL_INCOMPATIBLE ||
        frame->type == EHL_SERVER_CLOSE)
    {
        /* Host kick, protocol rejection and server shutdown are final. */
        c->haveResumeToken = 0;
        return -1;
    }
    if (frame->session_id != c->session)
        return -1;
    if (c->state == EHL_CLIENT_WAIT_AUTH)
    {
        if (frame->type != EHL_AUTH_PIN || frame->payload_size != 1 ||
            frame->payload[0] != 1)
            return -1;
        /* PIN is no longer needed after authentication. */
        if (c->resumeInFlight)
        {
            unsigned char payload[49 + EHL_RESUME_TOKEN_SIZE];
            size_t length = strlen(c->profile);
            if (!c->haveResumeToken || length >= 49)
                return -1;
            memcpy(payload, c->profile, length);
            payload[length] = 0;
            memcpy(payload + length + 1, c->resumeToken,
                   EHL_RESUME_TOKEN_SIZE);
            if (!queue(c, EHL_RESUME, payload,
                       length + 1 + EHL_RESUME_TOKEN_SIZE))
                return -1;
            memset(payload, 0, sizeof(payload));
        }
        else if (!queue(c, EHL_JOIN, (const unsigned char *)c->profile,
                        strlen(c->profile)))
            return -1;
        /* Retain the PIN only in RAM while resumable; never log or persist it.
         * On legacy servers it is wiped once PLAYING begins. */
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
    if (frame->type == EHL_RESUME &&
        (c->state == EHL_CLIENT_WAIT_START || c->state == EHL_CLIENT_PLAYING))
    {
        if (frame->payload_size != EHL_RESUME_TOKEN_SIZE)
            return -1;
        memcpy(c->resumeToken, frame->payload, EHL_RESUME_TOKEN_SIZE);
        c->haveResumeToken = 1;
        return 0;
    }
    if (frame->type == EHL_PLAYER_LIST || frame->type == EHL_HEARTBEAT)
        return 0;
    if (frame->type == EHL_START && c->state == EHL_CLIENT_WAIT_START &&
        frame->payload_size == 0)
    {
        c->state = EHL_CLIENT_PLAYING;
        c->resumeInFlight = 0;
        c->reconnectSince = 0;
        c->reconnectAttempts = 0;
        c->haveRemote = 0;
        c->haveRemoteSeq = 0;
        c->lastHeartbeat = 0;
        if (!c->haveResumeToken)
            memset(c->pin, 0, sizeof(c->pin));
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
    if (c->state == EHL_CLIENT_RECONNECTING)
    {
        if ((unsigned long)(now - c->reconnectSince) >= EHL_RECONNECT_WINDOW_MS)
        {
            c->haveResumeToken = 0;
            close_failed(c);
            return;
        }
        if ((long)(now - c->retryAt) < 0)
            return;
        c->state = EHL_CLIENT_CONNECTING;
        c->began = now ? now : 1;
    }
    /* Server echoes HEARTBEAT even when there is no second player's pose.
     * Do not leave a socket silently stale forever if Wi-Fi dies mid-game. */
    if (c->state == EHL_CLIENT_PLAYING &&
        (unsigned long)(now - c->lastRx) > EHL_PLAYING_SILENCE_MS)
    {
        close_failed(c);
        return;
    }
    if (c->state == EHL_CLIENT_CONNECTING)
    {
        if (c->began == 0)
            c->began = now ? now : 1;
        if ((unsigned long)(now - c->began) >
            (c->resumeInFlight ? 5000UL : EHL_CONNECT_TIMEOUT_MS))
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
    /* Poses are due every 100 ms, so an "else if heartbeat" placed AFTER
     * pose would never run while the player is moving/connected. Give the
     * sparse liveness frame priority once every 10 seconds. */
    if (c->state == EHL_CLIENT_PLAYING &&
        (c->lastHeartbeat == 0 ||
         (unsigned long)(now - c->lastHeartbeat) >= EHL_HEARTBEAT_INTERVAL_MS))
    {
        if (!queue(c, EHL_HEARTBEAT, NULL, 0))
        {
            close_failed(c);
            return;
        }
        c->lastHeartbeat = now;
    }
    else if (c->state == EHL_CLIENT_PLAYING &&
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
