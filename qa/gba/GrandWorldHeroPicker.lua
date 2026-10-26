-- GBA real input regression: select one of six protagonists THROUGH the intro UI.
-- No direct writes to save variables, emulator RAM, task functions or savestates.
-- The upstream mgba-run.sh always starts with a fresh throwaway ROM/save pair.
local here = (debug.getinfo(1, "S").source:sub(2)):match("^(.*[/\\])") or ""
package.path = here .. "?.lua;" .. package.path
local S = require("symbols")
local HEROES = { "Brendan", "May", "Red", "Leaf", "Ethan", "Lyra" }
local slot = tonumber(os.getenv("GW_HERO_SLOT") or "")
assert(slot and slot >= 0 and slot <= 5 and slot == math.floor(slot), "GW_HERO_SLOT must be 0..5")
local F = require("lib").new(S, "GrandWorldPicker" .. HEROES[slot + 1])

-- The linker-generated function addresses identify the LIVE intro screens,
-- unlike matching a cursor that could belong to the wrong five-row menu.
local function onTask(symbol)
  for i = 0, S.Task.count - 1 do
    local base = S.gTasks + i * S.Task.stride
    if F.r8(base + S.Task.isActive) ~= 0
       and (F.r32(base + S.Task.func) & ~1) == (symbol & ~1) then
      return true
    end
  end
  return false
end

local function advanceToTask(symbol, maxFrames)
  for i = 1, maxFrames do
    if onTask(symbol) then return true end
    -- Just one real A press per ~18 frames. Stop BEFORE confirming this menu.
    joypad.set(i % 18 == 1 and { A = true } or {})
    emu.frameadvance()
  end
  F.shot("intro_timeout")
  return false
end

local function key(k)
  F.press(k, 2)
  F.idle(10)
end

local function heroVar(id)
  return F.r16(F.sb1() + S.SaveBlock1.vars + (id - 0x4000) * 2)
end

F.run(function()
  client.speedmode(800)
  F.check("real ARM build exposes Oak gender and hero task symbols",
    S.Task_OakSpeech_HandleGenderInput >= 0x08000000
    and S.Task_OakSpeech_HandleOutfitInput >= 0x08000000
    and S.gTasks >= 0x02000000 and S.sMenu >= 0x02000000)

  local genderReady = advanceToTask(S.Task_OakSpeech_HandleGenderInput, 120000)
  F.check("intro reached live boy girl menu without RAM staging", genderReady)
  if not genderReady then F.finish(); return end

  F.check("gender menu starts at BOY row", F.mcur() == 0)
  local gender = slot % 2
  if gender == 1 then key("Down") end
  F.check("real gender menu navigated to requested row", F.mcur() == gender)
  key("A")
  F.check("gender selected by A stored in SaveBlock2",
    F.r8(F.sb2() + S.SaveBlock2.playerGender) == gender)

  local pickerReady = advanceToTask(S.Task_OakSpeech_HandleOutfitInput, 120000)
  F.check("actual three-choice protagonist picker reached", pickerReady)
  if not pickerReady then F.finish(); return end

  F.check("hero menu initially highlights first row", F.mcur() == 0)
  key("Down"); key("Down")
  local reachedThird = F.mcur() == 2
  key("Down")
  F.check("hero menu has exactly three nonwrapping choices",
    reachedThird and F.mcur() == 2)
  key("B")
  F.check("B never confirms a permanent hero identity",
    onTask(S.Task_OakSpeech_HandleOutfitInput))

  local row = slot // 2
  for _ = 1, 2 - row do key("Up") end
  F.check("requested hero selected using real cursor input",
    F.mcur() == row)
  F.shot("before_confirm")
  key("A")
  F.check("hero identity set by the real picker",
    heroVar(0x40FB) == slot,
    "expected=" .. slot .. " actual=" .. heroVar(0x40FB))
  F.check("hero appearance slot matches the choice",
    heroVar(0x40FC) == slot)
  F.shot("after_confirm")

  -- The real NewGame callback calls ClearSav1; this is why post-intro
  -- identity preservation must be checked independently of picker RAM.
  local entered = F.boot(100)
  F.check("intro reaches actual RegionHub overworld", entered and F.ow() and F.grp() == 100)
  if not entered then F.finish(); return end
  F.check("chosen identity survives NewGame save block reset", heroVar(0x40FB) == slot)
  F.check("chosen appearance survives NewGame save block reset", heroVar(0x40FC) == slot)
  F.check("chosen gender survives entering the world",
    F.r8(F.sb2() + S.SaveBlock2.playerGender) == gender)
  F.finish()
end)
