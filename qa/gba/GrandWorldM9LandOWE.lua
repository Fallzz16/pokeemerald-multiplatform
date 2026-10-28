-- M9: read-only, authentic terrestrial generated OWE smoke probe.
-- No writes to memory, no save edits, no artificial object insertion.
-- Requires pinned World's lib.lua and generated symbols.lua in headless mGBA.

local here = (debug.getinfo(1, "S").source:sub(2)):match("^(.*[/\\])") or ""
package.path = here .. "?.lua;" .. package.path
local S = require("symbols")
local F = require("lib").new(S, "GrandWorldM9LandOWE")

-- Pinned World's include/constants/event_objects.h: four reserved generated IDs.
local OWE_LOW, OWE_HIGH = 249, 252
local OBJ_EVENT_MON = 1 << 14
local SPECIES_MASK = 0x8FFF
local ROUTE29_GROUP, ROUTE29_MAP = 75, 2

local function generated()
  local out = {}
  for i = 0, 15 do
    local b = S.gObjectEvents + i * S.ObjectEvent.stride
    if (F.r8(b) & 1) ~= 0 then
      local localId = F.r8(b + S.ObjectEvent.localId)
      if localId >= OWE_LOW and localId <= OWE_HIGH then
        local gfx = F.r16(b + S.ObjectEvent.graphicsId)
        out[localId] = {
          species = gfx & SPECIES_MASK,
          gfx = gfx,
          x = F.rs16(b + S.ObjectEvent.x) - 7,
          y = F.rs16(b + S.ObjectEvent.y) - 7,
          visible = (F.r8(b + S.ObjectEvent.flags1) & 0x20) == 0,
        }
      end
    end
  end
  return out
end

F.run(function()
  if not F.boot(100) then
    F.check("boot reaches the real GBA hub", false)
    F.finish()
    return
  end
  local arrived = F.warpTo(0, 7, 5, 0, 0, 2, 0, 0, 0,
                           ROUTE29_GROUP, ROUTE29_MAP, "m9_land_route29")
  F.check("reached Route 29 without RAM warp", arrived and F.grp() == ROUTE29_GROUP
          and F.mapn() == ROUTE29_MAP)
  if not arrived then F.finish(); return end

  -- Sample actual World object-event table, not the wild encounter config.
  -- 4-second intervals, up to 40 seconds in-game. Wait while stationary so
  -- the engine's mid-step spawn guard cannot artificially suppress spawning.
  local seen, moved, visible, validGfx = {}, false, false, false
  local observed, firstShot = 0, false
  for n = 1, 10 do
    F.idle(240)
    if F.reportCrash("land_sample_" .. n) then break end
    if not F.ow() then
      F.L("overworld interrupted, stopping OWE probe")
      break
    end
    for localId, o in pairs(generated()) do
      observed = observed + 1
      local key = localId .. ":" .. o.species
      local prev = seen[key]
      if prev and (prev.x ~= o.x or prev.y ~= o.y) then moved = true end
      seen[key] = { x = o.x, y = o.y }
      visible = visible or o.visible
      validGfx = validGfx or ((o.gfx & OBJ_EVENT_MON) ~= 0 and o.species > 0)
      F.L(string.format("route29 sample=%d id=%d gfx=0x%04X species=%d pos=(%d,%d) visible=%s",
                        n, localId, o.gfx, o.species, o.x, o.y, tostring(o.visible)))
      if o.visible and not firstShot then
        F.shot("actual_generated_land_owe")
        firstShot = true
      end
    end
  end
  F.check("generated terrestrial OWE actually exists in live ObjectEvents",
          observed > 0, "observed samples=" .. observed)
  F.check("generated land OWE has a valid species graphics ID",
          validGfx, "must use OBJ_EVENT_MON, not a manual NPC")
  F.check("generated land OWE has been visible rather than hidden",
          visible, "screen evidence taken=" .. tostring(firstShot))
  F.check("generated land OWE changes map coordinates while idle",
          moved, "tracked IDs/species=" .. tostring(observed))
  F.shot("route29_final_state")
  F.finish()
end)
