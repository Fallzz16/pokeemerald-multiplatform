/* End-to-end native C reconnect QA over real TCP; never starts the GBA. */
#include "lnet_session_client.h"
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
int main(int argc, char **argv)
{
    LNetSessionClient *c;
    LNetPose local;
    unsigned short port;
    int i, initialPlaying = 0, sawDisconnect = 0;
    struct timespec pauseTime = { 0, 10000000L };
    if (argc != 5) return 2;
    port = (unsigned short)strtoul(argv[2], NULL, 10);
    c = lnet_session_client_new(argv[1], port, argv[3], argv[4]);
    if (!c) return 3;
    local.seq = 0;
    local.active = 1;
    local.mapGroup = local.mapNum = 0;
    local.x = 21;
    local.y = 13;
    local.direction = 1;
    local.gender = local.elevation = 0;
    for (i = 0; i < 1600; ++i)
    {
        int state;
        lnet_session_client_poll(c, &local);
        state = lnet_session_client_state(c);
        if (state == EHL_CLIENT_FAILED)
        {
            fputs("EHL8 client failed before recovery\n", stderr);
            lnet_session_client_close(c);
            return 4;
        }
        if (state == EHL_CLIENT_PLAYING)
        {
            if (initialPlaying && sawDisconnect)
            {
                puts("EHL8 native client resumed with original slot");
                fflush(stdout);
                lnet_session_client_close(c);
                return 0;
            }
            initialPlaying = 1;
        }
        else if (initialPlaying)
            sawDisconnect = 1;
        nanosleep(&pauseTime, NULL);
    }
    lnet_session_client_close(c);
    return 5;
}
