#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

bash scripts/verify_modern_ui.sh

python3 - <<'PY'
# v0.3.1 runtime VRAM safety budget for field/quest windows.
regions = {
    "start_menu":   (0x139, 7 * 18),
    "story_status": (0x1C0, 18 * 3),
    "quest_header": (0x139, 27 * 7),
    "quest_body":   (0x220, 27 * 8),
}
frame_start, frame_end = 0x214, 0x21C
map_start = 0x300

def end(start, count):
    return start + count - 1

def overlaps(a0, a1, b0, b1):
    return not (a1 < b0 or a0 > b1)

for name, (start, count) in regions.items():
    stop = end(start, count)
    if stop >= map_start:
        raise SystemExit(f"ERROR: {name} reaches map screen-block tiles: 0x{start:X}-0x{stop:X}")
    if name in ("quest_header", "quest_body") and overlaps(start, stop, frame_start, frame_end):
        raise SystemExit(f"ERROR: {name} overlaps standard frame tiles: 0x{start:X}-0x{stop:X}")

# Windows coexist in these pairs only.
pairs = [("start_menu", "story_status")]
for a, b in pairs:
    a0, ac = regions[a]; a1 = end(a0, ac)
    b0, bc = regions[b]; b1 = end(b0, bc)
    if overlaps(a0, a1, b0, b1):
        raise SystemExit(f"ERROR: {a} overlaps {b}")

print("VRAM window budget OK:")
for name, (start, count) in regions.items():
    print(f"  {name:12s} 0x{start:03X}-0x{end(start,count):03X}")
print("  std_frame    0x214-0x21C (reserved)")
print("  map_blocks   >=0x300 (untouched)")
PY

grep -q 'sQuestHeaderWindowTemplate' src/quest_log.c
grep -q 'sQuestBodyWindowTemplate' src/quest_log.c
grep -q '.baseBlock = 0x220' src/quest_log.c
grep -q '.height = 3' src/start_menu.c

echo "Emerald Vanilla+ v0.3.1 Quest UI hotfix verification passed."
