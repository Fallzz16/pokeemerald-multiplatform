/* No sockets or graphical game: test the production EHL8 snapshot parser. */
#define PORTABLE 1
#define _POSIX_C_SOURCE 200809L
#include "../src/lnet/lnet_session_client.c"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static int decode_fixture(LNetSessionClient *c, EhlSessionFrame *frame,
                          const unsigned char *data, size_t len)
{
    memset(frame, 0, sizeof(*frame));
    assert(len <= sizeof(frame->payload));
    memcpy(frame->payload, data, len);
    frame->payload_size = (uint16_t)len;
    return decode_room_list(c, frame);
}

int main(void)
{
    LNetSessionClient client;
    EhlSessionFrame frame;
    int players = -1, ready = -1, mine = -1;
    const unsigned char empty[] = {0};
    const unsigned char solo[] = {1, 1, 1, 2, 'Q', 'A'};
    const unsigned char allReady[] = {2, 1, 1, 1, 'A', 2, 1, 1, 'B'};
    const unsigned char ownCancel[] = {2, 1, 0, 1, 'A', 2, 1, 1, 'B'};
    const unsigned char duplicate[] = {2, 1, 1, 1, 'A', 1, 1, 1, 'B'};
    const unsigned char invalidReady[] = {1, 1, 2, 1, 'A'};
    const unsigned char invalidSlot[] = {1, 3, 1, 1, 'A'};
    const unsigned char invalidLength[] = {1, 1, 1, 48, 'A'};
    const unsigned char trailing[] = {0, 1};
    const unsigned char excess[] = {3};
    memset(&client, 0, sizeof(client));
    client.localSlot = 1;
    assert(!lnet_session_client_room_status(&client, &players, &ready, &mine));
    assert(decode_fixture(&client, &frame, empty, sizeof(empty)) == 0);
    assert(lnet_session_client_room_status(&client, &players, &ready, &mine));
    assert(players == 0 && ready == 0 && mine == 0);
    assert(decode_fixture(&client, &frame, solo, sizeof(solo)) == 0);
    assert(lnet_session_client_room_status(&client, &players, &ready, &mine));
    assert(players == 1 && ready == 1 && mine == 1);
    assert(decode_fixture(&client, &frame, allReady, sizeof(allReady)) == 0);
    assert(lnet_session_client_room_status(&client, &players, &ready, &mine));
    assert(players == 2 && ready == 2 && mine == 1);
    assert(decode_fixture(&client, &frame, ownCancel, sizeof(ownCancel)) == 0);
    assert(lnet_session_client_room_status(&client, &players, &ready, &mine));
    assert(players == 2 && ready == 1 && mine == 0);
    assert(decode_fixture(&client, &frame, duplicate, sizeof(duplicate)) < 0);
    assert(decode_fixture(&client, &frame, invalidReady, sizeof(invalidReady)) < 0);
    assert(decode_fixture(&client, &frame, invalidSlot, sizeof(invalidSlot)) < 0);
    assert(decode_fixture(&client, &frame, invalidLength, sizeof(invalidLength)) < 0);
    assert(decode_fixture(&client, &frame, trailing, sizeof(trailing)) < 0);
    assert(decode_fixture(&client, &frame, excess, sizeof(excess)) < 0);
    assert(decode_fixture(&client, &frame, solo, sizeof(solo) - 1) < 0);
    /* Malformed frames never contaminate a previously validated UI state. */
    assert(lnet_session_client_room_status(&client, &players, &ready, &mine));
    assert(players == 2 && ready == 1 && mine == 0);
    puts("EHL8 confirmed room/READY parser: PASS");
    return 0;
}
