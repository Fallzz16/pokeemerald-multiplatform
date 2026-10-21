/* EHL8 roster parser: no sockets, SDL, saved games or game state. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "../src/lnet/lnet_room_roster.h"

static void rejects(const uint8_t *buf, size_t size)
{
    LNetRoomRoster roster = {99, 99};
    assert(lnet_room_roster_parse(buf, size, &roster) == -1);
    assert(roster.players == 99 && roster.ready == 99);
}

int main(void)
{
    LNetRoomRoster roster = {99, 99};
    const uint8_t empty[] = {0};
    const uint8_t one[] = {1, 1, 0, 3, 'Q','A','A'};
    const uint8_t two[] = {2, 1, 1, 3, 'Q','A','A',
                              2, 1, 3, 'Q','A','B'};
    const uint8_t not_ready[] = {2, 1, 1, 3, 'Q','A','A',
                                    2, 0, 3, 'Q','A','B'};
    uint8_t bad[sizeof(two)];
    assert(lnet_room_roster_parse(empty, sizeof(empty), &roster) == 0);
    assert(roster.players == 0 && roster.ready == 0);
    assert(lnet_room_roster_parse(one, sizeof(one), &roster) == 0);
    assert(roster.players == 1 && roster.ready == 0);
    assert(lnet_room_roster_parse(two, sizeof(two), &roster) == 0);
    assert(roster.players == 2 && roster.ready == 2);
    assert(lnet_room_roster_parse(not_ready, sizeof(not_ready), &roster) == 0);
    assert(roster.players == 2 && roster.ready == 1);
    rejects(NULL, sizeof(one));
    rejects(one, 0);
    rejects(one, sizeof(one) - 1);
    memcpy(bad, two, sizeof(bad)); bad[0] = 3;
    rejects(bad, sizeof(bad));
    memcpy(bad, two, sizeof(bad)); bad[5] = '/';
    rejects(bad, sizeof(bad));
    memcpy(bad, two, sizeof(bad)); bad[7] = 1; /* duplicate slot */
    rejects(bad, sizeof(bad));
    memcpy(bad, two, sizeof(bad)); bad[7] = 3; /* invalid slot */
    rejects(bad, sizeof(bad));
    memcpy(bad, two, sizeof(bad)); bad[2] = 2; /* invalid ready */
    rejects(bad, sizeof(bad));
    memcpy(bad, two, sizeof(bad)); bad[3] = 0; /* empty identity */
    rejects(bad, sizeof(bad));
    memcpy(bad, two, sizeof(bad)); bad[9] = 49; /* identity too long */
    rejects(bad, sizeof(bad));
    rejects(two, sizeof(two) - 1);
    assert(lnet_room_roster_parse(two, sizeof(two), NULL) == -1);
    puts("EHL8 player roster parser: PASS");
    return 0;
}
