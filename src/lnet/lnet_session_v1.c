#include "lnet_session_v1.h"
#include <string.h>

static void wr16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)(v >> 8); p[1] = (uint8_t)v; }
static void wr32(uint8_t *p, uint32_t v) { wr16(p, (uint16_t)(v >> 16)); wr16(p + 2, (uint16_t)v); }
static void wr64(uint8_t *p, uint64_t v) { wr32(p, (uint32_t)(v >> 32)); wr32(p + 4, (uint32_t)v); }
static uint16_t rd16(const uint8_t *p) { return ((uint16_t)p[0] << 8) | p[1]; }
static uint32_t rd32(const uint8_t *p) { return ((uint32_t)rd16(p) << 16) | rd16(p + 2); }
static uint64_t rd64(const uint8_t *p) { return ((uint64_t)rd32(p) << 32) | rd32(p + 4); }

void ehl_session_decoder_init(EhlSessionDecoder *d)
{
    if (d != NULL) {
        memset(d, 0, sizeof(*d));
        d->target = EHL_SESSION_HEADER_SIZE;
    }
}

int ehl_session_encode(const EhlSessionFrame *f, uint8_t *out,
                       size_t capacity, size_t *written)
{
    size_t total;
    if (written != NULL) *written = 0;
    if (f == NULL || out == NULL || written == NULL ||
        f->type < EHL_HELLO || f->type > EHL_RESUME ||
        f->payload_size > EHL_SESSION_MAX_PAYLOAD) return -1;
    total = EHL_SESSION_HEADER_SIZE + (size_t)f->payload_size;
    if (capacity < total) return -1;
    out[0]='E'; out[1]='H'; out[2]='L'; out[3]='8';
    wr16(out+4, EHL_SESSION_MAJOR);
    wr16(out+6, EHL_SESSION_MINOR);
    wr16(out+8, f->type);
    wr16(out+10, 0); /* v1 reserved flags */
    wr32(out+12, f->payload_size);
    wr64(out+16, f->session_id);
    wr32(out+24, f->request_id);
    if (f->payload_size) memcpy(out+EHL_SESSION_HEADER_SIZE,f->payload,f->payload_size);
    *written = total;
    return 0;
}

int ehl_session_decoder_feed(EhlSessionDecoder *d, const uint8_t *src,
                             size_t length, size_t *consumed,
                             EhlSessionFrame *result)
{
    size_t n;
    uint16_t type;
    uint32_t length32;
    if (consumed != NULL) *consumed = 0;
    if (d == NULL || consumed == NULL || result == NULL ||
        (src == NULL && length != 0) || d->target < EHL_SESSION_HEADER_SIZE ||
        d->target > EHL_SESSION_MAX_FRAME || d->used > d->target) return -1;
    n = d->target - d->used;
    if (n > length) n = length;
    if (n) memcpy(d->wire+d->used, src, n);
    d->used += n;
    *consumed = n;
    if (d->used < d->target) return 0;
    if (d->target == EHL_SESSION_HEADER_SIZE) {
        const uint8_t *h = d->wire;
        type = rd16(h+8);
        length32 = rd32(h+12);
        if (h[0]!='E' || h[1]!='H' || h[2]!='L' || h[3]!='8' ||
            rd16(h+4)!=EHL_SESSION_MAJOR || rd16(h+6)!=EHL_SESSION_MINOR ||
            type<EHL_HELLO || type>EHL_RESUME || rd16(h+10)!=0 ||
            length32>EHL_SESSION_MAX_PAYLOAD) {
            ehl_session_decoder_init(d);
            return -1;
        }
        d->target += (size_t)length32;
        if (length32) return 0;
    }
    result->type = rd16(d->wire+8);
    result->payload_size = (uint16_t)rd32(d->wire+12);
    result->session_id = rd64(d->wire+16);
    result->request_id = rd32(d->wire+24);
    if (result->payload_size) memcpy(result->payload,d->wire+EHL_SESSION_HEADER_SIZE,result->payload_size);
    ehl_session_decoder_init(d);
    return 1;
}
