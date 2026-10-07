#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# v0.3.3 restores the internal audio core exactly to the known-good v0.3.1 files.
check_sha() {
  local expected="$1" path="$2"
  local actual
  actual="$(sha256sum "$path" | awk '{print $1}')"
  if [[ "$actual" != "$expected" ]]; then
    echo "ERROR: $path does not match the stable v0.3.1 audio core."
    echo " expected: $expected"
    echo " actual:   $actual"
    exit 1
  fi
}

check_sha 12cd4d7e2b3e8999b87a20af1a499c6a173ed0958fdbae226b9c24f6124ad7c3 src/m4a.c
check_sha b4888ff64bfbfe674ca331777aea4ce880d151ca54ec92e71911438030b0bf67 src/music_player.c
check_sha 4cc39106cf32d21386fee4b0355ec972dc5c2d70224bdcee56810f48d3c65685 src/platform/cgb_audio.c
check_sha 943050ee8518a437e9b316d31a60574a22f5f27ac0fb37d6900a099e2cbb98b3 src/sound_mixer.c
check_sha d02deb5cb930aba375dbdef0a5c3e6d0fd10da9e8ab6ee20c363ed7b21768405 include/platform.h
check_sha 598d86acbd4224a0a29898917e1aa885c7734f0e410d3834088299e3971e522a include/sound_mixer.h

# Quest UI runtime VRAM safety budget retained from v0.3.1.
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
grep -q 'fastForwardMultiplier' src/platform/sdl2.c
grep -q 'compressedAudio' src/platform/sdl2.c
grep -q 'sourceFrame += multiplier' src/platform/sdl2.c
grep -q 'RenderFastForwardIndicator' src/platform/sdl2.c
grep -q 'if (!SDL_AtomicGet(&fastForwardActive))' src/platform/sdl2.c

# Explicitly forbid the v0.3.2 audio-decoupling experiment from returning.
if grep -R -E 'Platform_ShouldAdvanceAudioFrame|AdvanceFastForwardSilentPlayers|SoundMixer_IsFastForwardMutedTrack|FastForward_ShouldMuteCgbChannel' \
  include src/m4a.c src/music_player.c src/sound_mixer.c src/platform/cgb_audio.c src/platform/sdl2.c >/dev/null 2>&1; then
  echo "ERROR: v0.3.2 audio-decoupling code is still present."
  exit 1
fi

echo "Emerald Vanilla+ v0.3.3 full-speed fast-forward verification passed."
