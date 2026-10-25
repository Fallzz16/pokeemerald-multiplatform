#include "gw_sdl_host.h"
#include <stdint.h>
#include <stdio.h>
#define SDL_MAIN_HANDLED
#include <SDL.h>

static uint16_t pixels[240 * 160];

int main(void)
{
    SDL_SetMainReady();
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

    /* Real host-side BMP theme import (never executes plugin code). */
    SDL_Surface *test_image = SDL_CreateRGBSurfaceWithFormat(0, 2, 2, 32, SDL_PIXELFORMAT_ARGB8888);
    if (!test_image) {
        gw_host_close(host);
        return 4;
    }
    SDL_FillRect(test_image, NULL, SDL_MapRGB(test_image->format, 255, 0, 0));
    if (SDL_SaveBMP(test_image, "gw_test_theme.bmp") != 0) {
        SDL_FreeSurface(test_image);
        gw_host_close(host);
        return 5;
    }
    SDL_FreeSurface(test_image);
    if (!gw_host_read_bmp_rgb555("gw_test_theme.bmp", pixels, 240, 160)) {
        remove("gw_test_theme.bmp");
        gw_host_close(host);
        return 6;
    }
    remove("gw_test_theme.bmp");
    if (pixels[0] != 0x001F || pixels[239] != 0x001F) {
        fprintf(stderr, "FAIL: Native BMP reader color/sample check\\n");
        gw_host_close(host);
        return 7;
    }
    gw_host_close(host);
    puts("PASS: SDL2 240x160 host smoke test (synthetic frame + data-only BMP theme)");
    return 0;
}
