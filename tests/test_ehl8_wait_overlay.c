/* Pure SDL renderer-call test with a tiny fake renderer.
 * No real window or game/save file is created by this fixture. */
#include <assert.h>
#include <stdio.h>
typedef struct SDL_Renderer { int calls; int border; } SDL_Renderer;
typedef struct {int x,y,w,h;} SDL_Rect;
enum { SDL_BLENDMODE_NONE = 0, SDL_BLENDMODE_BLEND = 1 };
static void SDL_SetRenderDrawBlendMode(SDL_Renderer *r, int mode)
{ (void)r; assert(mode == SDL_BLENDMODE_NONE || mode == SDL_BLENDMODE_BLEND); }
static void SDL_SetRenderDrawColor(SDL_Renderer *r,
                                   int red,int green,int blue,int alpha)
{ (void)r; assert(red >= 0 && green >= 0 && blue >= 0 && alpha >= 0); }
static void SDL_RenderFillRect(SDL_Renderer *r,const SDL_Rect *rect)
{
    assert(rect->x >= 0 && rect->y >= 0 && rect->w > 0 && rect->h > 0);
    assert(rect->x + rect->w <= 240 && rect->y + rect->h <= 160);
    r->calls++;
}
static void SDL_RenderDrawRect(SDL_Renderer *r,const SDL_Rect *rect)
{ assert(rect->w <= 240); r->border++; }
#include "../src/lnet/lnet_wait_overlay.h"
int main(void)
{
    SDL_Renderer renderer = {0,0};
    lnet_wait_overlay_render(&renderer, 0, -1);
    lnet_wait_overlay_render(&renderer, 2, -1);
    assert(renderer.calls == 0 && renderer.border == 0);
    lnet_wait_overlay_render(&renderer, 1, -1);
    assert(renderer.calls > 100 && renderer.border == 1);
    renderer.calls = 0;
    lnet_wait_overlay_render(&renderer, 3, -1);
    assert(renderer.calls > 100 && renderer.border == 2);
    renderer.calls = 0;
    lnet_wait_overlay_render(&renderer, 4, -1); /* network interrupted */
    assert(renderer.calls > 40 && renderer.border == 3);
    renderer.calls = 0;
    lnet_wait_overlay_render(&renderer, 5, -1); /* retry window exhausted */
    assert(renderer.calls > 40 && renderer.border == 4);
    renderer.calls = 0;
    lnet_wait_overlay_render(&renderer, 2, -1); /* connected again */
    assert(renderer.calls == 0 && renderer.border == 4);
    /* The same in-game panel now includes live counters from the server. */
    renderer.calls = 0;
    lnet_wait_overlay_render(&renderer, 1, 1 | (1 << 4)); /* 1/2, 1 ready */
    assert(renderer.calls > 100 && renderer.border == 5);
    renderer.calls = 0;
    lnet_wait_overlay_render(&renderer, 1, 2 | (2 << 4)); /* 2/2, 2 ready */
    assert(renderer.calls > 100 && renderer.border == 6);
    renderer.calls = 0;
    lnet_wait_overlay_render(&renderer, 1, 0); /* connected room, zero ready */
    assert(renderer.calls > 100 && renderer.border == 7);
    printf("EHL8 room population + reconnect HUD: PASS\n");
    return 0;
}
