# Emerald Vanilla+ v0.3.3 — Full-Speed Fast Forward

## Goal
Replace the v0.3.2 audio-decoupling experiment with a simpler traditional turbo that accelerates gameplay and all game audio together.

## Safety design
- Internal Emerald audio core restored byte-for-byte to the stable v0.3.1 source for `m4a`, `music_player`, CGB audio and the software mixer.
- Normal-speed SDL audio queue path remains equivalent to v0.3.1.
- Fast-forward logic lives in `src/platform/sdl2.c` only.
- Hold `Tab` to accelerate; `F6` cycles 2x / 4x / 8x.
- Final interleaved stereo output is decimated by the same multiplier only while fast-forward is held, giving traditional accelerated pitch/tempo without creating an ever-growing SDL audio queue.
- v0.3.1 Quest UI VRAM limits remain checked.

## Installer revision b
This package is self-contained. It does not require an old Git commit to exist locally and does not run `git checkout` against historical commits. Stable audio files are included directly in the package.
