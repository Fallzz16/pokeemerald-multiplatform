# Emerald Vanilla+ v0.3.4 — Classic Enhanced Quest UI + Full-Speed Fast Forward

**Emerald Vanilla+** keeps Pokémon Emerald's original English campaign, maps, encounters, battles, graphics, audio and balance while adding carefully scoped quality-of-life features to the native SDL2 port.

The project executes the decompiled game code directly as a native program. It does **not** bundle or load a commercial `.gba` ROM through an emulator.



## v0.3.4 — Quest UI visual rework

The Quest Log is now presented as one opaque Classic Enhanced menu instead of two framed panels over the overworld.

- The overworld can no longer show through the middle of the Quest Log.
- One full-screen outer frame and two internal separators create a single continuous composition.
- Header, body and footer remain separate VRAM-safe windows internally.
- Current objective lines are printed independently so multiline text cannot be clipped by newline rendering.
- `CURRENT` / `COMPLETED`, story progress, scrolling and PokéNav targeting are unchanged.
- Fast-forward and all v0.3.3 audio code are intentionally untouched.

## v0.3.3 — Full-speed fast forward

This update replaces the experimental v0.3.2 audio-decoupling approach with a simpler SDL-only turbo. The internal Emerald audio engine is restored to the stable v0.3.1 state.

- Hold **Tab** to fast-forward.
- Press **F6** to cycle **2x → 4x → 8x → 2x**.
- Gameplay, BGM, SFX and Pokémon cries all accelerate together.
- A small SDL overlay shows `>> 2x`, `>> 4x`, or `>> 8x`.
- At normal speed, the audio path matches the stable v0.3.1 build.

## v0.3.1 — Quest UI hotfix

This hotfix fixes a runtime VRAM overlap in the v0.3 Quest Log that could overwrite overworld tilemap data and produce missing/magenta scenery after opening QUESTS. The Quest screen is now split into two compact card-style panels with explicit VRAM-safe tile ranges, and the Start Menu Story card is smaller. Gameplay/content remain unchanged.


## v0.3 — Classic Enhanced UI

This release modernizes the presentation while deliberately preserving Emerald's pixel-art language and game rules. The first UI pass focuses on **Pokédex, Party, Pokémon Summary, Quest Log, Start Menu story status, and the PokéNav quest marker**.

### Visual language

- Emerald/teal surfaces instead of the harsh olive/neon combinations used by several original screens.
- Warm ivory information panels for stronger text contrast.
- Gold accents for progression and Skills information.
- Controlled violet accents for move pages, retaining the original page identity without the saturated magenta/blue look.
- Original tile geometry, pixel grid and screen resolution are preserved.

### Start Menu story card

The normal Start Menu now shows a small classic Emerald-style status window on the left with `STORY xx/29` and the current main-story objective title. It is read-only and derives from the same quest flags/variables as the v0.2 Quest Log.

### Quest Log refinement

The Quest Log now uses clearer information hierarchy, shows `STORY xx/29` in the header, uses **NEXT LOCATION** and **LAST** labels, and keeps Current/Completed navigation unchanged.

### Gameplay preservation

No species data, encounters, trainers, moves, items, maps, story scripts, battle logic, music or SFX are changed by the Modern UI pass. The UI source assets remain 4bpp-compatible and were validated through the project's graphics converter.

## v0.2 — Main Story Quest Guide

This release adds a non-invasive main-story guide designed to help players resume the adventure without changing the campaign itself.

### Quest Log

A new **QUESTS** entry appears in the normal Start Menu. It contains:

- **CURRENT** — the next unfinished main-story milestone.
- **WHAT WAS I DOING?** — a concise reminder of the current objective.
- **LOCATION** — the relevant city, route or dungeon, without exact NPC/path GPS.
- **PREV** — the last completed main-story milestone.
- **COMPLETED** — a scrollable history of completed main-story milestones.

Controls inside the Quest Log:

| Action | Control |
| --- | --- |
| Change Current / Completed tab | `L` / `R` |
| Scroll completed milestones | D-pad Up / Down |
| Return | `B` |

The tracker does **not** rewrite story scripts and does not add quest-state fields to the save. It derives progress from Emerald's existing flags, variables and badges, so existing saves can be interpreted automatically.

### PokéNav objective marker

The PokéNav region map now displays a small blinking marker for the **approximate region** of the active main-story objective. Dungeon targets are translated to the corresponding map region where appropriate. This is intentionally not an exact GPS arrow.

## Scope

v0.2 intentionally does **not** add side quests, new Pokémon, Fairy type, Mega Evolution, new encounters, balance changes, modern EXP Share, altered HMs, autosave, fast travel, voxel rendering, mod loading or other gameplay-overhaul features.

The retired v0.1 Space/Ctrl+P/Ctrl+R desktop shortcuts remain disabled. v0.3.3 adds a replacement hold-to-fast-forward on `Tab`, with `F6` cycling 2x/4x/8x, while Emerald's original `A+B+Start+Select` soft reset remains unchanged.

## Controls

| GBA control | Keyboard |
| --- | --- |
| A | `Z` |
| B | `X` |
| Start | `Enter` |
| Select | `Backslash` |
| L | `A` |
| R | `S` |
| D-pad | Arrow keys |

Windows XInput controllers remain mapped to equivalent GBA controls.

### Native fast-forward

| Action | Control |
| --- | --- |
| Hold turbo | `Tab` |
| Cycle turbo speed | `F6` |
| Available speeds | `2x`, `4x`, `8x` |

BGM, SFX and Pokémon cries speed up together with gameplay while turbo is held.

## Windows build

The current native target is 32-bit because the portable code/data layout relies on 32-bit pointers.

With the required MinGW and SDL2 development files installed:

```sh
make -f Makefile_pc -j2
```

Output:

```text
pokeemerald.exe
```

Place the matching 32-bit `SDL2.dll` beside the executable. The included GitHub Actions workflow can build and package the portable Windows folder automatically.

## Save file

The native port stores save data as:

```text
pokeemerald.sav
```

The Quest Log derives its state from the existing Emerald save data and does not require a separate quest save file.

## Verification

For the current v0.3.4 source, run:

```sh
bash scripts/verify_v034.sh
```

The v0.3.4 verifier first runs all v0.3.3 fast-forward/audio checks, then validates the new opaque Quest layout, its split VRAM budget, frame-tile reservation, and removal of the old two-panel framed presentation.

`bash scripts/verify_vanilla.sh` routes to the current release verifier. Older verifiers remain as historical QA documentation.

See [`MODERN_UI_V0.3_AUDIT.md`](MODERN_UI_V0.3_AUDIT.md) and [`docs/MODERN_UI_V0.3.md`](docs/MODERN_UI_V0.3.md) for the current implementation/QA report. The v0.2 and v0.1 audits remain included for lineage.

## Legal

Pokémon and Pokémon Emerald are trademarks of Nintendo, Creatures Inc., and GAME FREAK inc. This is an unofficial fan project and is not affiliated with or endorsed by those companies.

The repository's scoped `LICENSE` applies only to original multiplatform-port modifications contributed through the fork. It does not relicense upstream code, third-party components or copyrighted game assets.
