#ifndef GW_SDL_HOST_H
#define GW_SDL_HOST_H

#include <stdbool.h>
#include <stdint.h>

enum {
    GW_KEY_A = 1 << 0,
    GW_KEY_B = 1 << 1,
    GW_KEY_SELECT = 1 << 2,
    GW_KEY_START = 1 << 3,
    GW_KEY_RIGHT = 1 << 4,
    GW_KEY_LEFT = 1 << 5,
    GW_KEY_UP = 1 << 6,
    GW_KEY_DOWN = 1 << 7,
    GW_KEY_R = 1 << 8,
    GW_KEY_L = 1 << 9
};

typedef struct GWNativeHost GWNativeHost;

GWNativeHost *gw_host_open(const char *title, int scale, bool hidden);
bool gw_host_poll(GWNativeHost *host);
uint16_t gw_host_keys(const GWNativeHost *host);
bool gw_host_present_rgb555(GWNativeHost *host, const uint16_t *pixels, int pitch_pixels);
bool gw_host_read_bmp_rgb555(const char *bmp_path, uint16_t *pixels, int width, int height);
void gw_host_close(GWNativeHost *host);

#endif
