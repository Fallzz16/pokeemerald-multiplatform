#include "gw_sdl_host.h"
#include <SDL.h>
#include <stdlib.h>

#define GW_WIDTH 240
#define GW_HEIGHT 160

struct GWNativeHost {
    SDL_Window *window;
    SDL_Renderer *renderer;
    SDL_Texture *texture;
    uint32_t *screen;
    uint16_t keys;
    bool running;
};

GWNativeHost *gw_host_open(const char *title, int scale, bool hidden)
{
    GWNativeHost *host = NULL;
    Uint32 flags = hidden ? SDL_WINDOW_HIDDEN : SDL_WINDOW_SHOWN;
    if (scale < 1 || scale > 10)
        return NULL;
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS | SDL_INIT_GAMECONTROLLER) != 0)
        return NULL;
    host = (GWNativeHost *)calloc(1, sizeof(*host));
    if (!host)
        goto fail;
    host->window = SDL_CreateWindow(title ? title : "Grand World Native",
                                    SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                                    GW_WIDTH * scale, GW_HEIGHT * scale, flags);
    if (!host->window)
        goto fail;
    host->renderer = SDL_CreateRenderer(host->window, -1, SDL_RENDERER_ACCELERATED);
    if (!host->renderer)
        host->renderer = SDL_CreateRenderer(host->window, -1, SDL_RENDERER_SOFTWARE);
    if (!host->renderer)
        goto fail;
    host->texture = SDL_CreateTexture(host->renderer, SDL_PIXELFORMAT_ARGB8888,
                                      SDL_TEXTUREACCESS_STREAMING, GW_WIDTH, GW_HEIGHT);
    if (!host->texture)
        goto fail;
    host->screen = (uint32_t *)calloc(GW_WIDTH * GW_HEIGHT, sizeof(uint32_t));
    if (!host->screen)
        goto fail;
    host->running = true;
    return host;
fail:
    gw_host_close(host);
    return NULL;
}

bool gw_host_poll(GWNativeHost *host)
{
    SDL_Event event;
    const Uint8 *kbd;
    uint16_t keys = 0;
    if (!host)
        return false;
    while (SDL_PollEvent(&event)) {
        if (event.type == SDL_QUIT)
            host->running = false;
    }
    kbd = SDL_GetKeyboardState(NULL);
    if (kbd[SDL_SCANCODE_Z]) keys |= GW_KEY_A;
    if (kbd[SDL_SCANCODE_X]) keys |= GW_KEY_B;
    if (kbd[SDL_SCANCODE_BACKSPACE]) keys |= GW_KEY_SELECT;
    if (kbd[SDL_SCANCODE_RETURN]) keys |= GW_KEY_START;
    if (kbd[SDL_SCANCODE_RIGHT]) keys |= GW_KEY_RIGHT;
    if (kbd[SDL_SCANCODE_LEFT]) keys |= GW_KEY_LEFT;
    if (kbd[SDL_SCANCODE_UP]) keys |= GW_KEY_UP;
    if (kbd[SDL_SCANCODE_DOWN]) keys |= GW_KEY_DOWN;
    if (kbd[SDL_SCANCODE_S]) keys |= GW_KEY_R;
    if (kbd[SDL_SCANCODE_A]) keys |= GW_KEY_L;
    host->keys = keys;
    return host->running;
}

uint16_t gw_host_keys(const GWNativeHost *host)
{
    return host ? host->keys : 0;
}

bool gw_host_present_rgb555(GWNativeHost *host, const uint16_t *pixels, int pitch_pixels)
{
    if (!host || !pixels || pitch_pixels < GW_WIDTH)
        return false;
    for (int y = 0; y < GW_HEIGHT; ++y) {
        for (int x = 0; x < GW_WIDTH; ++x) {
            const uint16_t c = pixels[y * pitch_pixels + x];
            const uint8_t r = (uint8_t)((c & 31) * 255 / 31);
            const uint8_t g = (uint8_t)(((c >> 5) & 31) * 255 / 31);
            const uint8_t b = (uint8_t)(((c >> 10) & 31) * 255 / 31);
            host->screen[y * GW_WIDTH + x] = 0xFF000000u | ((uint32_t)r << 16)
                                            | ((uint32_t)g << 8) | b;
        }
    }
    if (SDL_UpdateTexture(host->texture, NULL, host->screen, GW_WIDTH * sizeof(uint32_t)) != 0)
        return false;
    if (SDL_RenderClear(host->renderer) != 0)
        return false;
    if (SDL_RenderCopy(host->renderer, host->texture, NULL, NULL) != 0)
        return false;
    SDL_RenderPresent(host->renderer);
    return true;
}

void gw_host_close(GWNativeHost *host)
{
    if (!host) {
        SDL_Quit();
        return;
    }
    free(host->screen);
    if (host->texture) SDL_DestroyTexture(host->texture);
    if (host->renderer) SDL_DestroyRenderer(host->renderer);
    if (host->window) SDL_DestroyWindow(host->window);
    free(host);
    SDL_Quit();
}
