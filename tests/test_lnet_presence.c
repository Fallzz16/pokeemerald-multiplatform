/* Native loopback acceptance for independent two-player Hoenn presence. */
#include "lnet_presence.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define PORT 45791

static int run_until(LNetPresence *host, LNetPresence *client,
                     const LNetPose *h, const LNetPose *c,
                     LNetPose *seenH, LNetPose *seenC)
{
    int i;
    for (i = 0; i < 400; i++)
    {
        lnet_presence_poll(host, h);
        lnet_presence_poll(client, c);
        if (lnet_presence_get_remote(client, seenH) &&
            lnet_presence_get_remote(host, seenC))
            return 1;
        usleep(10000);
    }
    return 0;
}

int main(void)
{
    unsigned char wire[LNET_PRESENCE_PACKET_SIZE];
    LNetPose hostPose = {0};
    LNetPose clientPose = {0};
    LNetPose decoded;
    LNetPose hostAtClient;
    LNetPose clientAtHost;
    LNetPresence *host;
    LNetPresence *client;
    int err = 0;
    int i;

    hostPose.active = 1;
    hostPose.mapGroup = 2;
    hostPose.mapNum = 3;
    hostPose.x = 11;
    hostPose.y = 4;
    hostPose.direction = 1;
    hostPose.gender = 0;
    hostPose.elevation = 3;
    hostPose.seq = 65535;
    assert(lnet_presence_pack(&hostPose, wire) == 0);
    assert(lnet_presence_unpack(wire, &decoded) == 0);
    assert(decoded.seq == hostPose.seq && decoded.x == 11 && decoded.mapNum == 3);
    wire[4] = 2; /* unsupported protocol */
    assert(lnet_presence_unpack(wire, &decoded) == -1);
    wire[4] = 1;
    wire[14] = 9; /* impossible facing */
    assert(lnet_presence_unpack(wire, &decoded) == -1);
    wire[14] = 1;
    wire[17] = 1; /* reserved bits */
    assert(lnet_presence_unpack(wire, &decoded) == -1);
    wire[17] = 0;

    clientPose = hostPose;
    clientPose.gender = 1;
    clientPose.x = 12;
    clientPose.direction = 3;
    host = lnet_presence_host(PORT, &err);
    if (host == NULL)
    {
        fprintf(stderr, "FAIL: presence bind err=%d\n", err);
        return 2;
    }
    client = lnet_presence_join("127.0.0.1", PORT, &err);
    if (client == NULL)
    {
        lnet_presence_close(host);
        return 2;
    }

    if (!run_until(host, client, &hostPose, &clientPose, &hostAtClient, &clientAtHost))
    {
        fprintf(stderr, "FAIL: no mutual world presence after nonblocking connect\n");
        return 1;
    }
    if (hostAtClient.gender != 0 || hostAtClient.x != 11 ||
        clientAtHost.gender != 1 || clientAtHost.x != 12)
        return 1;
    puts("passed: host and client exchange independent world snapshots");

    hostPose.x = 13;
    for (i = 0; i < 100; i++)
    {
        lnet_presence_poll(host, &hostPose);
        lnet_presence_poll(client, &clientPose);
        if (lnet_presence_get_remote(client, &hostAtClient) && hostAtClient.x == 13)
            break;
        usleep(10000);
    }
    if (i == 100)
    {
        fprintf(stderr, "FAIL: host tile movement did not reach client\n");
        return 1;
    }
    puts("passed: updated movement reaches peer");

    lnet_presence_close(host);
    for (i = 0; i < 50; i++)
    {
        lnet_presence_poll(client, &clientPose);
        if (!lnet_presence_get_remote(client, &hostAtClient))
            break;
        usleep(10000);
    }
    if (i == 50)
    {
        fprintf(stderr, "FAIL: disconnect retained a stale player\n");
        return 1;
    }
    puts("passed: closed peer removed; no saved map data or collision");
    lnet_presence_close(client);
    return 0;
}
