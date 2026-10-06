# Emerald Vanilla+ v0.3.2 — Fast Forward Audit

## User-selected behavior
- Hold `Tab` to fast-forward.
- `F6` cycles 2x -> 4x -> 8x -> 2x.
- SFX and Pokemon cry output are muted during fast-forward.
- BGM remains on its normal 60 Hz timeline and keeps normal pitch/tempo.
- SDL overlay shows `>> 2x`, `>> 4x`, or `>> 8x` without using GBA VRAM.

## Architecture
The SDL host increases game-frame cadence while tagging only one frame per speed multiplier as an audio frame. `m4aSoundMain` and `m4aSoundVSync` advance/queue BGM only on those real-time audio frames. On intermediate accelerated frames, SE1/SE2/SE3 and cry players advance in isolation so gameplay code waiting on SFX does not fall back to real-time speed. Their Direct Sound and CGB/PSG mixer contributions are suppressed while Tab is held.

## Safety
- No save-format changes.
- No map, encounter, trainer, Pokemon, move, item, story-script, battle-rule, or quest-state changes.
- The v0.3.1 Quest UI VRAM budget is rechecked by `scripts/verify_v032.sh`.
- Old Space/Ctrl+P/Ctrl+R desktop shortcuts remain absent.

## Remaining runtime QA
The Windows build must still be compiled by GitHub Actions and tested for: 2x/4x/8x pacing, BGM continuity, SFX mute, release-to-1x recovery, battles, menus, cries, fanfares, and prolonged 8x stability.
