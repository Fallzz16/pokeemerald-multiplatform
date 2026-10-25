#include "gw_style_index.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define GW_PREFIX "GW_ASSETS_V1"

static bool copy_checked(char *to, size_t size, const char *from)
{
    size_t length;
    if (!to || !from || !size)
        return false;
    length = strlen(from);
    if (length == 0 || length >= size)
        return false;
    memcpy(to, from, length + 1);
    return true;
}

static bool simple_id(const char *s, bool slashes)
{
    size_t n;
    if (!s || !*s || (n = strlen(s)) > 128)
        return false;
    if (s[0] == '/' || strstr(s, "//") || strstr(s, ".."))
        return false;
    for (size_t i = 0; i < n; ++i) {
        const char c = s[i];
        if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') ||
            c == '.' || c == '_' || c == '-' || (slashes && c == '/'))
            continue;
        return false;
    }
    return true;
}

static bool safe_relative(const char *s)
{
    if (!simple_id(s, true) || strlen(s) >= GW_STYLE_MAX_PATH)
        return false;
    if (s[0] == '/' || strstr(s, "/.") || strstr(s, ".."))
        return false;
    return true;
}

static bool join_path(const char *root, const char *relative, char *out, size_t size)
{
    int bytes;
    if (!safe_relative(relative))
        return false;
    bytes = snprintf(out, size, "%s/%s", root, relative);
    return bytes > 0 && (size_t)bytes < size;
}

bool gw_styles_load(GWStyleIndex *index, const char *root)
{
    char path[GW_STYLE_MAX_PATH * 2], line[GW_STYLE_MAX_PATH + 256];
    FILE *file = NULL;
    if (!index || !root || !*root)
        return false;
    memset(index, 0, sizeof(*index));
    if (!copy_checked(index->root, sizeof(index->root), root))
        return false;
    if (snprintf(path, sizeof(path), "%s/runtime-assets.tsv", root) >= (int)sizeof(path))
        return false;
    file = fopen(path, "rb");
    if (!file)
        return true; /* No packs installed is a valid classic-only setup. */
    if (!fgets(line, sizeof(line), file) || strcmp(line, GW_PREFIX "\n") != 0) {
        fclose(file);
        return false;
    }
    while (fgets(line, sizeof(line), file)) {
        GWStyleAsset *entry;
        char *fields[4] = {NULL, NULL, NULL, NULL};
        char *cursor = line;
        size_t len = strlen(line);
        if (!len || line[len - 1] != '\n' || index->count == GW_STYLE_MAX_ASSETS)
            goto failure;
        line[len - 1] = 0;
        for (size_t k = 0; k < 3; ++k) {
            char *sep = strchr(cursor, '\t');
            if (!sep)
                goto failure;
            *sep = 0;
            fields[k] = cursor;
            cursor = sep + 1;
        }
        fields[3] = cursor;
        if (strchr(cursor, '\t') || !simple_id(fields[1], false) ||
            !simple_id(fields[2], true) || !safe_relative(fields[3]))
            goto failure;
        if (strcmp(fields[0], "menus") && strcmp(fields[0], "sprites") &&
            strcmp(fields[0], "tiles") && strcmp(fields[0], "audio"))
            goto failure;
        if (strncmp(fields[3], fields[1], strlen(fields[1])) != 0 ||
            fields[3][strlen(fields[1])] != '/')
            goto failure;
        entry = &index->assets[index->count];
        if (!copy_checked(entry->kind, sizeof(entry->kind), fields[0]) ||
            !copy_checked(entry->pack, sizeof(entry->pack), fields[1]) ||
            !copy_checked(entry->logical, sizeof(entry->logical), fields[2]) ||
            !copy_checked(entry->relative, sizeof(entry->relative), fields[3]))
            goto failure;
        index->count++;
    }
    if (ferror(file))
        goto failure;
    fclose(file);
    return true;
failure:
    fclose(file);
    memset(index, 0, sizeof(*index));
    return false;
}

const char *gw_styles_find(const GWStyleIndex *index,
                           const char *kind, const char *pack, const char *logical,
                           char *path, size_t path_capacity)
{
    if (!index || !path || !kind || !pack || !logical)
        return NULL;
    if (!simple_id(pack, false) || !simple_id(logical, true))
        return NULL;
    for (size_t i = 0; i < index->count; ++i) {
        const GWStyleAsset *e = &index->assets[i];
        if (!strcmp(e->kind, kind) && !strcmp(e->pack, pack) &&
            !strcmp(e->logical, logical) &&
            join_path(index->root, e->relative, path, path_capacity))
            return path;
    }
    return NULL;
}

