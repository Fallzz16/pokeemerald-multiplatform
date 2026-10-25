#include "gw_sdl_host.h"
#include <stdint.h>
#define SDL_MAIN_HANDLED
#include <SDL.h>

#define WIDTH 240
#define HEIGHT 160
static uint16_t framebuffer[WIDTH * HEIGHT];

static int clamp(int n, int minimum, int maximum)
{
    return n < minimum ? minimum : (n > maximum ? maximum : n);
}

int main(void)
{
    SDL_SetMainReady();
    GWNativeHost *host = gw_host_open("Grand World Native: SDL2 host preview (NOT THE GAME)", 3, false);
    int player_x = 120, player_y = 80;
    if (!host)
        return 1;

    for (int frame = 0; frame < 1800 && gw_host_poll(host); ++frame) {
        uint16_t input = gw_host_keys(host);
        if (input & GW_KEY_LEFT) player_x--;
        if (input & GW_KEY_RIGHT) player_x++;
        if (input & GW_KEY_UP) player_y--;
        if (input & GW_KEY_DOWN) player_y++;
        player_x = clamp(player_x, 5, WIDTH - 6);
        player_y = clamp(player_y, 5, HEIGHT - 6);
        for (int y = 0; y < HEIGHT; ++y) {
            for (int x = 0; x < WIDTH; ++x) {
                int field = ((x / 16) + (y / 16)) % 2;
                framebuffer[y * WIDTH + x] = field ? 0x19A5 : 0x1143;
                if (x >= player_x - 5 && x <= player_x + 5 &&
                    y >= player_y - 5 && y <= player_y + 5)
                    framebuffer[y * WIDTH + x] = 0x7FFF;
            }
        }
        if (!gw_host_present_rgb555(host, framebuffer, WIDTH)) {
            gw_host_close(host);
            return 2;
        }
        SDL_Delay(16);
    }
    gw_host_close(host);
    return 0;
}
