#include "../src/lnet/lnet_start_gate.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    LNetStartGate offline = {0, 0};
    LNetStartGate ehl8 = {1, 0};

    /* Never block solo or Cable Club when no explicit EHL8 wait is set. */
    assert(!lnet_start_gate_blocked(&offline, 0));
    assert(!lnet_start_gate_blocked(&offline, -1));
    assert(!lnet_start_gate_blocked(&offline, 1));

    /* A real game is allowed to tick/network, but receives no input yet. */
    assert(lnet_start_gate_blocked(&ehl8, 0));
    assert(lnet_start_gate_blocked(&ehl8, 0));
    assert(lnet_start_gate_blocked(&ehl8, -1)); /* fail closed */
    assert(ehl8.released == 0);
    /* Only the EHL8 PLAYING state releases gameplay keys. */
    assert(!lnet_start_gate_blocked(&ehl8, 1));
    assert(ehl8.released == 1);
    /* Losing network after START must not lock the solo game. */
    assert(!lnet_start_gate_blocked(&ehl8, -1));
    assert(!lnet_start_gate_blocked(&ehl8, 0));
    puts("EHL8 opt-in gameplay input gate: PASS");
    return 0;
}
