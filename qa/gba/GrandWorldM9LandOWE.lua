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
local WILD_HEADER_STRIDE = 84 -- same verified ABI used by EncountersIncenseLink.lua

-- These are the original World debug-controller inputs. They only populate a
-- disposable CI test party; no generated OWE is fabricated or inserted.
local function prepareParty()
  if F.r8(S.gPartiesCount) ~= 0 then return true end
  F.dbg()
  F.idle(60)
  for _ = 1, 2 do F.press("Down", 3); F.idle(16) end
  F.press("A", 3); F.idle(60)
  for _ = 1, 9 do F.press("Down", 3); F.idle(16) end
  F.press("A", 3); F.idle(180)
  for _ = 1, 8 do F.press("B", 3); F.idle(20) end
  return F.r8(S.gPartiesCount) > 0
end

local function getLandHeader()
  -- Detect missing land encounter header before attributing zero OWEs to VRAM.
  -- Header ABI from pinned World's EncountersIncenseLink.lua test.
  for i = 0, 1024 do
    local header = S.gWildMonHeaders + i * WILD_HEADER_STRIDE
    local grp, map = F.r8(header), F.r8(header + 1)
    if grp == 255 and map == 255 then return nil end
    if grp == ROUTE29_GROUP and map == ROUTE29_MAP then
      return F.r32(header + 4), i
    end
  end
  return nil
end

-- Read the actual live map grid to route around trees/gates; NEVER move the
-- avatar through memory or teleport to a grass tile. Collision bits are the
-- packed World map format (include/global.fieldmap.h, bits 10-11).
local function gridBlock(x, y)
  local b = S.gBackupMapLayout
  local w = F.r32(b + S.BackupMapLayout.width)
  local h = F.r32(b + S.BackupMapLayout.height)
  local mem = F.r32(b + S.BackupMapLayout.map)
  local gx, gy = x + S.BackupMapLayout.mapOffset,
                 y + S.BackupMapLayout.mapOffset
  if w < 1 or w > 256 or h < 1 or h > 256 or
     gx < 7 or gy < 7 or gx >= w - 7 or gy >= h - 7 or
     mem < 0x02000000 or mem >= 0x02040000 then
    return nil
  end
  return F.r16(mem + (gx + gy * w) * 2)
end

local DIR = {
  {0, -1, "Up"}, {0, 1, "Down"},
  {-1, 0, "Left"}, {1, 0, "Right"},
}
local function tileKey(x, y) return x .. "," .. y end

local function findRoute(sx, sy, tx, ty, blocked)
  local queue = {{x=sx, y=sy}}
  local seen = {[tileKey(sx,sy)] = true}
  local previous = {}
  local head = 1
  while head <= #queue and #queue < 1000 do
    local current = queue[head]
    if current.x == tx and current.y == ty then
      local steps = {}
      local k = tileKey(tx, ty)
      while previous[k] do
        local p = previous[k]
        table.insert(steps, 1, p.step)
        k = p.from
      end
      return steps
    end
    head = head + 1
    for _, dir in ipairs(DIR) do
      local nx, ny = current.x + dir[1], current.y + dir[2]
      local key = tileKey(nx, ny)
      local block = gridBlock(nx, ny)
      if not seen[key] and not blocked[key] and block and
         ((block >> 10) & 3) == 0 then
        seen[key] = true
        previous[key] = {from=tileKey(current.x,current.y),
                         step={x=nx,y=ny,dir=dir[3]}}
        queue[#queue + 1] = {x=nx, y=ny}
      end
    end
  end
  return nil
end

local function reachField(tx, ty)
  local blocked = {}
  for attempt = 1, 24 do
    if not F.ow() or F.grp() ~= ROUTE29_GROUP or F.mapn() ~= ROUTE29_MAP then
      return false, "left overworld or entered a traditional battle"
    end
    local cx, cy = F.pos()
    if cx == tx and cy == ty then return true, "arrived via normal controls" end
    local route = findRoute(cx, cy, tx, ty, blocked)
    if not route then return false, "no collision-safe path found" end
    F.L(string.format("  mapgrid detour attempt=%d from=(%d,%d) steps=%d",
                      attempt, cx, cy, #route))
    local blockedThisAttempt = false
    for _, step in ipairs(route) do
      if not F.ow() or F.grp() ~= ROUTE29_GROUP or F.mapn() ~= ROUTE29_MAP then
        return false, "real encounter or map connection interrupted path"
      end
      if not F.step(step.dir) then
        blocked[tileKey(step.x, step.y)] = true
        blockedThisAttempt = true
        F.L(string.format("  real field collision %s at (%d,%d), rerouting",
                          step.dir, step.x, step.y))
        break
      end
    end
    if not blockedThisAttempt then
      local x, y = F.pos()
      if x == tx and y == ty then return true, "arrived" end
    end
  end
  return false, "navigation retry budget exhausted"
end

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
  F.check("disposable test party is available for legitimate wild battles", prepareParty(),
          "party count=" .. F.r8(S.gPartiesCount))
  local arrived = F.warpTo(0, 7, 5, 0, 0, 2, 0, 0, 0,
                           ROUTE29_GROUP, ROUTE29_MAP, "m9_land_route29")
  F.check("reached Route 29 without RAM warp", arrived and F.grp() == ROUTE29_GROUP
          and F.mapn() == ROUTE29_MAP)
  if not arrived then F.finish(); return end
  local info, headerIdx = getLandHeader()
  F.check("Route 29 has a resident wild land encounter table",
          info ~= nil and info ~= 0,
          string.format("index=%s landInfo=0x%08X", tostring(headerIdx), info or 0))

  -- Original World battle-palette field fixture uses Route29 (25,9). Warp 0
  -- exits at (34,11), close to a gate but potentially outside any grass patch.
  -- Walking there uses ordinary GBA button inputs; do not move avatar via RAM.
  local walked, walkReason = reachField(25, 9)
  local cx, cy = F.pos()
  F.check("player traversed into the tested Route 29 field area",
          walked and cx == 25 and cy == 9 and F.ow(),
          string.format("pos=(%d,%d), ow=%s, reason=%s",
                        cx, cy, tostring(F.ow()), walkReason))
  F.shot("route29_field_probe")

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
