#include "gw_sdl_host.h"
#include <stdint.h>
#include <stdio.h>

static uint16_t pixels[240 * 160];

int main(void)
{
    GWNativeHost *host = gw_host_open("Grand World Native host test (not the game)", 2, true);
    if (!host) {
        fprintf(stderr, "FAIL: SDL2 native host init\n");
        return 1;
    }
    for (int y = 0; y < 160; y++)
        for (int x = 0; x < 240; x++)
            pixels[y * 240 + x] = (uint16_t)((x & 31) | ((y & 31) << 5) | (((x + y) & 31) << 10));
    if (!gw_host_poll(host) || !gw_host_present_rgb555(host, pixels, 240)) {
        fprintf(stderr, "FAIL: SDL2 native host events/present\n");
        gw_host_close(host);
        return 2;
    }
    if (gw_host_keys(NULL) != 0) {
        fprintf(stderr, "FAIL: SDL2 invalid-host keys\n");
        gw_host_close(host);
        return 3;
    }
    gw_host_close(host);
    puts("PASS: SDL2 240x160 host smoke test (synthetic frame only)");
    return 0;
}
