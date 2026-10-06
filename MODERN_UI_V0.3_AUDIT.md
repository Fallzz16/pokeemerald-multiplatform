# Emerald Vanilla+ v0.3 — Modern UI Audit

v0.3 is a presentation-only evolution of v0.2. It intentionally changes UI palette assets and a small read-only UI integration surface while leaving game content and rules untouched.

## Runtime/source changes

- `graphics/party_menu/bg.png`
- `graphics/summary_screen/tiles.png`
- `graphics/pokedex/bg_hoenn.pal`
- `graphics/pokedex/bg_national.pal`
- `graphics/pokedex/search_menu.pal`
- `graphics/pokedex/search_results_bg.pal`
- `include/quest_log.h`
- `src/quest_log.c`
- `src/start_menu.c`
- `src/pokenav_region_map.c`

## Project metadata / QA

- `README.md`
- `docs/MODERN_UI_V0.3.md`
- `docs/modern-ui-v0.3-preserved.sha256`
- `scripts/verify_modern_ui.sh`
- `scripts/verify_vanilla.sh` (routes to the current v0.3 verifier)
- `.github/workflows/build-windows-native.yml`

No maps, event scripts, Pokémon data, trainers, encounters, battle logic, music or sound-effect assets are part of the approved v0.3 change surface.

## QA status

- v0.3 preservation verifier: **PASS**.
- `quest_log.c` host syntax check after charmap preprocessing: **PASS**.
- `start_menu.c` host syntax check after charmap preprocessing: **PASS**.
- `pokenav_region_map.c` host syntax check after generation of its standard graphics dependencies and charmap preprocessing: **PASS**.
- Party and Summary indexed PNG topology/used palette-index sets match v0.2; only palette/color presentation changed.
- Party, Summary and Pokédex edited sources regenerated successfully through the project's `gbagfx` pipeline.
- Regression caught during QA: Story Status window remained present when entering normal Save flow. Fixed by clearing auxiliary Start Menu windows before `SaveStartCallback`; re-verified after the fix.
- Final Windows link/runtime playtest remains pending because the sandbox lacks the 32-bit MinGW/SDL2 Windows toolchain. The included GitHub Actions workflow performs that build.
