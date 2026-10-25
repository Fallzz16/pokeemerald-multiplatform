/* Native preferences integration test with real installed demo mod packs.
 * Runs without launching the Pokemon engine and never touches game saves.
 */
#include "gw_style_index.h"
#include <stdio.h>
#include <string.h>

static GWStyleIndex index_data;
static GWStyleIndex no_packs;

static int check_prefs(const char *expected_menu, const char *expected_sprite)
{
    GWStylePrefs prefs;
    if (!gw_styles_read_prefs(&index_data, &prefs))
        return 0;
    return strcmp(prefs.menus, expected_menu) == 0
        && strcmp(prefs.sprites, expected_sprite) == 0;
}

int main(int argc, char **argv)
{
    GWStylePrefs original;
    GWStylePrefs prefs;
    const char *menu_pack, *sprite_pack;
    char resolved[GW_STYLE_MAX_PATH * 2];
    int result = 1;
    int modified = 0;
    if (argc != 2 || !gw_styles_load(&index_data, argv[1]) ||
        !gw_styles_read_prefs(&index_data, &original)) {
        fprintf(stderr, "FAIL: mod root or preferences cannot be read\n");
        return 2;
    }
    if (gw_styles_options(&index_data, "menus", "menus/background") < 2 ||
        gw_styles_options(&index_data, "sprites", "sprites/follower") < 2) {
        fprintf(stderr, "FAIL: expected installed demo menu + sprite pack\n");
        return 3;
    }
    menu_pack = gw_styles_option(&index_data, "menus", "menus/background", 1);
    sprite_pack = gw_styles_option(&index_data, "sprites", "sprites/follower", 1);
    if (!strcmp(menu_pack, "classic") || !strcmp(sprite_pack, "classic") ||
        !gw_styles_find(&index_data, "menus", menu_pack, "menus/background",
                        resolved, sizeof(resolved)) ||
        !gw_styles_find(&index_data, "sprites", sprite_pack, "sprites/follower",
                        resolved, sizeof(resolved)))
        return 4;

    strcpy(prefs.menus, "classic");
    strcpy(prefs.sprites, "classic");
    modified = 1;
    if (!gw_styles_write_prefs(&index_data, &prefs) ||
        !check_prefs("classic", "classic")) {
        fprintf(stderr, "FAIL: classic choice persistence\n");
        goto restore;
    }
    strncpy(prefs.menus, menu_pack, sizeof(prefs.menus) - 1);
    prefs.menus[sizeof(prefs.menus) - 1] = 0;
    strncpy(prefs.sprites, sprite_pack, sizeof(prefs.sprites) - 1);
    prefs.sprites[sizeof(prefs.sprites) - 1] = 0;
    if (!gw_styles_write_prefs(&index_data, &prefs) ||
        !check_prefs(menu_pack, sprite_pack)) {
        fprintf(stderr, "FAIL: modded choice persistence\n");
        goto restore;
    }
    /* If a pack is disabled, stale settings safely revert to classic.
       This fallback is read-only and does not mutate the actual catalog. */
    no_packs = index_data;
    no_packs.count = 0;
    if (!gw_styles_read_prefs(&no_packs, &prefs) ||
        strcmp(prefs.menus, "classic") || strcmp(prefs.sprites, "classic")) {
        fprintf(stderr, "FAIL: unavailable pack fallback\n");
        goto restore;
    }
    puts("PASS: catalog lookup, classic/mod style persistence and fallback");
    result = 0;
restore:
    if (modified && !gw_styles_write_prefs(&index_data, &original)) {
        fprintf(stderr, "FAIL: could not restore original cosmetic settings\n");
        return 5;
    }
    return result;
}
