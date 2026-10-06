#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

required=(
  include/platform.h
  include/sound_mixer.h
  src/m4a.c
  src/music_player.c
  src/platform/cgb_audio.c
  src/platform/sdl2.c
  src/sound_mixer.c
  src/quest_log.c
  src/start_menu.c
  docs/vanillaplus-v0.3.2-preserved.sha256
)
for path in "${required[@]}"; do
  [[ -f "$path" ]] || { echo "ERROR: missing $path"; exit 1; }
done

# Everything outside the approved v0.3.2 native FF/audio surface must still match v0.3.1.
sha256sum -c docs/vanillaplus-v0.3.2-preserved.sha256 >/dev/null

# Keep the v0.3.1 Quest UI inside the verified VRAM budget.
python3 - <<'PY'
regions = {
    "start_menu":   (0x139, 7 * 18),
    "story_status": (0x1C0, 18 * 3),
    "quest_header": (0x139, 27 * 7),
    "quest_body":   (0x220, 27 * 8),
}
frame_start, frame_end = 0x214, 0x21C
map_start = 0x300

def end(start, count): return start + count - 1
def overlaps(a0, a1, b0, b1): return not (a1 < b0 or a0 > b1)
for name, (start, count) in regions.items():
    stop = end(start, count)
    if stop >= map_start:
        raise SystemExit(f"ERROR: {name} reaches map screen blocks: 0x{start:X}-0x{stop:X}")
    if name in ("quest_header", "quest_body") and overlaps(start, stop, frame_start, frame_end):
        raise SystemExit(f"ERROR: {name} overlaps standard frame tiles")
if overlaps(0x139, end(0x139, 7*18), 0x1C0, end(0x1C0, 18*3)):
    raise SystemExit("ERROR: Start Menu and Story card overlap")
print("VRAM window budget OK")
PY

grep -q 'case SDLK_TAB:' src/platform/sdl2.c
grep -q 'case SDLK_F6:' src/platform/sdl2.c
grep -q 'sFastForwardMultiplier = 2' src/platform/sdl2.c
grep -q 'sFastForwardMultiplier = 4' src/platform/sdl2.c
grep -q 'sFastForwardMultiplier = 8' src/platform/sdl2.c
grep -q 'Platform_ShouldAdvanceAudioFrame' src/m4a.c
grep -q 'AdvanceFastForwardSilentPlayers' src/m4a.c
grep -q 'Platform_ShouldAdvanceAudioFrame' src/music_player.c
grep -q 'SoundMixer_IsFastForwardMutedTrack' src/sound_mixer.c
grep -q 'FastForward_ShouldMuteCgbChannel' src/platform/cgb_audio.c
grep -q 'RenderFastForwardIndicator' src/platform/sdl2.c

# Retired desktop shortcuts must remain gone.
if grep -Eq '\bspeedUp\b|\bpaused\b|\btimeScale\b|SDLK_SPACE|SDLK_p|SDLK_r' src/platform/sdl2.c; then
  echo "ERROR: retired Space/Ctrl+P/Ctrl+R fast/pause/reset code returned."
  exit 1
fi

echo "Emerald Vanilla+ v0.3.2 fast-forward verification passed."
