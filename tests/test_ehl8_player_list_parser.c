/* Isolated protocol parser regression: no sockets, game windows or saves. */
#define PORTABLE 1
#define _POSIX_C_SOURCE 200809L
#include "../src/lnet/lnet_session_client.c"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static int decode_fixture(LNetSessionClient *c, EhlSessionFrame *frame,
                          const unsigned char *data, size_t n)
{
    memset(frame, 0, sizeof(*frame));
    assert(n <= sizeof(frame->payload));
    memcpy(frame->payload, data, n);
    frame->payload_size = (uint16_t)n;
    return decode_room_list(c, frame);
}

int main(void)
{
    LNetSessionClient client;
    EhlSessionFrame frame;
    int players = -1, ready = -1;
    const unsigned char empty[] = {0};
    const unsigned char solo[] = {1, 1, 1, 2, 'Q', 'A'};
    const unsigned char full[] = {2, 1, 1, 1, 'A', 2, 1, 1, 'B'};
    const unsigned char duplicate[] = {2, 1, 1, 1, 'A', 1, 1, 1, 'B'};
    const unsigned char badReady[] = {1, 1, 2, 1, 'A'};
    const unsigned char badSlot[] = {1, 3, 1, 1, 'A'};
    const unsigned char badLen[] = {1, 1, 1, 48, 'A'};
    const unsigned char trailing[] = {0, 1};
    const unsigned char badCount[] = {3};
    memset(&client, 0, sizeof(client));
    assert(!lnet_session_client_lobby_counts(&client, &players, &ready));
    assert(decode_fixture(&client, &frame, empty, sizeof(empty)) == 0);
    assert(lnet_session_client_lobby_counts(&client, &players, &ready));
    assert(players == 0 && ready == 0);
    assert(decode_fixture(&client, &frame, solo, sizeof(solo)) == 0);
    assert(lnet_session_client_lobby_counts(&client, &players, &ready));
    assert(players == 1 && ready == 1);
    assert(decode_fixture(&client, &frame, full, sizeof(full)) == 0);
    assert(lnet_session_client_lobby_counts(&client, &players, &ready));
    assert(players == 2 && ready == 2);

    /* Bad snapshots cannot replace the last verified state or add a phantom
     * player to the UI. A caller will treat the server frame as malformed. */
    assert(decode_fixture(&client, &frame, duplicate, sizeof(duplicate)) < 0);
    assert(decode_fixture(&client, &frame, badReady, sizeof(badReady)) < 0);
    assert(decode_fixture(&client, &frame, badSlot, sizeof(badSlot)) < 0);
    assert(decode_fixture(&client, &frame, badLen, sizeof(badLen)) < 0);
    assert(decode_fixture(&client, &frame, trailing, sizeof(trailing)) < 0);
    assert(decode_fixture(&client, &frame, badCount, sizeof(badCount)) < 0);
    assert(decode_fixture(&client, &frame, solo, sizeof(solo)-1) < 0);
    assert(lnet_session_client_lobby_counts(&client, &players, &ready));
    assert(players == 2 && ready == 2);
    /* The per-player READY toggle is opt-in and only valid before START.
     * Rapid toggles update the pending request, never a socket from SDL. */
    client.state = EHL_CLIENT_WAIT_START;
    client.selfSlot = 1;
    client.desiredReady = 1;
    assert(lnet_session_client_toggle_ready(&client) == 1);
    assert(client.desiredReady == 0 && client.pendingReady == 1);
    assert(lnet_session_client_toggle_ready(&client) == 1);
    assert(client.desiredReady == 1 && client.pendingReady == 1);
    client.pendingReady = 0;
    client.state = EHL_CLIENT_PLAYING;
    assert(lnet_session_client_toggle_ready(&client) == 0);
    assert(client.pendingReady == 0);
    client.state = EHL_CLIENT_RECONNECTING;
    assert(lnet_session_client_toggle_ready(&client) == 0);
    client.state = EHL_CLIENT_WAIT_START;
    client.selfSlot = 0;
    assert(lnet_session_client_toggle_ready(&client) == 0);
    puts("EHL8 native PLAYER_LIST parser: PASS");
    return 0;
}
