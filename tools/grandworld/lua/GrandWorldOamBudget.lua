-- M8 graphics diagnostics: inspect actual GBA OAM without changing save or gameplay.
-- Intended for mGBA headless on a throwaway Verify1.gba, via mgba-run.sh.
-- Counts hardware OAM entries with enabled OBJ display; not a CPU/FPS profiler.
local here = (debug.getinfo(1, "S").source:sub(2)):match("^(.*[/\\])") or ""
package.path = here .. "?.lua;" .. package.path
local S = require("symbols")
local F = require("lib").new(S, "GrandWorldOamBudget")

local function activeOamCount()
  local count = 0
  for i = 0, 127 do
    local attr0 = F.r16(0x07000000 + i * 8)
    local objMode = (attr0 >> 8) & 3
    -- OBJ mode 2 disables a NON-affine sprite. Mode 3 is double-size affine.
    if objMode ~= 2 then count = count + 1 end
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
  F.check("M8 OAM: active hardware sprites within bounds", low >= 1 and high <= 128,
    string.format("min=%d max=%d", low, high))
  -- Reproduce deterministic steps if traversable; track the final settled scene.
  for _, direction in ipairs({"Right", "Left", "Down", "Up"}) do
    F.step(direction)
  end
  F.idle(15)
  sample("hub_after_movement", 120)
  F.finish()
end)
