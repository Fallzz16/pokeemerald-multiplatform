#!/usr/bin/env python3
"""Read-only GBA OBJ tile budget instrumentation in a disposable CI checkout.

The *only* C change removes 'static' from an EWRAM bitmap so the existing
World test symbol generator can resolve its address. The bitmap, allocation
algorithm, sprite art, palettes and save layout remain unchanged.
Never apply to a release checkout.
"""
import argparse
from pathlib import Path
import sys

SPRITE_ANCHOR = "EWRAM_DATA static u8 sSpriteTileAllocBitmap[128] = {0};"
SPRITE_REPLACEMENT = "EWRAM_DATA u8 sSpriteTileAllocBitmap[128] = {0};"
SYMBOL_ANCHOR = '    "sOWESpawnCountdown", "sLockFieldControls", "gM9OWEProbe",\n'
SYMBOL_REPLACEMENT = (SYMBOL_ANCHOR +
    '    "sSpriteTileAllocBitmap", "gReservedSpriteTileCount",\n')

LUA_FUNCTION = """
-- Test-only inspection of the native World OBJ tile allocation bitmap:
-- 1024 bits x 32-byte 4bpp tiles = 32768 bytes of OBJ VRAM.
-- This measures allocation, not unique visible pixels, DMA time or FPS.
local function logGraphicsBudget(stage)
  assert(S.sSpriteTileAllocBitmap and S.sSpriteTileAllocBitmap ~= 0,
         "missing native OBJ bitmap symbol in instrumented ARM build")
  assert(S.gReservedSpriteTileCount and S.gReservedSpriteTileCount ~= 0,
         "missing reserved OBJ tile count in instrumented ARM build")
  local used, free, currentFree, largestFree, freeRuns = 0, 0, 0, 0, 0
  for i = 0, 127 do
    local value = F.r8(S.sSpriteTileAllocBitmap + i)
    for bit = 0, 7 do
      if (value & (1 << bit)) ~= 0 then
        used = used + 1
        currentFree = 0
      else
        free = free + 1
        if currentFree == 0 then freeRuns = freeRuns + 1 end
        currentFree = currentFree + 1
        largestFree = math.max(largestFree, currentFree)
      end
    end
  end
  local sprites, palettes, oweCount = 0, 0, 0
  for i = 0, S.Sprite.count - 1 do
    if (F.r16(S.gSprites + i * S.Sprite.stride + S.Sprite.inUse) & 1) ~= 0 then
      sprites = sprites + 1
    end
  end
  for i = 0, S.SpritePalette.count - 1 do
    if F.r16(S.sSpritePaletteTags + i * 2) ~= S.SpritePalette.free then
      palettes = palettes + 1
    end
  end
  for _ in pairs(generated()) do oweCount = oweCount + 1 end
  local follow = follower()
  local followerAlive = follow ~= nil and follow.visible and spriteActive(follow.spriteId)
  local reserved = F.r16(S.gReservedSpriteTileCount)
  assert(used + free == 1024 and reserved <= 1024 and used >= reserved,
         "OBJ bitmap inconsistent with reserved tile count")
  -- Exact identical *unfaded* OBJ palette colors across occupied slots.
  -- These are AUDIT CANDIDATES, NOT safe deduplication: tags can have distinct
  -- time-of-day blend behavior, ownership or release callbacks.
  assert(S.gPlttBufferUnfaded and S.gPlttBufferUnfaded ~= 0,
         "no native unfaded palette buffer symbol")
  local colorsSeen, duplicateExtraSlots, duplicatePairs = {}, 0, 0
  for slot = 0, S.SpritePalette.count - 1 do
    if F.r16(S.sSpritePaletteTags + slot * 2) ~= S.SpritePalette.free then
      local parts = {}
      for color = 0, 15 do
        parts[#parts+1] = string.format("%04X",
          F.r16(S.gPlttBufferUnfaded + 512 + slot * 32 + color * 2))
      end
      local fingerprint = table.concat(parts, "")
      local prev = colorsSeen[fingerprint] or 0
      if prev > 0 then
        duplicateExtraSlots = duplicateExtraSlots + 1
        duplicatePairs = duplicatePairs + prev
      end
      colorsSeen[fingerprint] = prev + 1
    end
  end
  F.L(string.format(
    "GRAPHICS_BUDGET stage=%s used=%d free=%d largest_free=%d free_runs=%d reserved=%d sprites=%d palettes=%d owe=%d follower=%d palette_duplicate_slots=%d palette_duplicate_pairs=%d",
    stage, used, free, largestFree, freeRuns, reserved, sprites, palettes,
    oweCount, followerAlive and 1 or 0, duplicateExtraSlots, duplicatePairs))
end

"""
LUA_INSERT_BEFORE = "-- Source-pinned local EWRAM symbols emitted only for the experimental test\n"
LUA_CALL_STAGES = ("field-before-spawn", "field-after-2400-frames",
                   "field-after-real-battle-flee")
LUA_SAMPLE_ANCHOR = '    if F.reportCrash("land_sample_" .. n) then break end\n'
LUA_SAMPLE_REPLACEMENT = (LUA_SAMPLE_ANCHOR +
    '    if n % 10 == 0 and F.ow() then logGraphicsBudget("sample-" .. n) end\n')


def replace_once(text, old, new, label):
    if text.count(old) != 1 or new == old:
        raise ValueError(f"FAIL CLOSED: missing/duplicate anchor: {label}")
    return text.replace(old, new, 1)


def changes(sprite, generator, lua):
    sprite = replace_once(sprite, SPRITE_ANCHOR, SPRITE_REPLACEMENT,
                          "native sprite bitmap linkage")
    generator = replace_once(generator, SYMBOL_ANCHOR, SYMBOL_REPLACEMENT,
                             "pinned World symbol list (after M9 instrumentation)")
    lua = replace_once(lua, LUA_INSERT_BEFORE,
                       LUA_FUNCTION + LUA_INSERT_BEFORE,
                       "OWE read-only probe insertion")
    for stage in LUA_CALL_STAGES:
        call = f'  logRuntimeBudget("{stage}")\n'
        lua = replace_once(lua, call,
                           call + f'  logGraphicsBudget("{stage}")\n',
                           f"runtime graphics snapshot {stage}")
    lua = replace_once(lua, LUA_SAMPLE_ANCHOR, LUA_SAMPLE_REPLACEMENT,
                       "OWE sampling loop")
    return sprite, generator, lua


def instrument(world, apply=False):
    root = Path(world)
    paths = (root / "src/sprite.c",
             root / "test/overworld/GenLuaSymbols.py",
             root / "test/overworld/lua/GrandWorldM9LandOWE.lua")
    original = [p.read_text(encoding="utf-8") for p in paths]
    patched = changes(*original)  # validate ALL anchors before writing anything
    if apply:
        for path, value in zip(paths, patched):
            path.write_text(value, encoding="utf-8")
    return {"files_checked": len(paths),
            "symbols_exposed_test_only": 2,
            "snapshot_stages": list(LUA_CALL_STAGES),
            "samples_every_n_iterations": 10,
            "gameplay_sources_changed": apply,
            "rom_assets_or_saves_changed": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--apply", action="store_true",
                        help="Only on an ephemeral pinned World checkout")
    args = parser.parse_args()
    try:
        print(instrument(args.world, apply=args.apply))
    except (OSError, ValueError) as error:
        sys.exit(str(error))


if __name__ == "__main__":
    main()
