# Emerald Vanilla+ v0.2 — Implementation & QA Audit

## Product decisions

The v0.2 feature set follows these locked decisions:

- Main-story quests only; no side-quest tracker.
- Guidance level: objective + city/route/dungeon.
- PokéNav marker: approximate region, not exact NPC/path GPS.
- Completed main-story milestones remain viewable.
- “What was I doing?” resume reminder enabled.
- Product name: **Emerald Vanilla+**.

## Architecture

The tracker is deliberately read-only with respect to story progression. It does not replace event scripts and it does not create a parallel quest progression variable. Instead, `src/quest_log.c` evaluates the flags, variables and badges already used by Pokémon Emerald.

This has three practical benefits:

1. Story scripts remain authoritative.
2. Existing saves can immediately resolve their current objective.
3. A failed or skipped UI interaction cannot block campaign progression.

## Main-story milestones

| # | Milestone | Completion signal | Approximate target |
| ---: | --- | --- | --- |
| 1 | A Professor in Trouble | `FLAG_RESCUED_BIRCH` | Route 101 |
| 2 | Your First Rival Battle | `FLAG_RECEIVED_POKEDEX_FROM_BIRCH` | Route 103 / Littleroot |
| 3 | A Visit to Petalburg | `VAR_PETALBURG_GYM_STATE >= 2` | Petalburg City |
| 4 | The Stone Badge | `FLAG_BADGE01_GET` | Rustboro City |
| 5 | Stolen Devon Goods | `FLAG_RETURNED_DEVON_GOODS` | Route 116 / Rusturf Tunnel |
| 6 | The Knuckle Badge | `FLAG_BADGE02_GET` | Dewford Town |
| 7 | Letter for Steven | `FLAG_DELIVERED_STEVEN_LETTER` | Granite Cave |
| 8 | Deliver the Devon Goods | `FLAG_DELIVERED_DEVON_GOODS` | Slateport City |
| 9 | The Dynamo Badge | `FLAG_BADGE03_GET` | Mauville City |
| 10 | Trouble at Mt. Chimney | `FLAG_DEFEATED_EVIL_TEAM_MT_CHIMNEY` | Meteor Falls → Mt. Chimney |
| 11 | The Heat Badge | `FLAG_BADGE04_GET` | Lavaridge Town |
| 12 | The Balance Badge | `FLAG_BADGE05_GET` | Petalburg City |
| 13 | Storm at the Institute | `VAR_WEATHER_INSTITUTE_STATE >= 1` | Route 119 |
| 14 | The Invisible Obstacle | `FLAG_RECEIVED_DEVON_SCOPE` | Route 120 |
| 15 | The Feather Badge | `FLAG_BADGE06_GET` | Fortree City |
| 16 | The Orbs of Mt. Pyre | `VAR_MT_PYRE_STATE >= 1` | Mt. Pyre |
| 17 | Team Magma's Hideout | `VAR_SLATEPORT_HARBOR_STATE >= 1` | Magma Hideout |
| 18 | The Stolen Submarine | `VAR_SLATEPORT_HARBOR_STATE >= 2` | Slateport City |
| 19 | Team Aqua's Hideout | `FLAG_TEAM_AQUA_ESCAPED_IN_SUBMARINE` | Aqua Hideout / Lilycove |
| 20 | The Mind Badge | `FLAG_BADGE07_GET` | Mossdeep City |
| 21 | Attack on the Space Center | `VAR_MOSSDEEP_SPACE_CENTER_STATE >= 3` | Mossdeep City |
| 22 | The Deep Sea | `FLAG_RECEIVED_HM_DIVE` | Mossdeep City |
| 23 | Beneath Route 128 | `FLAG_KYOGRE_ESCAPED_SEAFLOOR_CAVERN` | Seafloor Cavern |
| 24 | A City in Crisis | `FLAG_WALLACE_GOES_TO_SKY_PILLAR` | Sootopolis City |
| 25 | Seek the Sky Dragon | `VAR_SKY_PILLAR_STATE >= 1` | Sky Pillar |
| 26 | Return to Sootopolis | `VAR_SKY_PILLAR_STATE >= 2` | Sootopolis City |
| 27 | The Rain Badge | `FLAG_BADGE08_GET` | Sootopolis City |
| 28 | Victory Road | `FLAG_DEFEATED_WALLY_VICTORY_ROAD` | Victory Road |
| 29 | The Pokémon League | `FLAG_IS_CHAMPION` | Ever Grande City |

