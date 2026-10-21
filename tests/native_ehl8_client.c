/* Standalone deterministic native client for real TCP interoperability QA.
 * No Emerald state or .sav accessed, no SDL dependency. */
#include "lnet_session_client.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>
int main(int argc, char **argv)
{
    LNetSessionClient *client;
    LNetPose local, remote;
    unsigned short port;
    int i;
    int linger = (argc == 8 &&
                 (strcmp(argv[7], "linger") == 0 ||
                  strcmp(argv[7], "lingerlong") == 0));
    int reconnect = (argc == 8 && strcmp(argv[7], "reconnect") == 0);
    int awaitStart = (argc == 8 && strcmp(argv[7], "awaitstart") == 0);
    int mapcycle = (argc == 8 && strcmp(argv[7], "mapcycle") == 0);
    int readySwitch = (argc == 8 && strcmp(argv[7], "readyswitch") == 0);
    int firstWaitFrame = -1, revoked = 0, rearmed = 0;
    int firstPlayingFrame = -1, sawMap0 = 0, sawMap1 = 0, sawHidden = 0;
    int reconnectObserved = 0;
    int sawWaitStart = 0;
    struct timespec startTime, currentTime;
    unsigned long startElapsed = 0;
    /* The manual host test must not start before at least 2.5 seconds. */
    const unsigned long minimumWaitMs = 2500UL;
    int lingerCount = (argc == 8 && strcmp(argv[7], "lingerlong") == 0)
        ? 650 : 180;
    int witnessed = 0;
    int sawCancelledAck = 0, sawRestoredAck = 0;
    struct timespec pauseTime = { 0, 10000000L };
    if (argc != 7 && !linger && !reconnect && !awaitStart &&
        !mapcycle && !readySwitch)
    {
        fprintf(stderr, "usage: native_ehl8_client IPv4 port pin profile x expected_remote_x [linger|reconnect|awaitstart|mapcycle|readyswitch]\n");
        return 2;
    }
    port = (unsigned short)strtoul(argv[2], NULL, 10);
    client = lnet_session_client_new(argv[1], port, argv[3], argv[4]);
    if (!client)
        return 3;
    local.seq = 0;
    local.active = 1;
    local.mapGroup = 0;
    local.mapNum = 0;
    local.x = (unsigned short)atoi(argv[5]);
    local.y = 13;
    local.direction = 1;
    local.gender = 0;
    local.elevation = 0;
    clock_gettime(CLOCK_MONOTONIC, &startTime);
    for (i = 0; i < (mapcycle ? 540 : (linger ? lingerCount : 800)); ++i)
    {
        int state, remoteVisible;
        if (readySwitch && firstWaitFrame >= 0)
        {
            int framesWaiting = i - firstWaitFrame;
            if (framesWaiting >= 55 && framesWaiting < 230)
            {
                lnet_session_client_set_ready(client, 0);
                revoked = 1;
            }
            else if (framesWaiting >= 230)
            {
                lnet_session_client_set_ready(client, 1);
                rearmed = 1;
            }
        }
        if (mapcycle && firstPlayingFrame >= 0)
        {
            int elapsedFrames = i - firstPlayingFrame;
            local.active = elapsedFrames < 185 || elapsedFrames >= 255;
            local.mapNum = elapsedFrames < 85 ? 0 :
                           elapsedFrames < 255 ? 1 : 2;
        }
        lnet_session_client_poll(client, &local);
        state = lnet_session_client_state(client);
        if (readySwitch)
        {
            int players, roomReady, myReady;
            if (lnet_session_client_room_status(client,
                                                &players, &roomReady, &myReady)
                && players == 2)
            {
                if (revoked && roomReady == 0 && !myReady)
                    sawCancelledAck = 1;
                if (rearmed && sawCancelledAck &&
                    roomReady == 2 && myReady)
                    sawRestoredAck = 1;
            }
        }
        if (mapcycle && state == EHL_CLIENT_PLAYING && firstPlayingFrame < 0)
            firstPlayingFrame = i;
        if (state == EHL_CLIENT_WAIT_START)
        {
            sawWaitStart = 1;
            if (firstWaitFrame < 0)
                firstWaitFrame = i;
        }
        if (awaitStart && state == EHL_CLIENT_PLAYING)
        {
            clock_gettime(CLOCK_MONOTONIC, &currentTime);
            startElapsed = (unsigned long)(currentTime.tv_sec - startTime.tv_sec)
                * 1000UL + (unsigned long)(currentTime.tv_nsec - startTime.tv_nsec
                + 1000000000L) / 1000000UL - 1000UL;
            if (!sawWaitStart || startElapsed < minimumWaitMs)
            {
                fprintf(stderr, "EHL8 manual START arrived too early or WAIT_START skipped\n");
                lnet_session_client_close(client);
                return 6;
            }
        }
        if (lnet_session_client_state(client) == EHL_CLIENT_RECONNECTING)
            reconnectObserved = 1;
        if (lnet_session_client_state(client) == EHL_CLIENT_FAILED)
        {
            lnet_session_client_close(client);
            return 4;
        }
        remoteVisible = lnet_session_client_get_remote(client, &remote);
        if (mapcycle && firstPlayingFrame >= 0)
        {
            int elapsedFrames = i - firstPlayingFrame;
            if (remoteVisible && remote.x == (unsigned short)atoi(argv[6]))
            {
                if (remote.mapGroup == 0 && remote.mapNum == 0 && remote.active)
                    sawMap0 = 1;
                if (remote.mapGroup == 0 && remote.mapNum == 1 && remote.active)
                    sawMap1 = 1;
                if (remote.mapGroup == 0 && remote.mapNum == 2 && remote.active
                    && sawMap0 && sawMap1 && sawHidden)
                {
                    puts("EHL8 native map transitions, inactive hide and reappearance verified");
                    lnet_session_client_close(client);
                    return 0;
                }
            }
            if (elapsedFrames > 220 && sawMap1 && !remoteVisible)
                sawHidden = 1;
        }
        if (remoteVisible && remote.x == (unsigned short)atoi(argv[6]) &&
            remote.active)
        {
            witnessed = 1;
            if (readySwitch && revoked && rearmed &&
                sawCancelledAck && sawRestoredAck && sawWaitStart)
            {
                puts("EHL8 native READY cancelled and restored before host START");
                lnet_session_client_close(client);
                return 0;
            }
            if (awaitStart)
            {
                puts("EHL8 native WAIT_START heartbeats and delayed manual START verified");
                lnet_session_client_close(client);
                return 0;
            }
            if (reconnect && reconnectObserved)
            {
                puts("EHL8 native token resume and fresh remote pose verified");
                lnet_session_client_close(client);
                return 0;
            }
            if (!linger && !reconnect && !mapcycle && !readySwitch)
            {
                puts("EHL8 native client remote overworld pose verified");
                lnet_session_client_close(client);
                return 0;
            }
        }
        nanosleep(&pauseTime, NULL);
    }
    lnet_session_client_close(client);
    if (linger && witnessed)
    {
        puts("EHL8 native client remote and heartbeat observation window completed");
        return 0;
    }
    return 5;
}
