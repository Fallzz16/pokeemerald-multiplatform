#ifdef PORTABLE
/*
 * LAN link conduit - session implementation.
 *
 * Wire format: every message is 3 bytes: [u8 kind][u16 value (big-endian)].
 *   kind 0x10 = HELLO carrying the sender's role (0 host / 1 client)
 *   kind 0x20 = SLOT carrying one 16-bit slot value
 */
#include "lnet_session.h"

#include <stdlib.h>
#include <string.h>
#include <time.h>

#define MSG_HELLO 0x10
#define MSG_SLOT  0x20

/* Socket operations never wait for a peer on the game thread. */
#define LNET_HELLO_TIMEOUT_SECONDS 8
#define LNET_CONNECT_TIMEOUT_SECONDS 10
#define LNET_SLOT_TIMEOUT_SECONDS 6

/* Non-blocking handshake phases. The HELLO exchange is driven a few bytes at a
 * time from poll(): the peer is allowed to connect but then send nothing (a
 * stale/semidead connection), and the game loop must never block on it. */
#define HS_STEP_FIRST  1 /* host: send host HELLO; client: recv peer HELLO */
#define HS_STEP_SECOND 2 /* host: recv client HELLO; client: send own HELLO */

struct LNetSession
{
    LNetSock *sock;
    LNetSock *listener; /* host: still-listening accept socket while connecting */
    LNetSock *pending;  /* client: in-progress nonblocking connect socket */
    LNetRole role;
    int alive;
    int connecting; /* 1 while host accept / client connect not yet completed */
    int helloDone;  /* HELLO role handshake finished */
    char host[128];  /* client: connect target */
    unsigned short port;
    /* non-blocking HELLO handshake progress */
    int hsStep;
    unsigned char hsOut[3];
    int hsOutSent;
    unsigned char hsIn[3];
    int hsInGot;
    time_t connectStarted;
    time_t helloStarted;
    time_t slotStarted;
    int slotPending;
    unsigned char slotOut[3];
    unsigned char slotIn[3];
    size_t slotOutSent;
    size_t slotInGot;
};

/* Send our HELLO message without blocking. Returns 1 once all 3 bytes are
 * written, 0 while still writing (poll again), -1 on a permanent error. */
static int hs_send_hello(LNetSession *s, LNetRole role, int *err)
{
    size_t adv = 0;
    int r;

    if (s->hsOutSent == 0)
    {
        s->hsOut[0] = MSG_HELLO;
        s->hsOut[1] = 1; /* Hybrid LAN protocol v1; reject incompatible donor peers. */
        s->hsOut[2] = (unsigned char)role;
    }
    r = lnet_net_send_nb(s->sock, s->hsOut + s->hsOutSent,
                         sizeof(s->hsOut) - (size_t)s->hsOutSent, &adv, err);
    if (r < 0)
        return -1;
    if (r == 0 || adv == 0)
    {
        if (err)
            *err = LNET_ERR_AGAIN;
        return 0;
    }
    s->hsOutSent += (int)adv;
    if (s->hsOutSent < (int)sizeof(s->hsOut))
    {
        if (err)
            *err = LNET_ERR_AGAIN;
        return 0;
    }
    return 1;
}

/* Receive the peer's HELLO message without blocking. Returns 1 once all 3 bytes
 * are validated, 0 while still waiting (poll again), -1 on an error or a peer
 * that failed the role check. */
static int hs_recv_hello(LNetSession *s, LNetRole wantPeer, int *err)
{
    size_t adv = 0;
    int r;

    r = lnet_net_recv_nb(s->sock, s->hsIn + s->hsInGot,
                         sizeof(s->hsIn) - (size_t)s->hsInGot, &adv, err);
    if (r < 0)
        return -1;
    if (r == 0 || adv == 0)
    {
        if (err)
            *err = LNET_ERR_AGAIN;
        return 0;
    }
    s->hsInGot += (int)adv;
    if (s->hsInGot < (int)sizeof(s->hsIn))
    {
        if (err)
            *err = LNET_ERR_AGAIN;
        return 0;
    }
    if (s->hsIn[0] != MSG_HELLO || s->hsIn[1] != 1 || s->hsIn[2] != (unsigned char)wantPeer)
    {
        if (err)
            *err = LNET_ERR_RECV;
        return -1;
    }
    return 1;
}

LNetSession *lnet_session_host(unsigned short port, int *err)
{
    LNetSock *listener;
    LNetSession *s;

    if (err)
        *err = LNET_ERR_OK;
    listener = lnet_net_listen(port, err);
    if (listener == NULL)
        return NULL;

    s = (LNetSession *)calloc(1, sizeof(LNetSession));
    s->listener = listener;
    s->role = LNET_ROLE_HOST;
    s->alive = 1;
    s->connecting = 1;
    return s;
}

LNetSession *lnet_session_join(const char *host, unsigned short port, int *err)
{
    LNetSession *s;

    if (err)
        *err = LNET_ERR_OK;
    s = (LNetSession *)calloc(1, sizeof(LNetSession));
    s->role = LNET_ROLE_CLIENT;
    s->alive = 1;
    s->connecting = 1;
    s->connectStarted = time(NULL);
    (void)strncpy(s->host, host, sizeof(s->host) - 1);
    s->host[sizeof(s->host) - 1] = '\0';
    s->port = port;
    return s;
}

/* Drive connection establishment for a pending session. Returns 1 when the
 * HELLO handshake is complete (the session is ready for exchange), 0 while
 * still connecting (poll again later), or -1 on a permanent error. */
