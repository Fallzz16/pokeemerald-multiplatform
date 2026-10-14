#ifndef LNET_SESSION_V1_H
#define LNET_SESSION_V1_H
/* Standalone EHL8 session framing; not the original Cable Club serial stream. */
#include <stddef.h>
#include <stdint.h>

#define EHL_SESSION_HEADER_SIZE 28u
#define EHL_SESSION_MAX_PAYLOAD 4096u
#define EHL_SESSION_MAX_FRAME (EHL_SESSION_HEADER_SIZE + EHL_SESSION_MAX_PAYLOAD)
#define EHL_SESSION_MAJOR 1u
#define EHL_SESSION_MINOR 0u

enum EhlMessageType {
    EHL_HELLO = 1, EHL_WELCOME, EHL_INCOMPATIBLE, EHL_AUTH_PIN,
    EHL_JOIN, EHL_PLAYER_LIST, EHL_READY, EHL_START, EHL_LEAVE,
    EHL_KICK, EHL_HEARTBEAT, EHL_POSE, EHL_INVITE, EHL_INVITE_REPLY,
    EHL_PAIR_PREPARE, EHL_PAIR_CLOSE, EHL_SERVER_CLOSE
};

typedef struct {
    uint16_t type;
    uint32_t request_id;
    uint64_t session_id;
    uint16_t payload_size;
    uint8_t payload[EHL_SESSION_MAX_PAYLOAD];
} EhlSessionFrame;

typedef struct {
    uint8_t wire[EHL_SESSION_MAX_FRAME];
    size_t used;
    size_t target;
} EhlSessionDecoder;

/* -1: invalid header, oversized payload or invalid arguments; 0: incomplete;
 *  1: exactly one decoded frame.  *consumed is always the number of input
 *  bytes used by this call, so callers can process multiple concatenated
 *  frames.  Invalid input resets the decoder. */
void ehl_session_decoder_init(EhlSessionDecoder *d);
int ehl_session_encode(const EhlSessionFrame *frame, uint8_t *dst,
                       size_t capacity, size_t *written);
int ehl_session_decoder_feed(EhlSessionDecoder *d, const uint8_t *src,
                             size_t length, size_t *consumed,
                             EhlSessionFrame *result);
#endif
