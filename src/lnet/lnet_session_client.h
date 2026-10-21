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
/* Game-thread-only request: EHL8 READY/UNREADY before START.
 * Existing clients default to READY=1 for full backward compatibility. */
void lnet_session_client_set_ready(LNetSessionClient *c, int ready);
void lnet_session_client_poll(LNetSessionClient *c, const LNetPose *local);
int lnet_session_client_get_remote(const LNetSessionClient *c, LNetPose *out);
/* Only validated server snapshot counts and local READY acknowledgement.
 * Read on the game thread, never from the SDL renderer thread. */
int lnet_session_client_room_status(const LNetSessionClient *c,
                                    int *players, int *ready, int *mine);
int lnet_session_client_state(const LNetSessionClient *c);
#endif
