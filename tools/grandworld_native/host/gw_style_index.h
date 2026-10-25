#ifndef GW_STYLE_INDEX_H
#define GW_STYLE_INDEX_H
#include <stdbool.h>
#include <stddef.h>

#define GW_STYLE_MAX_ASSETS 2048
#define GW_STYLE_MAX_PACK_ID 65
#define GW_STYLE_MAX_LOGICAL_ID 129
#define GW_STYLE_MAX_PATH 512

typedef struct {
    char kind[16];
    char pack[GW_STYLE_MAX_PACK_ID];
    char logical[GW_STYLE_MAX_LOGICAL_ID];
    char relative[GW_STYLE_MAX_PATH];
} GWStyleAsset;

typedef struct {
    char root[GW_STYLE_MAX_PATH];
    GWStyleAsset assets[GW_STYLE_MAX_ASSETS];
    size_t count;
} GWStyleIndex;

typedef struct {
    char menus[GW_STYLE_MAX_PACK_ID];
    char sprites[GW_STYLE_MAX_PACK_ID];
} GWStylePrefs;

bool gw_styles_load(GWStyleIndex *index, const char *root);
const char *gw_styles_find(const GWStyleIndex *index,
                           const char *kind, const char *pack, const char *logical,
                           char *path, size_t path_capacity);
size_t gw_styles_options(const GWStyleIndex *index, const char *kind,
                          const char *logical);
const char *gw_styles_option(const GWStyleIndex *index, const char *kind,
                             const char *logical, size_t choice);
bool gw_styles_read_prefs(const GWStyleIndex *index, GWStylePrefs *prefs);
bool gw_styles_write_prefs(const GWStyleIndex *index, const GWStylePrefs *prefs);

#endif
