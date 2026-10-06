# Emerald Vanilla+ v0.3 — Classic Enhanced UI

## Locked design decisions

- Style: **Classic Enhanced**.
- First-pass focus: **Pokédex + Party + Pokémon Summary**.
- Fidelity: maximum Emerald fidelity; improve presentation, not mechanics.
- Quest Log and Start Menu are visually integrated in the same pass.
- PokéNav objective marker is harmonized with the new palette.
- PC Storage is intentionally deferred to the second UI pass.

## Design system

The project stays at the original 240×160 logical presentation and keeps the original pixel grid. No HD/vector overlay is introduced.

### Core colors

- Deep Emerald / Teal — main chrome and background surfaces.
- Warm Ivory — content cards and readable information surfaces.
- Mint — secondary information and positive/active detail.
- Hoenn Gold — progression, Skills, and objective emphasis.
- Controlled Violet — move-page identity without neon saturation.
- Slate — neutral outlines and inactive controls.

All source assets remain indexed/palette-driven and compatible with the existing 4bpp graphics pipeline.

## Pokédex

Changed only palette sources used by the existing Pokédex tilemaps and search screens:

- `graphics/pokedex/bg_hoenn.pal`
- `graphics/pokedex/bg_national.pal`
- `graphics/pokedex/search_menu.pal`
- `graphics/pokedex/search_results_bg.pal`

The screen structure, Pokémon list behavior, info/area/cry/size pages, sorting, search behavior, Seen/Caught logic and Pokédex data are untouched.

## Party

`graphics/party_menu/bg.png` keeps its tile/pixel topology but uses a redesigned Classic Enhanced palette. HP/status colors remain distinct, while the old olive/purple-heavy chrome is replaced with emerald, mint, ivory and slate.

No party commands, selection behavior, Pokémon data, held-item behavior or field-move logic changes.

## Pokémon Summary

`graphics/summary_screen/tiles.png` keeps every existing tile position and page tilemap. Palette banks were redesigned per page:

- Info: emerald / mint.
- Skills: ivory / Hoenn gold.
- Battle Moves: teal / controlled violet.
- Contest Moves: related violet/rose family.

This preserves every existing text coordinate, status window, page transition, move selector and data field.

## Start Menu

The normal Start Menu now opens a small left-side **Story Status** window using standard Emerald window framing. It displays:

- `STORY xx/29`
- current main-story objective title

The card does not appear in Safari Zone, link/Union Room, Battle Pike/Pyramid or other special menus because those menus keep their original auxiliary-window behavior. It is explicitly removed before opening Save, Pokédex, Party, Bag, PokéNav, Trainer Card, Options or Quest Log screens and rebuilt when the normal Start Menu returns.

## Quest Log

The v0.2 Quest Log remains read-only relative to story progression. v0.3 adds:

- header progress `STORY xx/29`;
- `NEXT LOCATION` terminology;
- `LAST` milestone terminology;
- simplified header/control clutter.

No new quest state is added to the save.

## PokéNav

The approximate quest marker remains 8×8 and continues using the v0.2 placement/blink logic. Only its four-color palette changes to emerald + Hoenn gold so it belongs to the new UI language.

## PC Storage

Not changed in v0.3. It is the planned first target of the second Modern UI wave.

## QA performed

- `src/quest_log.c` host syntax check: passed after charmap preprocessing.
- `src/start_menu.c` host syntax check: passed after charmap preprocessing.
- `src/pokenav_region_map.c` host syntax check: passed after generating its normal graphics dependencies and charmap preprocessing; placement/state logic is unchanged.
- Party, Summary and Pokédex edited assets successfully passed the project's `gbagfx` conversions to 4bpp / GBA palette formats.
- Source diff checked against v0.2; gameplay/content files outside the approved Modern UI surface remain unchanged.
- Final Windows runtime/playtest remains pending because this sandbox does not provide the complete 32-bit MinGW + SDL2 link runtime.

## First runtime test checklist

1. Open normal Start Menu at early/mid/late story points and verify Story card text does not overflow.
2. Open/close QUESTS repeatedly and verify the Story card is removed/recreated cleanly.
3. Validate Pokédex list, Info, Area, Cry, Size, Search and Search Results palettes.
4. Validate all six party slots with fainted/status/egg/held-item combinations.
5. Validate all Summary pages, eggs, status conditions and move-selection mode.
6. Validate PokéNav objective marker on zoomed/unzoomed region map.
7. Confirm special Start Menus do not show the Story card.
8. Open SAVE from the normal Start Menu and confirm the Story card is cleared before the save prompt, then rebuilt on return.
9. Save/reload and confirm no save-format regression.
