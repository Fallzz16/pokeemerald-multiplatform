#ifndef GUARD_LNET_SESSION_CLIENT_H
#define GUARD_LNET_SESSION_CLIENT_H
/* Dedicated EHL8 overworld client. Never opens or modifies Cable Club SIO.
 * Nonblocking, game-thread driven. No direct save/map/sprite access. */
#include "lnet_presence.h"
#include "lnet_room_roster.h"
typedef struct LNetSessionClient LNetSessionClient;
enum {
    EHL_CLIENT_CONNECTING = 0,
    EHL_CLIENT_WAIT_WELCOME,
    EHL_CLIENT_WAIT_AUTH,
    EHL_CLIENT_WAIT_JOIN,
    EHL_CLIENT_WAIT_START,
    EHL_CLIENT_PLAYING,
    EHL_CLIENT_FAILED,
    EHL_CLIENT_RECONNECTING
};
LNetSessionClient *lnet_session_client_new(const char *ipv4, unsigned short port,
                                           const char *pin, const char *profile);
void lnet_session_client_close(LNetSessionClient *c);
/* Opt-in for user launcher; must be called before first native poll.
 * Returns 1 on successful setup. QA Lab remains auto-ready by default. */
int lnet_session_client_set_manual_ready(LNetSessionClient *c, int enabled);
/* Returns new desired ready status (0/1), or -1 outside WAIT_START. */
int lnet_session_client_toggle_ready(LNetSessionClient *c);
void lnet_session_client_poll(LNetSessionClient *c, const LNetPose *local);
int lnet_session_client_get_remote(const LNetSessionClient *c, LNetPose *out);
/* Last strictly checked server roster; 0 = not yet received/connection lost. */
int lnet_session_client_get_roster(const LNetSessionClient *c,
                                   LNetRoomRoster *out);
int lnet_session_client_state(const LNetSessionClient *c);
#endif
