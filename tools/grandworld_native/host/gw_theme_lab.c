/* Grand World Native STYLE LAB.
 * Interactive menu/sprite pack selector for the isolated SDL host.
 * This is a real native resource-pipeline test; NOT World gameplay.
 */
#define SDL_MAIN_HANDLED
#include <SDL.h>
#include "gw_sdl_host.h"
#include "gw_style_index.h"
#include "gw_follower_visual.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { W = 240, H = 160, FOLLOWER = 24 };
static GWStyleIndex library;
static GWStylePrefs preferences;
static uint16_t screen[W * H];
static uint32_t background[W * H];
static uint32_t companion[FOLLOWER * FOLLOWER];
static uint32_t directional[GW_FACE_COUNT][FOLLOWER * FOLLOWER];
static bool has_direction[GW_FACE_COUNT];
static bool custom_bg, custom_sprite;

/* Original tiny monospaced 5x7 glyphs, columns are seven-bit pixel masks. */
static const char font_letters[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 :-./()<>!";
static const unsigned char font_data[][5] = {
    {0x7e,0x11,0x11,0x11,0x7e},{0x7f,0x49,0x49,0x49,0x36},
    {0x3e,0x41,0x41,0x41,0x22},{0x7f,0x41,0x41,0x22,0x1c},
    {0x7f,0x49,0x49,0x49,0x41},{0x7f,0x09,0x09,0x09,0x01},
    {0x3e,0x41,0x49,0x49,0x7a},{0x7f,0x08,0x08,0x08,0x7f},
    {0x41,0x41,0x7f,0x41,0x41},{0x20,0x40,0x41,0x3f,0x01},
    {0x7f,0x08,0x14,0x22,0x41},{0x7f,0x40,0x40,0x40,0x40},
    {0x7f,0x02,0x0c,0x02,0x7f},{0x7f,0x04,0x08,0x10,0x7f},
    {0x3e,0x41,0x41,0x41,0x3e},{0x7f,0x09,0x09,0x09,0x06},
    {0x3e,0x41,0x51,0x21,0x5e},{0x7f,0x09,0x19,0x29,0x46},
    {0x26,0x49,0x49,0x49,0x32},{0x01,0x01,0x7f,0x01,0x01},
    {0x3f,0x40,0x40,0x40,0x3f},{0x1f,0x20,0x40,0x20,0x1f},
    {0x7f,0x20,0x18,0x20,0x7f},{0x63,0x14,0x08,0x14,0x63},
    {0x03,0x04,0x78,0x04,0x03},{0x61,0x51,0x49,0x45,0x43},
    {0x3e,0x51,0x49,0x45,0x3e},{0x00,0x42,0x7f,0x40,0x00},
    {0x42,0x61,0x51,0x49,0x46},{0x21,0x41,0x45,0x4b,0x31},
    {0x18,0x14,0x12,0x7f,0x10},{0x27,0x45,0x45,0x45,0x39},
    {0x3c,0x4a,0x49,0x49,0x30},{0x01,0x71,0x09,0x05,0x03},
    {0x36,0x49,0x49,0x49,0x36},{0x06,0x49,0x49,0x29,0x1e},
    {0,0,0,0,0},{0,0x36,0x36,0,0},
    {0,0x20,0x10,0x08,0},{0,0x08,0x08,0x08,0},
    {0x20,0x10,0x08,0x04,0x02},{0,0x60,0x60,0},
    {0,0x1c,0x22,0x41,0},{0,0x41,0x22,0x1c,0},
    {0x08,0x14,0x22,0x41,0},{0,0x41,0x22,0x14,0x08},
    {0,0,0x5f,0,0}
};

static uint16_t color555(unsigned r, unsigned g, unsigned b)
{
    return (uint16_t)((r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10));
}

static uint16_t from_argb(uint32_t c)
{
    return color555((c >> 16) & 255, (c >> 8) & 255, c & 255);
}

static void dot(int x, int y, uint16_t color)
{
    if (x >= 0 && x < W && y >= 0 && y < H)
        screen[y * W + x] = color;
}

static void rect(int x, int y, int width, int height, uint16_t color)
{
    for (int yy = y; yy < y + height; ++yy)
        for (int xx = x; xx < x + width; ++xx)
            dot(xx, yy, color);
}

static void glyph(int x, int y, char c, uint16_t color)
{
    const char *index;
    if (c >= 'a' && c <= 'z') c -= ('a' - 'A');
    index = strchr(font_letters, c);
    if (!index) return;
    const unsigned char *columns = font_data[index - font_letters];
    for (int col = 0; col < 5; ++col)
        for (int row = 0; row < 7; ++row)
            if (columns[col] & (1u << row))
                dot(x + col, y + row, color);
}

static void line_text(int x, int y, const char *text, uint16_t color)
{
    for (int n = 0; text[n] && n < 38; ++n)
        glyph(x + n * 6, y, text[n], color);
}

static void fill_default(void)
{
    for (int y = 0; y < H; ++y) {
        for (int x = 0; x < W; ++x) {
            bool check = ((x / 16) + (y / 16)) % 2;
            screen[y * W + x] = check ? color555(81,148,91) : color555(97,169,103);
        }
    }
    rect(0, 64, W, 32, color555(203,185,133));
    rect(104, 0, 32, H, color555(203,185,133));
}

static void draw_companion(int x, int y, GWFace8 face)
{
    if (!custom_sprite) {
        rect(x + 7, y + 8, 13, 12, color555(232,163,66));
        rect(x + 9, y + 3, 4, 8, color555(232,163,66));
        rect(x + 16, y + 3, 4, 8, color555(232,163,66));
        rect(x + 15, y + 11, 2, 2, color555(33,37,41));
        return;
    }
    const uint32_t *frame = (face >= 0 && face < GW_FACE_COUNT && has_direction[face])
        ? directional[face] : companion;
    for (int j = 0; j < FOLLOWER; ++j) {
        for (int i = 0; i < FOLLOWER; ++i) {
            uint32_t c = frame[j * FOLLOWER + i];
            if ((c >> 24) >= 128)
                dot(x + i, y + j, from_argb(c));
        }
    }
}

static bool update_images(void)
{
    char path[GW_STYLE_MAX_PATH * 2];
    custom_bg = false;
    custom_sprite = false;
    for (int face = 0; face < GW_FACE_COUNT; ++face)
        has_direction[face] = false;
    if (strcmp(preferences.menus, "classic") &&
        gw_styles_find(&library, "menus", preferences.menus, "menus/background",
                       path, sizeof(path))) {
        if (!gw_host_read_image_argb(path, background, W, H))
            return false;
        custom_bg = true;
    }
    if (strcmp(preferences.sprites, "classic") &&
        gw_styles_find(&library, "sprites", preferences.sprites, "sprites/follower",
                       path, sizeof(path))) {
        if (!gw_host_read_image_argb(path, companion, FOLLOWER, FOLLOWER))
            return false;
        custom_sprite = true;
        for (int face = 0; face < GW_FACE_COUNT; ++face) {
            char logical[64];
            snprintf(logical, sizeof(logical), "sprites/follower/%s",
                     gw_follower_direction_name((GWFace8)face));
            /* The baseline follower sprite is the fallback for partial packs. */
            if (gw_styles_find(&library, "sprites", preferences.sprites,
                               logical, path, sizeof(path))) {
                if (!gw_host_read_image_argb(path, directional[face], FOLLOWER, FOLLOWER))
                    return false;
                has_direction[face] = true;
            }
        }
    }
    return true;
}

static void paint(int px, int py, int fx, int fy, GWFace8 facing, bool settings, int category)
{
    if (custom_bg) {
        for (int i = 0; i < W * H; ++i)
            screen[i] = ((background[i] >> 24) >= 128)
                        ? from_argb(background[i]) : color555(46,93,58);
    } else {
        fill_default();
    }
    rect(px - 5, py - 10, 10, 16, color555(49,85,182));
    rect(px - 6, py - 14, 12, 5, color555(180,49,63));
    draw_companion(fx - FOLLOWER / 2, fy - FOLLOWER / 2, facing);

    if (!settings) {
        rect(4, 4, 202, 24, color555(23,49,55));
        line_text(10, 8, "GRAND WORLD NATIVE STYLE LAB", color555(235,246,214));
        line_text(10, 18, "F1: STYLES  F5: RELOAD", color555(197,207,160));
        char direction_text[32];
        snprintf(direction_text, sizeof(direction_text), "FOLLOWER LOOK: %s",
                 gw_follower_direction_name(facing));
        rect(4, 146, 142, 12, color555(23,49,55));
        line_text(10, 149, direction_text, color555(235,246,214));
        return;
    }
    rect(6, 7, 228, 132, color555(21,43,52));
    rect(10, 11, 220, 16, color555(55,101,111));
    line_text(18, 15, "STYLE SETTINGS - EXPERIMENT", color555(248,239,185));
    line_text(14, 32, "UP DOWN: CHOOSE", color555(180,206,201));
    line_text(14, 42, "LEFT RIGHT: CHANGE", color555(180,206,201));
    for (int row = 0; row < 2; ++row) {
        const int y = 58 + row * 23;
        const char *name = row == 0 ? "MENU" : "FOLLOWER";
        const char *value = row == 0 ? preferences.menus : preferences.sprites;
        if (category == row)
            rect(12, y - 3, 214, 19, color555(47,83,113));
        line_text(18, y, name, color555(245,229,160));
        line_text(78, y, value, color555(242,250,240));
    }
    line_text(14, 110, "F5 REFRESH  F1 CLOSE", color555(190,225,184));
    line_text(14, 122, "TEST HOST - NO GAMEPLAY", color555(230,166,157));
}

/* Reload all packs and style preferences as one change. If the updated
 * catalog is corrupt or a PNG cannot be decoded, keep the last working
 * index, preferences and rendered assets. This changes no Pokemon saves. */
typedef struct {
    uint32_t bg[W * H];
    uint32_t follower[FOLLOWER * FOLLOWER];
    uint32_t directions[GW_FACE_COUNT][FOLLOWER * FOLLOWER];
    bool has_direction[GW_FACE_COUNT];
    bool has_bg, has_sprite;
} GWVisualSnapshot;

static bool reload_styles(const char *root)
{
    GWStyleIndex *candidate = malloc(sizeof(*candidate));
    GWStyleIndex *previous = NULL;
    GWVisualSnapshot *snapshot = NULL;
    GWStylePrefs next_prefs, old_prefs;
    bool good = false;
    if (!candidate)
        return false;
    if (!gw_styles_load(candidate, root) ||
        !gw_styles_read_prefs(candidate, &next_prefs))
        goto finish;
    previous = malloc(sizeof(*previous));
    snapshot = malloc(sizeof(*snapshot));
    if (!previous || !snapshot)
        goto finish;
    memcpy(previous, &library, sizeof(library));
    old_prefs = preferences;
    memcpy(snapshot->bg, background, sizeof(background));
    memcpy(snapshot->follower, companion, sizeof(companion));
    memcpy(snapshot->directions, directional, sizeof(directional));
    memcpy(snapshot->has_direction, has_direction, sizeof(has_direction));
    snapshot->has_bg = custom_bg;
    snapshot->has_sprite = custom_sprite;

    memcpy(&library, candidate, sizeof(library));
    preferences = next_prefs;
    if (!update_images()) {
        memcpy(&library, previous, sizeof(library));
        preferences = old_prefs;
        /* Do not reopen old resources: they may have been deleted meanwhile. */
        memcpy(background, snapshot->bg, sizeof(background));
        memcpy(companion, snapshot->follower, sizeof(companion));
        memcpy(directional, snapshot->directions, sizeof(directional));
        memcpy(has_direction, snapshot->has_direction, sizeof(has_direction));
        custom_bg = snapshot->has_bg;
        custom_sprite = snapshot->has_sprite;
        goto finish;
    }
    good = true;
finish:
    free(snapshot);
    free(previous);
    free(candidate);
    return good;
}

static bool style_advance(int category, int direction)
{
    const char *kind = category == 0 ? "menus" : "sprites";
    const char *logical = category == 0 ? "menus/background" : "sprites/follower";
    GWStylePrefs before = preferences;
    char *selected = category == 0 ? preferences.menus : preferences.sprites;
    size_t total = gw_styles_options(&library, kind, logical);
    size_t position = 0;
    for (size_t i = 0; i < total; ++i) {
        if (!strcmp(gw_styles_option(&library, kind, logical, i), selected)) {
            position = i;
            break;
        }
    }
    if (!total)
        return false;
    position = (position + (direction > 0 ? 1 : total - 1)) % total;
    const char *choice = gw_styles_option(&library, kind, logical, position);
    strncpy(selected, choice, GW_STYLE_MAX_PACK_ID - 1);
    selected[GW_STYLE_MAX_PACK_ID - 1] = 0;
    if (update_images() && gw_styles_write_prefs(&library, &preferences))
        return true;
    /* A corrupt mod must not replace working settings or leave a blank sprite. */
    preferences = before;
    update_images();
    return false;
}

int main(int argc, char **argv)
{
    const char *root = "mods";
    bool selftest = false, settings = false, last_f1 = false, last_f5 = false;
    int category = 0, px = 120, py = 78;
    int fx = 87, fy = 108, frames = 0;
    GWFace8 facing = GW_FACE_NE;
    uint16_t oldkeys = 0;
    GWNativeHost *host;
    SDL_SetMainReady();
    for (int i = 1; i < argc; ++i) {
        if (!strcmp(argv[i], "--mods") && i + 1 < argc) root = argv[++i];
        else if (!strcmp(argv[i], "--selftest")) selftest = true;
        else {
            fprintf(stderr, "Usage: gw_theme_lab [--mods PATH] [--selftest]\n");
            return 2;
        }
    }
    if (!gw_styles_load(&library, root) ||
        !gw_styles_read_prefs(&library, &preferences)) {
        fprintf(stderr, "Invalid style index or preferences under %s\n", root);
        return 3;
    }
    host = gw_host_open("Grand World Native: Style Lab (NOT GAMEPLAY)",
                        3, selftest);
    if (!host) {
        fprintf(stderr, "SDL2 could not initialize\n");
        return 4;
    }
    if (!update_images()) {
        fprintf(stderr, "Active theme resource could not be decoded\n");
        gw_host_close(host);
        return 5;
    }
    if (selftest) {
        for (int kind = 0; kind < 2; ++kind) {
            const char *category_name = kind ? "sprites" : "menus";
            const char *logical = kind ? "sprites/follower" : "menus/background";
            size_t options = gw_styles_options(&library, category_name, logical);
            for (size_t i = 1; i < options; ++i) {
                char path[GW_STYLE_MAX_PATH * 2];
                static uint32_t scratch[W * H];
                if (!gw_styles_find(&library, category_name,
                    gw_styles_option(&library, category_name, logical, i),
                    logical, path, sizeof(path)) ||
                    !gw_host_read_image_argb(path, scratch,
                         kind ? FOLLOWER : W, kind ? FOLLOWER : H)) {
                    fprintf(stderr, "Invalid enabled image resource: %s\n", logical);
                    gw_host_close(host);
                    return 6;
                }
            }
        }
        for (int face = 0; face < GW_FACE_COUNT; ++face) {
            char id[64], resolved[GW_STYLE_MAX_PATH * 2];
            const char *pack = preferences.sprites;
            snprintf(id, sizeof(id), "sprites/follower/%s",
                     gw_follower_direction_name((GWFace8)face));
            if (strcmp(pack, "classic") &&
                gw_styles_find(&library, "sprites", pack, id,
                               resolved, sizeof(resolved))) {
                static uint32_t scratch_pose[FOLLOWER * FOLLOWER];
                if (!gw_host_read_image_argb(resolved, scratch_pose, FOLLOWER, FOLLOWER)) {
                    fprintf(stderr, "FAIL: cannot load eight-direction pose %s\\n", id);
                    gw_host_close(host);
                    return 8;
                }
            }
        }
        paint(px, py, fx, fy, facing, true, 0);
        if (!gw_host_present_rgb555(host, screen, W)) {
            gw_host_close(host);
            return 7;
        }
        printf("PASS: mod asset catalog, menu sprite resolution, SDL2 UI frame\n");
        gw_host_close(host);
        return 0;
    }

    for (; gw_host_poll(host); SDL_Delay(16)) {
        const uint16_t keys = gw_host_keys(host);
        const uint16_t press = (uint16_t)(keys & ~oldkeys);
        const Uint8 *key_state = SDL_GetKeyboardState(NULL);
        const bool f1 = key_state[SDL_SCANCODE_F1] != 0;
        const bool f5 = key_state[SDL_SCANCODE_F5] != 0;
        const bool esc = key_state[SDL_SCANCODE_ESCAPE] != 0;
        if (f1 && !last_f1) settings = !settings;
        if (f5 && !last_f5 && !reload_styles(root))
            fprintf(stderr, "Could not reload mods: previous styles preserved\\n");
        if (settings) {
            if (press & (GW_KEY_UP | GW_KEY_DOWN)) category ^= 1;
            if ((press & GW_KEY_LEFT) && !style_advance(category, -1))
                fprintf(stderr, "Could not persist style selection\n");
            if ((press & GW_KEY_RIGHT) && !style_advance(category, 1))
                fprintf(stderr, "Could not persist style selection\n");
            if (esc) settings = false;
        } else {
            if (keys & GW_KEY_LEFT) px--;
            if (keys & GW_KEY_RIGHT) px++;
            if (keys & GW_KEY_UP) py--;
            if (keys & GW_KEY_DOWN) py++;
            if (px < 40) px = 40;
            if (px > W - 8) px = W - 8;
            if (py < 20) py = 20;
            if (py > H - 20) py = H - 20;
        }
        /* Follower moves only along one grid axis at a time, while its body
           can look diagonally toward the player's current position. */
        if (!settings && ++frames % 3 == 0) {
            int dx = px - fx, dy = py - fy;
            if (abs(dx) > 28 || abs(dy) > 28) {
                if (abs(dx) >= abs(dy)) fx += dx > 0 ? 2 : -2;
                else fy += dy > 0 ? 2 : -2;
            }
        }
        facing = gw_follower_look_at(px - fx, py - fy, facing, 5);
        paint(px, py, fx, fy, facing, settings, category);
        if (!gw_host_present_rgb555(host, screen, W))
            break;
        oldkeys = keys;
        last_f1 = f1;
        last_f5 = f5;
    }
    gw_host_close(host);
    return 0;
}
