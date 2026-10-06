# Emerald Vanilla+ v0.3.1 — Quest UI / VRAM Hotfix

## Runtime bug found in v0.3

The original Quest Log used a single 28x18-pixel-tile window beginning at BG0 tile `0x139`.
That window required 504 tiles and extended through tile `0x330`. On the overworld BG layout,
map screen blocks begin at tile `0x300`, so opening QUESTS could overwrite live field tilemap data.
Symptoms included missing map tiles, large magenta/backdrop areas, and corrupted scenery after returning
to the Start Menu.

## Fix

The Quest Log is now split into two card-style windows that deliberately straddle the standard frame
graphics without touching them:

- Header: `0x139-0x1F5` (27x7)
- Standard frame graphics: `0x214-0x21C` (reserved)
- Body: `0x220-0x2F7` (27x8)
- Overworld map screen blocks: `>=0x300` (untouched)

The Start Menu story card was also reduced from 19x4 to 18x3 tiles for a less intrusive presentation.
Completed milestones now show four rows at a time in the compact body panel.

## QA

- `quest_log.c` host syntax check after project charmap preprocessing: PASS
- `start_menu.c` host syntax check after project charmap preprocessing: PASS
- v0.3 preservation verifier: PASS
- v0.3.1 VRAM window budget verifier: PASS

A Windows runtime rebuild/playtest is still required to confirm the visual result on the native SDL2 port.