int lnet_session_poll(LNetSession *s, int *err)
{
    LNetSock *conn = NULL;
    int r;

    if (s == NULL)
        return -1;
    if (!s->alive)
        return -1;
    if (s->helloDone)
        return 1;
    if (s->role == LNET_ROLE_CLIENT && s->sock == NULL
        && time(NULL) - s->connectStarted > LNET_CONNECT_TIMEOUT_SECONDS)
    {
        s->alive = 0;
        if (err)
            *err = LNET_ERR_CONNECT;
        return -1;
    }
    if (err)
        *err = LNET_ERR_OK;

    /* 1) Connection phase: host accept / client connect. */
    if (s->sock == NULL)
    {
        if (s->role == LNET_ROLE_HOST)
        {
            if (s->listener == NULL)
                return -1;
            conn = lnet_net_accept_nb(s->listener, err);
            if (conn == NULL)
            {
                if (err && *err == LNET_ERR_AGAIN)
                    return 0; /* keep waiting for a client */
                return -1;
            }
            (void)lnet_net_close(s->listener);
            s->listener = NULL;
            s->sock = conn;
            s->hsStep = HS_STEP_FIRST;
            s->hsOutSent = 0;
            s->hsInGot = 0;
            s->helloStarted = time(NULL);
        }
        else
        {
            conn = lnet_net_connect_nb(s->host, s->port, &s->pending, err);
            if (conn == NULL)
            {
                if (err && *err == LNET_ERR_AGAIN)
                    return 0; /* connect still in progress */
                return -1;
            }
            s->pending = NULL;
            s->sock = conn;
            s->hsStep = HS_STEP_FIRST;
            s->hsOutSent = 0;
            s->hsInGot = 0;
            s->helloStarted = time(NULL);
        }
    }

    if (time(NULL) - s->helloStarted > LNET_HELLO_TIMEOUT_SECONDS)
    {
        s->alive = 0;
        if (err)
            *err = LNET_ERR_RECV;
        return -1;
    }

    /* 2) Non-blocking HELLO handshake. Each step only makes progress when data
     * is actually ready, so a peer that connects but never answers cannot hang
     * the game loop. */
    if (s->hsStep == HS_STEP_FIRST)
    {
        if (s->role == LNET_ROLE_HOST)
            r = hs_send_hello(s, LNET_ROLE_HOST, err);
        else
            r = hs_recv_hello(s, LNET_ROLE_HOST, err);
        if (r <= 0)
            return r;
        s->hsStep = HS_STEP_SECOND;
    }
    if (s->hsStep == HS_STEP_SECOND)
    {
        if (s->role == LNET_ROLE_HOST)
            r = hs_recv_hello(s, LNET_ROLE_CLIENT, err);
        else
            r = hs_send_hello(s, LNET_ROLE_CLIENT, err);
        if (r <= 0)
            return r;
    }

    s->helloDone = 1;
    s->connecting = 0;
    return 1;
}

void lnet_session_close(LNetSession *s)
{
    if (s == NULL)
        return;
    s->alive = 0;
    lnet_net_close(s->sock);
    if (s->listener != NULL)
        lnet_net_close(s->listener);
    if (s->pending != NULL)
        lnet_net_close(s->pending);
    free(s);
}

LNetRole lnet_session_role(const LNetSession *s)
{
    return s->role;
}

int lnet_session_is_ready(const LNetSession *s)
{
    return s != NULL && s->helloDone && s->sock != NULL;
}

/*
 * Advance one 3-byte SIO exchange without ever blocking the game loop.
 * A slot is captured once, then partial sends and receives are resumed on
 * subsequent calls. SerialCB must run only after both messages are complete.
 * Returns 1 = complete, 0 = pending, -1 = closed/error/timeout.
 */
int lnet_session_exchange(LNetSession *s, unsigned short myVal, unsigned short *peerVal)
{
    size_t advanced = 0;
    int err;
    int r;

    if (s == NULL || s->sock == NULL || !s->alive || !s->helloDone)
        return -1;

    if (!s->slotPending)
    {
        s->slotPending = 1;
        s->slotStarted = time(NULL);
        s->slotOutSent = 0;
        s->slotInGot = 0;
        s->slotOut[0] = MSG_SLOT;
        s->slotOut[1] = (unsigned char)(myVal >> 8);
        s->slotOut[2] = (unsigned char)(myVal & 0xFF);
    }
    if (time(NULL) - s->slotStarted > LNET_SLOT_TIMEOUT_SECONDS)
    {
        s->alive = 0;
        return -1;
    }

    if (s->slotOutSent < sizeof(s->slotOut))
    {
        r = lnet_net_send_nb(s->sock, s->slotOut + s->slotOutSent,
                             sizeof(s->slotOut) - s->slotOutSent, &advanced, &err);
        if (r < 0)
        {
            s->alive = 0;
            return -1;
        }
        if (r == 0)
            return 0;
        s->slotOutSent += advanced;
        if (s->slotOutSent < sizeof(s->slotOut))
            return 0;
    }

    advanced = 0;
    r = lnet_net_recv_nb(s->sock, s->slotIn + s->slotInGot,
                         sizeof(s->slotIn) - s->slotInGot, &advanced, &err);
    if (r < 0)
    {
        s->alive = 0;
        return -1;
    }
    if (r == 0)
        return 0;
    s->slotInGot += advanced;
    if (s->slotInGot < sizeof(s->slotIn))
        return 0;
    if (s->slotIn[0] != MSG_SLOT)
    {
        s->alive = 0;
        return -1;
    }
    if (peerVal != NULL)
        *peerVal = (unsigned short)(((unsigned short)s->slotIn[1] << 8) | s->slotIn[2]);
    s->slotPending = 0;
    return 1;
}
#endif /* PORTABLE */
