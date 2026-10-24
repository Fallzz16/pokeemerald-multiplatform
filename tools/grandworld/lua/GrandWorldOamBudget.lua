-- M8 graphics diagnostics: inspect actual GBA OAM without changing save or gameplay.
-- Intended for mGBA headless on a throwaway Verify1.gba, via mgba-run.sh.
-- Counts hardware OAM entries with enabled OBJ display; not a CPU/FPS profiler.
local here = (debug.getinfo(1, "S").source:sub(2)):match("^(.*[/\\])") or ""
package.path = here .. "?.lua;" .. package.path
local S = require("symbols")
local F = require("lib").new(S, "GrandWorldOamBudget")

-- GBA OAM has 128 slots, but the World renderer parks unused/dummy entries
-- at (DISPLAY_WIDTH+64, DISPLAY_HEIGHT), with affineMode=OFF and objMode=0.
-- Counting all *enabled* OAM entries therefore reported a false 128/128.
-- Count ONLY objects whose actual hardware bounding box intersects 240x160.
local dimensions = {
  [0] = { {8,8}, {16,16}, {32,32}, {64,64} },   -- square
  [1] = { {16,8}, {32,8}, {32,16}, {64,32} },  -- horizontal
  [2] = { {8,16}, {8,32}, {16,32}, {32,64} }, -- vertical
}

local function activeOamCount()
  local count = 0
  for i = 0, 127 do
    local addr = 0x07000000 + i * 8
    local attr0, attr1 = F.r16(addr), F.r16(addr + 2)
    local affine = ((attr0 >> 8) & 1) ~= 0
    local doubleOrDisabled = ((attr0 >> 9) & 1) ~= 0
    if affine or not doubleOrDisabled then
      local shape, size = (attr0 >> 14) & 3, (attr1 >> 14) & 3
      local dim = dimensions[shape] and dimensions[shape][size + 1]
      if dim then
        local x, y = attr1 & 511, attr0 & 255
        if x >= 256 then x = x - 512 end
        if y >= 160 then y = y - 256 end
        local scale = affine and doubleOrDisabled and 2 or 1
        local w, h = dim[1] * scale, dim[2] * scale
        if x < 240 and x + w > 0 and y < 160 and y + h > 0 then
          count = count + 1
        end
      end
    end
  end
  return count
end

local function sample(label, frames)
  local low, high, sum = 128, 0, 0
  for i = 1, frames do
    emu.frameadvance()
    local count = activeOamCount()
    low = math.min(low, count)
    high = math.max(high, count)
    sum = sum + count
  end
  F.L(string.format("OAM_METRIC scenario=%s frames=%d active_min=%d active_max=%d active_avg=%.3f",
    label, frames, low, high, sum / frames))
  return low, high
end

F.run(function()
  if not F.boot(100) then
    F.check("M8 OAM: booted overworld", false)
    F.finish()
    return
  end
  F.check("M8 OAM: game actually in RegionHub", F.grp() == 100)
  F.idle(40)
  local low, high = sample("hub_idle", 180)
  F.check("M8 OAM: active hardware sprites within bounds", low >= 1 and high < 128,
    string.format("min=%d max=%d", low, high))
  -- Reproduce deterministic steps if traversable; track the final settled scene.
  for _, direction in ipairs({"Right", "Left", "Down", "Up"}) do
    F.step(direction)
  end
  F.idle(15)
  sample("hub_after_movement", 120)
  F.finish()
end)
