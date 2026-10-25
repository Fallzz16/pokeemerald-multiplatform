/* Grand World native desktop entrypoint.
 * This invokes REAL Pokemon World/M8 engine functions and the REAL GBA GPU
 * renderer. This file cannot become a playable executable until the engine
 * C/ASM, original assets and platform services are successfully linked.
 * Do not substitute synthetic title/menu or fabricated game resources.
 */
#define SDL_MAIN_HANDLED
#include <SDL.h>
#include <stdint.h>
#include <stdio.h>
#include "global.h"
#include "gw_sdl_host.h"

#if !defined(PORTABLE) || !defined(GW_WORLD_NATIVE)
#error "This desktop entrypoint may only be compiled for portable World"
#endif

enum { GW_SCREEN_WIDTH = 240, GW_SCREEN_HEIGHT = 160 };
enum { GW_FRAME_PERIOD_MS = 1000 / 60 };

extern void AgbMain(void);
extern void GwWorldFrame(void);
extern void GwWorldVBlank(void);
extern void DrawFrame(uint16_t *pixels);

/* The host input bits 0..9 deliberately match GBA A, B, Select, Start,
 * Right, Left, Up, Down, R, L. REG_KEYINPUT uses active-low logic. */
static void set_host_keys(uint16_t host_keys)
{
    REG_KEYINPUT = (u16)(KEYS_MASK & ~host_keys);
}

int main(int argc, char **argv)
{
    GWNativeHost *host;
    uint16_t frame[GW_SCREEN_WIDTH * GW_SCREEN_HEIGHT];
    Uint32 next_tick;
    bool headless = false;
    (void)argv;

    if (argc > 1) {
        fprintf(stderr, "Usage: grandworld-native [no arguments]\n");
        return 2;
    }
    SDL_SetMainReady();
    host = gw_host_open("Grand World - real World engine (experimental)", 3,
                        headless);
    if (!host) {
        fprintf(stderr, "SDL2 graphics host initialization failed\n");
        return 3;
    }

    /* Native AgbMain returns after initialization; the GBA AgbMain keeps
     * entering AgbMainLoop forever, unchanged by the host-only overlay. */
    set_host_keys(0);
    AgbMain();
    next_tick = SDL_GetTicks();
    while (gw_host_poll(host)) {
        set_host_keys(gw_host_keys(host));
        GwWorldFrame();
        DrawFrame(frame);          /* actual GBA renderer: VCount/HBlank */
        GwWorldVBlank();           /* actual World VBlank interrupt */
        if (!gw_host_present_rgb555(host, frame, GW_SCREEN_WIDTH))
            break;
        next_tick += 16u;
        {
            Uint32 now = SDL_GetTicks();
            if ((int32_t)(next_tick - now) > 0)
                SDL_Delay(next_tick - now);
            else
                next_tick = now;
        }
    }
    gw_host_close(host);
    return 0;
}
