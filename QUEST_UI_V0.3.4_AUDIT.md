# Emerald Vanilla+ v0.3.4 — Quest UI Visual Rework

## Goal
Replace the visually split v0.3.1 Quest Log with a single opaque Classic Enhanced presentation while preserving the proven VRAM safety fix and the v0.3.3 fast-forward/audio behavior.

## Visual architecture
The screen looks like one full-screen menu, but it is internally assembled from small VRAM-safe pieces:

- one 1×1 solid backdrop tile at `0x138`, reused across the visible BG0;
- header window: `27×6`, tiles `0x139–0x1DA`;
- footer window: `27×2`, tiles `0x1DB–0x210`;
- standard Emerald frame graphics remain reserved at `0x214–0x21C`;
- body window: `27×8`, tiles `0x220–0x2F7`;
- overworld screen-block space begins at `0x300` and is untouched.

The outer border and internal separators reuse Emerald's standard frame graphics directly in the BG0 tilemap. No giant 28×18 text window is allocated.

## Text-flow fix
Objective strings are split at `CHAR_NEWLINE` and rendered as two explicit lines. This avoids the clipped first-line behavior seen in the v0.3.3 runtime screenshot.

## Preserved behavior
- `CURRENT` / `COMPLETED` tabs.
- `L/R` tab switching.
- Up/Down completed-list scrolling.
- `B` to return.
- 29-story-milestone state logic.
- PokéNav approximate objective marker.
- v0.3.3 SDL-only full-speed fast-forward.
- Stable v0.3.1 internal audio core.
- Save format and campaign content.

## QA gate
`scripts/verify_v034.sh` runs the full v0.3.3 verifier first, then checks the new Quest VRAM layout, frame reservation, opaque backdrop path, explicit multiline rendering, and absence of the old two-panel frames.

Runtime Windows QA is still required after GitHub Actions builds the executable.
