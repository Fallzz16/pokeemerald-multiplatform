#ifndef GUARD_LNET_START_GATE_H
#define GUARD_LNET_START_GATE_H
/*
 * Optional desktop EHL8 input gate. Network polling and rendering continue
 * normally while waiting for the server's actual START frame.
 * Once started, gameplay is never re-frozen by a transient disconnection;
 * users can continue their save offline, per Emerald Hybrid decisions.
 *
 * state: 1 = EHL8 PLAYING, 0 = waiting, -1 = failed/unavailable.
 * Only called on the native game thread, NOT the SDL render thread.
 */
typedef struct
{
    int enabled;
    int released;
} LNetStartGate;

static inline int lnet_start_gate_blocked(LNetStartGate *gate, int state)
{
    if (!gate->enabled || gate->released)
        return 0;
    if (state == 1)
    {
        gate->released = 1;
        return 0;
    }
    return 1;
}
#endif
