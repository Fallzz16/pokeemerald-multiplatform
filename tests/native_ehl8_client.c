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
    int reconnect = (argc == 8 && (strcmp(argv[7], "reconnect") == 0 ||
                                     strcmp(argv[7], "manualreconnect") == 0));
    int manualReconnect = (argc == 8 && strcmp(argv[7], "manualreconnect") == 0);
    int rosterMode = (argc == 8 && strcmp(argv[7], "roster") == 0);
    int manualReady = (argc == 8 && strcmp(argv[7], "manualready") == 0);
    int manualCancel = (argc == 8 && strcmp(argv[7], "manualcancel") == 0);
    int toggledReady = 0;
    int lobbyTicks = 0;
    int sawFullRoster = 0;
    int awaitStart = (argc == 8 && strcmp(argv[7], "awaitstart") == 0);
    int reconnectObserved = 0;
    int sawWaitStart = 0;
    struct timespec startTime, currentTime;
    unsigned long startElapsed = 0;
    /* The manual host test must not start before at least 2.5 seconds. */
    const unsigned long minimumWaitMs = 2500UL;
    int lingerCount = (argc == 8 && strcmp(argv[7], "lingerlong") == 0)
        ? 650 : 180;
    int witnessed = 0;
    struct timespec pauseTime = { 0, 10000000L };
    if (argc != 7 && !linger && !reconnect && !awaitStart && !rosterMode && !manualReady && !manualCancel)
    {
        fprintf(stderr, "usage: native_ehl8_client IPv4 port pin profile x expected_remote_x [linger|reconnect|awaitstart]\n");
        return 2;
    }
    port = (unsigned short)strtoul(argv[2], NULL, 10);
    client = lnet_session_client_new(argv[1], port, argv[3], argv[4]);
    if (!client)
        return 3;
    if ((manualReady || manualCancel || manualReconnect) && !lnet_session_client_set_manual_ready(client, 1))
    {
        lnet_session_client_close(client);
        return 8;
    }
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
    for (i = 0; i < (linger ? lingerCount : 800); ++i)
    {
        int state;
        lnet_session_client_poll(client, &local);
        state = lnet_session_client_state(client);
        if ((manualReady || manualReconnect) && state == EHL_CLIENT_WAIT_START &&
            i >= 80 && !toggledReady)
        {
            if (lnet_session_client_toggle_ready(client) != 1)
            {
                lnet_session_client_close(client);
                return 9;
            }
            toggledReady = 1;
        }
        if (manualCancel && state == EHL_CLIENT_WAIT_START)
        {
            int expected = -1;
            lobbyTicks++;
            if (lobbyTicks >= 35 && toggledReady == 0) expected = 1;
            else if (lobbyTicks >= 100 && toggledReady == 1) expected = 0;
            else if (lobbyTicks >= 165 && toggledReady == 2) expected = 1;
            if (expected != -1)
            {
                if (lnet_session_client_toggle_ready(client) != expected)
                {
                    lnet_session_client_close(client);
                    return 10;
                }
                toggledReady++;
            }
        }
        if (rosterMode)
        {
            LNetRoomRoster roster;
            if (lnet_session_client_get_roster(client, &roster))
            {
                if (roster.players > 2 || roster.ready > roster.players)
                {
                    lnet_session_client_close(client);
                    return 7;
                }
                if (roster.players == 2 && roster.ready == 2)
                    sawFullRoster = 1;
            }
        }
        if (state == EHL_CLIENT_WAIT_START)
            sawWaitStart = 1;
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
        if (lnet_session_client_get_remote(client, &remote) &&
            remote.x == (unsigned short)atoi(argv[6]) && remote.active)
        {
            witnessed = 1;
            if (manualCancel && toggledReady == 3)
            {
                puts("EHL8 native manual READY CANCEL READY and host START verified");
                lnet_session_client_close(client);
                return 0;
            }
            if (manualReady && toggledReady)
            {
                puts("EHL8 native manual READY and host START verified");
                lnet_session_client_close(client);
                return 0;
            }
            if (rosterMode && sawFullRoster)
            {
                puts("EHL8 native PLAYER_LIST 2/2 READY and remote pose verified");
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
            if (!linger && !reconnect && !rosterMode && !manualReady && !manualCancel)
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
