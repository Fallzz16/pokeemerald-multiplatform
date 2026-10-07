#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# First preserve every v0.3.3 guarantee: stable v0.3.1 audio core +
# SDL-only 2x/4x/8x full-speed fast-forward.
bash scripts/verify_v033.sh

python3 - <<'PY'
regions = {
    "quest_backdrop": (0x138, 1),
    "quest_header":   (0x139, 27 * 6),
    "quest_footer":   (0x1DB, 27 * 2),
    "quest_body":     (0x220, 27 * 8),
}
frame_start, frame_end = 0x214, 0x21C
map_start = 0x300

def end(start, count):
    return start + count - 1

def overlaps(a0, a1, b0, b1):
    return not (a1 < b0 or a0 > b1)

items = list(regions.items())
for name, (start, count) in items:
    stop = end(start, count)
    if stop >= map_start:
        raise SystemExit(f"ERROR: {name} reaches map screen blocks: 0x{start:X}-0x{stop:X}")
    if overlaps(start, stop, frame_start, frame_end):
        raise SystemExit(f"ERROR: {name} overlaps standard frame tiles: 0x{start:X}-0x{stop:X}")

for i, (name_a, (start_a, count_a)) in enumerate(items):
    for name_b, (start_b, count_b) in items[i + 1:]:
        if overlaps(start_a, end(start_a, count_a), start_b, end(start_b, count_b)):
            raise SystemExit(f"ERROR: {name_a} overlaps {name_b}")

assert end(0x139, 27 * 6) == 0x1DA
assert end(0x1DB, 27 * 2) == 0x210
assert end(0x220, 27 * 8) == 0x2F7

print("v0.3.4 Quest VRAM budget OK:")
for name, (start, count) in items:
    print(f"  {name:15s} 0x{start:03X}-0x{end(start,count):03X}")
print("  std_frame       0x214-0x21C (reserved)")
print("  map_blocks      >=0x300 (untouched)")
PY

grep -q '#include "bg.h"' src/quest_log.c
grep -q 'QUEST_BACKDROP_TILE       0x138' src/quest_log.c
grep -q '.baseBlock = 0x139' src/quest_log.c
grep -q '.height = 6' src/quest_log.c
grep -q '.baseBlock = 0x1DB' src/quest_log.c
grep -q '.tilemapTop = 17' src/quest_log.c
grep -q '.baseBlock = 0x220' src/quest_log.c
grep -q '.tilemapTop = 8' src/quest_log.c
grep -q 'PrintTwoLineObjective' src/quest_log.c
grep -q 'DrawQuestBackdrop' src/quest_log.c
grep -q 'DrawQuestFrame' src/quest_log.c
grep -q 'FillBgTilemapBufferRect(0, QUEST_BACKDROP_TILE, 0, 0, 30, 20' src/quest_log.c
grep -q 'CopyBgTilemapBufferToVram(0)' src/quest_log.c

if grep -q 'DrawStdWindowFrame(sQuestHeaderWindowId' src/quest_log.c \
 || grep -q 'DrawStdWindowFrame(sQuestBodyWindowId' src/quest_log.c; then
  echo "ERROR: old two-panel Quest frames returned."
  exit 1
fi

echo "Emerald Vanilla+ v0.3.4 Quest UI rework verification passed."