size_t gw_styles_options(const GWStyleIndex *index, const char *kind,
                         const char *logical)
{
    size_t options = 1;
    if (!index)
        return 1;
    for (size_t i = 0; i < index->count; ++i) {
        const GWStyleAsset *e = &index->assets[i];
        bool seen = false;
        if (strcmp(e->kind, kind) || strcmp(e->logical, logical))
            continue;
        for (size_t j = 0; j < i; ++j) {
            if (!strcmp(index->assets[j].kind, kind) &&
                !strcmp(index->assets[j].logical, logical) &&
                !strcmp(index->assets[j].pack, e->pack)) {
                seen = true;
                break;
            }
        }
        if (!seen) options++;
    }
    return options;
}

const char *gw_styles_option(const GWStyleIndex *index, const char *kind,
                             const char *logical, size_t choice)
{
    if (choice == 0 || !index)
        return "classic";
    for (size_t i = 0; i < index->count; ++i) {
        const GWStyleAsset *e = &index->assets[i];
        bool seen = false;
        if (strcmp(e->kind, kind) || strcmp(e->logical, logical))
            continue;
        for (size_t j = 0; j < i; ++j) {
            if (!strcmp(index->assets[j].kind, kind) &&
                !strcmp(index->assets[j].logical, logical) &&
                !strcmp(index->assets[j].pack, e->pack)) {
                seen = true;
                break;
            }
        }
        if (!seen && --choice == 0)
            return e->pack;
    }
    return "classic";
}

bool gw_styles_read_prefs(const GWStyleIndex *index, GWStylePrefs *prefs)
{
    char path[GW_STYLE_MAX_PATH * 2], buffer[128];
    FILE *file;
    if (!index || !prefs)
        return false;
    strcpy(prefs->menus, "classic");
    strcpy(prefs->sprites, "classic");
    if (snprintf(path, sizeof(path), "%s/style-settings.ini", index->root) >= (int)sizeof(path))
        return false;
    file = fopen(path, "rb");
    if (!file)
        return true;
    if (!fgets(buffer, sizeof(buffer), file) || strcmp(buffer, "GW_STYLE_V1\n")) {
        fclose(file);
        return false;
    }
    while (fgets(buffer, sizeof(buffer), file)) {
        char *sep = strchr(buffer, '=');
        char *value;
        if (!sep)
            continue;
        *sep = 0;
        value = sep + 1;
        value[strcspn(value, "\r\n")] = 0;
        if (strcmp(value, "classic") && !simple_id(value, false))
            continue;
        if (!strcmp(buffer, "menus"))
            copy_checked(prefs->menus, sizeof(prefs->menus), value);
        if (!strcmp(buffer, "sprites"))
            copy_checked(prefs->sprites, sizeof(prefs->sprites), value);
    }
    fclose(file);
    /* Graceful fallback after packs are removed or disabled. */
    bool menu_exists = !strcmp(prefs->menus, "classic");
    bool sprite_exists = !strcmp(prefs->sprites, "classic");
    for (size_t i = 0; i < index->count; ++i) {
        if (!strcmp(index->assets[i].pack, prefs->menus) &&
            !strcmp(index->assets[i].kind, "menus") &&
            !strcmp(index->assets[i].logical, "menus/background"))
            menu_exists = true;
        if (!strcmp(index->assets[i].pack, prefs->sprites) &&
            !strcmp(index->assets[i].kind, "sprites") &&
            !strcmp(index->assets[i].logical, "sprites/follower"))
            sprite_exists = true;
    }
    if (!menu_exists) strcpy(prefs->menus, "classic");
    if (!sprite_exists) strcpy(prefs->sprites, "classic");
    return true;
}

bool gw_styles_write_prefs(const GWStyleIndex *index, const GWStylePrefs *prefs)
{
    char target[GW_STYLE_MAX_PATH * 2], staging[GW_STYLE_MAX_PATH * 2];
    FILE *file;
    if (!index || !prefs ||
        (!simple_id(prefs->menus, false) && strcmp(prefs->menus, "classic")) ||
        (!simple_id(prefs->sprites, false) && strcmp(prefs->sprites, "classic")))
        return false;
    if (snprintf(target, sizeof(target), "%s/style-settings.ini", index->root) >= (int)sizeof(target) ||
        snprintf(staging, sizeof(staging), "%s/style-settings.tmp", index->root) >= (int)sizeof(staging))
        return false;
    file = fopen(staging, "wb");
    if (!file)
        return false;
    if (fprintf(file, "GW_STYLE_V1\nmenus=%s\nsprites=%s\n", prefs->menus, prefs->sprites) < 0) {
        fclose(file);
        remove(staging);
        return false;
    }
    if (fclose(file) != 0) {
        remove(staging);
        return false;
    }
    if (rename(staging, target) == 0)
        return true;
#ifdef _WIN32
    /* Win32 CRT rename does not replace existing files. Cosmetic settings only. */
    if (remove(target) == 0 && rename(staging, target) == 0)
        return true;
#endif
    remove(staging);
    return false;
}
