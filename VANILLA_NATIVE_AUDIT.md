# Emerald Vanilla Native — Baseline Audit

## Goal

Run the original English Pokémon Emerald game code as a native Windows application through the SDL2 portability layer, without loading a GBA ROM in an emulator and without adding gameplay/content features.

## Source baseline

- Fork source: `Fallzz16/pokeemerald-multiplatform`
- Selected historical baseline: `74b8989bfbebabb10f5cbf136c4a48a4f99cc3d9`
- Commit title: `Add Windows and Linux PC ports`
- Upstream Emerald identity documented by the project: `BPEE`, revision 0, English.

This baseline was chosen because it predates the later display-background system, display options page, voxel renderer, runtime mod loader, ROM-hack importer and related experimental features.

## Intentional changes in this vanilla pass

Only the active SDL2 platform backend was altered. The pass removes desktop conveniences that are not part of the original GBA game:

- Space-bar fast-forward.
- Right-trigger fast-forward.
- `Ctrl+P` pause.
- `Ctrl+R` desktop soft-reset shortcut.
- Automatic Windows debug-console allocation.

The original game-side `A+B+Start+Select` soft reset remains intact in `src/main.c`.

## Content preservation

No map, encounter table, trainer, Pokémon, move, item, script, dialogue, battle system, graphic asset, music track or sound-effect asset was intentionally changed.

`docs/vanilla-baseline.sha256` contains SHA-256 hashes for every file from the supplied baseline archive except the two intentionally edited presentation/project files (`src/platform/sdl2.c` and `README.md`). Run:

```sh
bash scripts/verify_vanilla.sh
```

The verifier also rejects known post-baseline feature markers and desktop speed/pause shortcuts.

## Local validation performed

- Source archive extracted successfully.
- 480 files found under `src/`.
- 5,729 files found under `graphics/`.
- 3,551 files found under `data/`.
- No voxel/mod-loader/display-page markers found in the selected baseline.
- All native host build tools in `make_tools.mk` compiled successfully in the working environment.

## Build limitation of the current sandbox

The current execution sandbox does not provide the required 32-bit MinGW cross compiler or SDL2 Windows development libraries, so `pokeemerald.exe` cannot be linked here.

A GitHub Actions workflow is included at `.github/workflows/build-windows-native.yml`. It installs the 32-bit MinGW toolchain, downloads SDL2 2.30.7's MinGW development package, verifies the vanilla payload, builds `pokeemerald.exe`, packages `SDL2.dll`, and uploads a portable Windows artifact.

## First runtime QA after a successful Windows build

1. Boot/logo/title sequence.
2. New Game and Birch intro.
3. Player naming and truck intro.
4. Littleroot movement/collision.
5. NPC dialogue and doors/warps.
6. Starter selection and first battle.
7. Bag/menu/Pokédex once unlocked.
8. Music/SFX channel sanity.
9. Save, exit, relaunch, Continue.
10. Original `A+B+Start+Select` soft reset.
