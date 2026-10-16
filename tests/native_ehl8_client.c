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
    int reconnectObserved = 0;
    int lingerCount = (argc == 8 && strcmp(argv[7], "lingerlong") == 0)
        ? 650 : 180;
    int witnessed = 0;
    struct timespec pauseTime = { 0, 10000000L };
    if (argc != 7 && !linger && !reconnect)
    {
        fprintf(stderr, "usage: native_ehl8_client IPv4 port pin profile x expected_remote_x [linger]\n");
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
    for (i = 0; i < (linger ? lingerCount : 800); ++i)
    {
        lnet_session_client_poll(client, &local);
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
            if (reconnect && reconnectObserved)
            {
                puts("EHL8 native token resume and fresh remote pose verified");
                lnet_session_client_close(client);
                return 0;
            }
            if (!linger && !reconnect)
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
