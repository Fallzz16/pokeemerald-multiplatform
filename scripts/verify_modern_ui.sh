#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

required=(
  graphics/party_menu/bg.png
  graphics/summary_screen/tiles.png
  graphics/pokedex/bg_hoenn.pal
  graphics/pokedex/bg_national.pal
  graphics/pokedex/search_menu.pal
  graphics/pokedex/search_results_bg.pal
  include/quest_log.h
  src/quest_log.c
  src/start_menu.c
  src/pokenav_region_map.c
  docs/modern-ui-v0.3-preserved.sha256
)

for path in "${required[@]}"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required Modern UI v0.3 file missing: $path"
        exit 1
    fi
done

if grep -RIlE 'Voxel Engine|ModManager|ROM Hack Importer|DISPLAY page' src include data graphics sound 2>/dev/null | grep -q .; then
    echo "ERROR: post-baseline experimental feature markers were found."
    exit 1
fi

if grep -Eq '\bspeedUp\b|\bpaused\b|\btimeScale\b|SDLK_SPACE|SDLK_p|SDLK_r' src/platform/sdl2.c; then
    echo "ERROR: desktop-only speed/pause/reset shortcuts are present in the active SDL2 backend."
    exit 1
fi

sha256sum -c docs/modern-ui-v0.3-preserved.sha256 >/dev/null

grep -q 'MENU_ACTION_QUESTS' src/start_menu.c
grep -q 'sWindowTemplate_StoryStatus' src/start_menu.c
grep -q 'QuestLog_GetStoryProgress' src/quest_log.c
grep -q 'FLAG_IS_CHAMPION' src/quest_log.c
grep -q 'RGB(31, 27, 10)' src/pokenav_region_map.c

echo "Emerald Vanilla+ v0.3 Classic Enhanced verification passed."
