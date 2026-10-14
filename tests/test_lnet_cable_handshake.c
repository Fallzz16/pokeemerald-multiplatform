/*
 * Model the precise two-player handshake predicates in Emerald's DoHandshake
 * while exercising the REAL native TCP + SIO transport on 127.0.0.1.
 *
 * This tests the transport/serial word ordering, not the entire game scene.
 * Human/automated Cable Club gameplay is still a separate acceptance gate.
 */
#include "lnet_link.h"
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>

#define TEST_PORT 45777u
#define MASTER_HANDSHAKE 0x8FFFu
#define SLAVE_HANDSHAKE  0xB9A0u
#define EXPECT_IDLE_HIGH 0xFFFFFFFF00000000ULL
#define MAX_SLOTS 36

typedef struct
{
    int host;
    int ready;
    int succeeded;
    int slotCount;
    int sawBothPlayers;
    int invalidView;
} Peer;

static Peer sHost = {1, 0, 0, 0, 0, 0};
static Peer sClient = {0, 0, 0, 0, 0, 0};

static void *run_peer(void *arg)
{
    Peer *p = (Peer *)arg;
    LNetLink *link;
    unsigned short outbound = 0;
    unsigned short peerSend = 0;
    unsigned long long received = 0;
    int lastCount = 0;
    int err = LNET_ERR_OK;
    int i;

    if (!p->host)
        usleep(30000); /* host must bind before client attempts connection */

    link = p->host ? lnet_link_host(TEST_PORT, &err)
                   : lnet_link_join("127.0.0.1", TEST_PORT, &err);
    if (link == NULL)
        return NULL;

    for (i = 0; i < 300000 && !lnet_link_ready(link); i++)
    {
        if (lnet_link_poll(link, &err) < 0)
            goto done;
        sched_yield();
    }
    if (!lnet_link_ready(link))
        goto done;
    p->ready = 1;

    for (i = 0; i < MAX_SLOTS; i++)
    {
        int result;
        unsigned short words[4];
        int count;
        int j;

        do
        {
            result = lnet_link_slot(link, outbound, &peerSend, &received);
            if (result == 0)
                sched_yield();
        } while (result == 0);
        if (result < 0)
            break;
        p->slotCount++;

        words[0] = (unsigned short)received;
        words[1] = (unsigned short)(received >> 16);
        words[2] = (unsigned short)(received >> 32);
        words[3] = (unsigned short)(received >> 48);

        if ((received & EXPECT_IDLE_HIGH) != EXPECT_IDLE_HIGH)
            p->invalidView = 1;
        if (words[p->host ? 0 : 1] != outbound
            || words[p->host ? 1 : 0] != peerSend)
            p->invalidView = 1;

        /* Mirrored from DoHandshake: count consecutive handshake words,
         * require slot zero MASTER and stable 2-player count to complete. */
        count = 0;
        for (j = 0; j < 4; j++)
        {
            if (((words[j] & (unsigned short)~3u) == SLAVE_HANDSHAKE)
                || words[j] == MASTER_HANDSHAKE)
                count++;
            else
            {
                if (words[j] != 0xFFFFu)
                    count = 0;
                break;
            }
        }
        if (count == 2)
            p->sawBothPlayers = 1;
        if (count > 1 && count == lastCount && words[0] == MASTER_HANDSHAKE)
        {
            p->succeeded = !p->invalidView;
            break;
        }

        lastCount = count;
        /* Emerald's link master advances to MASTER_HANDSHAKE after it has
         * recognized two valid players; client always sends SLAVE. */
        outbound = (p->host && count > 1) ? MASTER_HANDSHAKE
                                          : SLAVE_HANDSHAKE;
    }

done:
    lnet_link_close(link);
    return NULL;
}

int main(void)
{
    pthread_t th, tc;
    if (pthread_create(&th, NULL, run_peer, &sHost) != 0)
        return 2;
    if (pthread_create(&tc, NULL, run_peer, &sClient) != 0)
        return 2;
    pthread_join(th, NULL);
    pthread_join(tc, NULL);

    if (!sHost.ready || !sClient.ready ||
        !sHost.succeeded || !sClient.succeeded ||
        !sHost.sawBothPlayers || !sClient.sawBothPlayers ||
        sHost.invalidView || sClient.invalidView)
    {
        fprintf(stderr,
                "FAIL: Cable Club SIO handshake model host=%d/%d client=%d/%d "
                "slots=%d,%d view-invalid=%d,%d\n",
                sHost.ready, sHost.succeeded,
                sClient.ready, sClient.succeeded,
                sHost.slotCount, sClient.slotCount,
                sHost.invalidView, sClient.invalidView);
        return 1;
    }
    printf("passed: two-player Emerald SIO handshake model (host=%d, client=%d slots)\n",
           sHost.slotCount, sClient.slotCount);
    return 0;
}
