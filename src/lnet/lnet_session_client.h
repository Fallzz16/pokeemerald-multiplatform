#ifndef GUARD_LNET_SESSION_CLIENT_H
#define GUARD_LNET_SESSION_CLIENT_H
/* Dedicated EHL8 overworld client. Never opens or modifies Cable Club SIO.
 * Nonblocking, game-thread driven. No direct save/map/sprite access. */
#include "lnet_presence.h"
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
void lnet_session_client_poll(LNetSessionClient *c, const LNetPose *local);
int lnet_session_client_get_remote(const LNetSessionClient *c, LNetPose *out);
/* F5 player action: request READY=1/0 on the existing EHL8 protocol.
 * Called exclusively on the game thread. Returns 0 outside WAIT_START. */
int lnet_session_client_toggle_ready(LNetSessionClient *c);
/* Returns 1 for a validated latest PLAYER_LIST, 0 if not available. */
int lnet_session_client_lobby_counts(const LNetSessionClient *c,
                                     int *players, int *ready);
int lnet_session_client_state(const LNetSessionClient *c);
#endif
