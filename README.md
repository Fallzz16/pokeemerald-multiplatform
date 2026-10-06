# Emerald Vanilla+ v0.3.2 — Classic Enhanced + Audio-Safe Fast Forward

**Emerald Vanilla+** keeps Pokémon Emerald's original English campaign, maps, encounters, battles, graphics, audio and balance while adding carefully scoped quality-of-life features to the native SDL2 port.

The project executes the decompiled game code directly as a native program. It does **not** bundle or load a commercial `.gba` ROM through an emulator.



## v0.3.2 — Audio-safe fast forward

This update adds an mGBA-style **hold-to-fast-forward** mode to the native SDL2 build without speeding up the background music.

- Hold **Tab** to fast-forward gameplay.
- Press **F6** to cycle the selected speed: **2x → 4x → 8x → 2x**.
- A small `>> 2x`, `>> 4x`, or `>> 8x` indicator is drawn by SDL in the top-right corner and does not consume GBA VRAM.
- The BGM clock remains at normal 60 Hz while extra gameplay frames are simulated.
- Sound-effect and Pokémon-cry players continue to advance with the accelerated game so waits do not become artificially slow, but their mixer output is muted while fast-forward is held.
- Releasing Tab immediately returns gameplay and audio to normal timing.

The original Emerald soft-reset combination `A+B+Start+Select` is unchanged.

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

v0.2 intentionally does **not** add side quests, new Pokémon, Fairy type, Mega Evolution, new encounters, balance changes, modern EXP Share, altered HMs, autosave, fast travel, voxel rendering, mod loading or other gameplay-overhaul features. v0.3.2 adds only a native fast-forward convenience layer; it does not alter saved game state or campaign data.

The original v0.1 cleanup of the old Space/Ctrl+P/Ctrl+R shortcuts remains in place. v0.3.2 introduces a replacement fast-forward implementation on **Tab** with audio decoupling, while Emerald's original `A+B+Start+Select` soft reset remains.

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

### Native fast-forward controls

| Action | Control |
| --- | --- |
| Hold fast forward | `Tab` |
| Cycle FF speed | `F6` |
| Available speeds | `2x`, `4x`, `8x` |

During fast-forward the BGM remains at normal speed and SFX/cry output is muted.

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

For the current v0.3.2 source, run:

```sh
bash scripts/verify_v032.sh
```

The v0.3.2 verifier preserves everything outside the explicitly approved fast-forward/audio surface, re-checks the v0.3.1 Quest VRAM budget, rejects the retired Space/Ctrl+P/Ctrl+R shortcuts, and verifies the Tab/F6 fast-forward and audio-decoupling hooks.

`bash scripts/verify_vanilla.sh` routes to the current release verifier. Older verifiers are retained as historical QA documentation.

See [`MODERN_UI_V0.3_AUDIT.md`](MODERN_UI_V0.3_AUDIT.md) and [`docs/MODERN_UI_V0.3.md`](docs/MODERN_UI_V0.3.md) for the current implementation/QA report. The v0.2 and v0.1 audits remain included for lineage.

## Legal

Pokémon and Pokémon Emerald are trademarks of Nintendo, Creatures Inc., and GAME FREAK inc. This is an unofficial fan project and is not affiliated with or endorsed by those companies.

The repository's scoped `LICENSE` applies only to original multiplatform-port modifications contributed through the fork. It does not relicense upstream code, third-party components or copyrighted game assets.
