#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

required=(
  include/quest_log.h
  src/quest_log.c
  src/start_menu.c
  src/menu.c
  src/pokenav_region_map.c
  docs/vanillaplus-v0.2-preserved.sha256
)

for path in "${required[@]}"; do
    if [[ ! -f "$path" ]]; then
        echo "ERROR: required Vanilla+ v0.2 file missing: $path"
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

sha256sum -c docs/vanillaplus-v0.2-preserved.sha256 >/dev/null

grep -q 'MENU_ACTION_QUESTS' src/start_menu.c
grep -q 'QuestLog_GetCurrentTargetMapSecId' src/pokenav_region_map.c
grep -q 'FLAG_IS_CHAMPION' src/quest_log.c

echo "Emerald Vanilla+ v0.2 verification passed."