For the Mt. Chimney objective, `FLAG_MET_ARCHIE_METEOR_FALLS` is also used to move the PokéNav target from Meteor Falls to Mt. Chimney once the story has advanced to that stage.

## Files intentionally changed/added in v0.2

Gameplay/UI integration:

- `include/quest_log.h` — public Quest Log interface.
- `src/quest_log.c` — milestone resolution and Quest Log UI.
- `src/start_menu.c` — adds `QUESTS` to the normal Start Menu and returns cleanly to it.
- `src/menu.c` — safely accommodates nine normal Start Menu entries.
- `src/pokenav_region_map.c` — blinking approximate objective marker.

Project/QA metadata:

- `README.md`
- `VANILLAPLUS_V0.2_AUDIT.md`
- `docs/vanillaplus-v0.2-preserved.sha256`
- `scripts/verify_vanillaplus.sh`
- `.github/workflows/build-windows-native.yml`

## UI safety checks

- The normal Start Menu maximum remains within `sCurrentStartMenuActions[9]`.
- Nine Start Menu rows use the full 144-pixel content area without adding a tenth slot.
- The Quest Log uses a 28×18 window and only opens from the normal field Start Menu.
- Quest state is not written into SaveBlock structures, avoiding save-format changes.
- Completed list scrolling is bounded by the count of resolved milestones.
- The PokéNav marker uses unique sprite tile/palette tags and frees both on region-map teardown.
- The marker hides when outside the visible zoomed map and blinks at a fixed interval.

## Static validation performed

- `src/quest_log.c`: passed the project character-map preprocessor and host C syntax check.
- `src/start_menu.c`: passed the project character-map preprocessor and host C syntax check.
- `src/menu.c`: passed asset-safe host C syntax check.
- `src/pokenav_region_map.c`: passed asset-safe host C syntax check.
- Quest text passed the Emerald character-map converter, including `POKéMON` encoding.
- Generated build files/tool binaries created during QA were removed before packaging.

## Preservation verification

`docs/vanillaplus-v0.2-preserved.sha256` hashes every file from the v0.1 source package except the explicitly approved v0.2 integration files/project metadata. `scripts/verify_vanillaplus.sh` validates this manifest.

This means maps, encounter tables, trainers, species data, move/item data, dialogue scripts, battle logic, graphics, music and sound-effect assets remain unchanged from the v0.1 Vanilla Native source package.

## Runtime status

The current sandbox does not provide the 32-bit MinGW + SDL2 Windows link environment, so a real `pokeemerald.exe` runtime playtest is still pending. The included GitHub Actions workflow is configured to perform the Windows build and upload a portable artifact.

### Required first runtime QA

1. Open Start Menu at game start and after all normal menu systems are unlocked.
2. Open/close `QUESTS` repeatedly and verify cursor restoration.
3. Validate CURRENT objective on representative saves from early, mid and late game.
4. Validate non-linear Brawly/Steven ordering.
5. Scroll COMPLETED with 0, 1, 6, 7 and 29 completed milestones.
6. Open PokéNav before/after key progression changes and confirm approximate marker placement.
7. Zoom/pan PokéNav and confirm marker follows map transform and hides offscreen.
8. Save/reload and confirm the same quest is derived without any quest-specific save state.
9. Finish the League and confirm `MAIN STORY COMPLETE!` with no active marker.
