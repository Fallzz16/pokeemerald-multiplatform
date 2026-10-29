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

-- Adapted directly from pinned World's EncountersIncenseLink.lua runtime
-- metatile reader. Map JSON or a visually green tile alone cannot prove
-- the actual in-game encounter behavior used by TrySelectTileForOWE.
local function metatileBehavior(x, y)
  local block = gridBlock(x, y)
  if not block then return nil end
  local id = block & S.Metatiles.idMask
  local layout = F.r32(S.gMapHeader + S.MapHeader.mapLayout)
  local primary = F.r32(layout + S.MapLayout.primaryTileset)
  local secondary = F.r32(layout + S.MapLayout.secondaryTileset)
  local flags1 = F.r8(primary + S.Tileset.flags1)
  local inPrimary = S.Metatiles.inPrimary
  if (flags1 & S.Tileset.hasFrlgAttributesBit) ~= 0
     or F.r8(layout + S.MapLayout.isFrlg) ~= 0
     or F.r8(layout + S.MapLayout.isJohto) ~= 0 then
    inPrimary = S.Metatiles.inPrimaryFrlg
  end
  local ts, localId
  if id < inPrimary then ts, localId = primary, id
  else ts, localId = secondary, id - inPrimary end
  local attrs = F.r32(ts + S.Tileset.metatileAttributes)
  if (F.r8(ts + S.Tileset.flags1) & S.Tileset.hasFrlgAttributesBit) ~= 0 then
    return F.r32(attrs + localId * 4) & S.Metatiles.behaviorMaskFrlg
  end
  return F.r16(attrs + localId * 2) & S.Metatiles.behaviorMask
end

local function countNearbyGrass(cx, cy, silent)
  local grass, mismatched = 0, 0
  local types = {}
  local center = gridBlock(cx, cy)
  if not center then return 0 end
  local elevation = (center >> 12) & 15
  for y = cy - 4, cy + 4 do
    for x = cx - 7, cx + 7 do
      if math.abs(x - cx) > 1 or math.abs(y - cy) > 1 then
        local b = gridBlock(x, y)
        if b and ((b >> 10) & 3) == 0 then
          local behavior = metatileBehavior(x, y)
          if behavior then
            types[behavior] = (types[behavior] or 0) + 1
            -- World explicitly rejects different-elevation land spawns.
            -- Nearby grass on another ledge is not spawnable grass.
            if behavior == 2 or behavior == 3 then
              if ((b >> 12) & 15) == elevation then grass = grass + 1
              else mismatched = mismatched + 1 end
            end
          end
        end
      end
    end
  end
  if not silent then
    local details = {}
    for behavior, n in pairs(types) do details[#details + 1] = behavior .. ":" .. n end
    table.sort(details)
    F.L(string.format("  Route29 window: elevation=%d same-level grass=%d other-level grass=%d types={%s}",
                      elevation, grass, mismatched, table.concat(details, ", ")))
  end
  return grass
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

-- Find a field vantage point CONNECTED to the current player tile. Route29
-- gate warp 0 is a tree-lined courtyard: hardcoding (25,9) picks a tile
-- outside its connected walkable component and falsely blames OWE spawning.
-- Search only real passable map tiles and require real tall/long grass in the
-- 15x9 spawn rectangle. Prefer a dry standing tile, preserving random battles.
local function findFieldVantage()
  local sx, sy = F.pos()
  local queue = {{x=sx,y=sy,d=0}}
  local seen = {[tileKey(sx,sy)] = true}
  local head, fallback = 1, nil
  while head <= #queue and #queue <= 1800 do
    local p = queue[head]
    head = head + 1
    local current = gridBlock(p.x,p.y)
    local ownBehavior = metatileBehavior(p.x,p.y)
    local dry = ownBehavior ~= 2 and ownBehavior ~= 3
    local elevation = current and ((current >> 12) & 15)
    local grass = countNearbyGrass(p.x,p.y,true)
    -- Require a WALKABLE adjacent grass tile on the same elevation as the
    -- vantage. Eight grass tiles visible through a tree wall is not habitat.
    local adjacent = false
    for _, dir in ipairs(DIR) do
      local x, y = p.x+dir[1], p.y+dir[2]
      local block = gridBlock(x,y)
      local behavior = metatileBehavior(x,y)
      if block and ((block >> 10) & 3) == 0 and
         ((block >> 12) & 15) == elevation and
         (behavior == 2 or behavior == 3) then
        adjacent = true
      end
    end
    if grass > 0 and adjacent and dry then
      F.L(string.format("  connected grass edge=(%d,%d), path=%d, same-level grass=%d",
                        p.x,p.y,p.d,grass))
      return p.x,p.y,grass
    end
    -- Some routes have no dry verge; a reachable grass tile is an honest
    -- fallback. Walking into it may trigger vanilla random encounters.
    if (ownBehavior == 2 or ownBehavior == 3) and not fallback then
      fallback={x=p.x,y=p.y,grass=math.max(grass,1)}
    end
    for _, dir in ipairs(DIR) do
      local x, y = p.x+dir[1], p.y+dir[2]
      local key = tileKey(x,y)
      local block = gridBlock(x,y)
      if not seen[key] and block and ((block >> 10) & 3) == 0 then
        seen[key] = true
        queue[#queue+1] = {x=x,y=y,d=p.d+1}
      end
    end
  end
  if fallback then
    F.L(string.format("  reachable grass tile fallback=(%d,%d)",
                      fallback.x,fallback.y))
    return fallback.x,fallback.y,fallback.grass
  end
  F.L("  NO connected grass tile found from Route29 gate entry")
  return nil,nil,0
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

-- Live occupancy probes, NOT static linker RAM and NOT a synthetic OAM test.
-- The World symbol generator derives offsets from the same ARM build.
local function logRuntimeBudget(stage)
  local activeObjects, activeSprites, usedPalettes = 0, 0, 0
  for i = 0, 15 do
    if (F.r8(S.gObjectEvents + i * S.ObjectEvent.stride) & 1) ~= 0 then
      activeObjects = activeObjects + 1
    end
  end
  for i = 0, S.Sprite.count - 1 do
    if (F.r16(S.gSprites + i * S.Sprite.stride + S.Sprite.inUse) & 1) ~= 0 then
      activeSprites = activeSprites + 1
    end
  end
  for i = 0, S.SpritePalette.count - 1 do
    if F.r16(S.sSpritePaletteTags + i * 2) ~= S.SpritePalette.free then
      usedPalettes = usedPalettes + 1
    end
  end
  F.L(string.format("  LIVE GBA %s: objectEvents=%d/16 sprites=%d/%d objPalettes=%d/%d",
                    stage, activeObjects, activeSprites, S.Sprite.count,
                    usedPalettes, S.SpritePalette.count))
end

-- Source-pinned local EWRAM symbols emitted only for the experimental test
-- ROM via the workflow's GenLuaSymbols.py adapter. Read-only inspection:
-- countdown=255 means encounters were disabled; a changing nonzero countdown
-- means the update loop is live even when no visible object is created.
local function logSpawnGuard(stage)
  local countdown = F.r8(S.sOWESpawnCountdown)
  local lock = F.r8(S.sLockFieldControls)
  F.L(string.format("  OWE GUARDS %s: countdown=%d fieldControlsLocked=%d",
                    stage, countdown, lock))
end

local STAGES = {
  "frames", "field_or_dexnav_lock", "no_land_header", "owe_area_disabled",
  "countdown_tick", "player_mid_step", "no_spawn_slot", "water_guard",
  "rejected_spawn_tile", "filtered_or_missing_species", "graphics_budget",
  "real_spawn_success", "passed_header", "timer_phase",
  "countdown_completed", "attempt_started"
}
local function logOWEStages(stage)
  local parts = {}
  for i = 0, 15 do
    parts[#parts+1] = STAGES[i+1] .. "=" .. F.r16(S.gM9OWEProbe + i*2)
  end
  F.L("  OWE STAGES " .. stage .. ": " .. table.concat(parts, " "))
end

-- Fully live encounter QA. Move by ordinary GBA buttons to an accessible tile
-- beside a generated OWE and press A. Do not seed IDs, inject objects, force
-- scripts, edit flags/coordinates, or disable vanilla random encounters.
-- A traditional grass battle MUST NOT count as an OWE interaction.
local function battleWithGeneratedLandOWE()
  local knownSpecies = {}
  local engagedId, engagedSpecies
  local function remember()
    local mons=generated()
    for id, o in pairs(mons) do
      if o.visible and o.species > 0 then knownSpecies[id]=o.species end
    end
    return mons
  end
  local function checkEngaged()
    local id=F.r16(S.gSpecialVar_LastTalked)
    if id >= OWE_LOW and id <= OWE_HIGH and knownSpecies[id] then
      engagedId, engagedSpecies = id, knownSpecies[id]
      F.L(string.format("  live generated OWE interaction id=%d species=%d",
                        engagedId, engagedSpecies))
      return true
    end
    return false
  end
  local function battleStarted()
    return F.battlers() >= 2
  end
  for attempt=1,45 do
    if F.reportCrash("owe_interact_"..attempt) then break end
    if battleStarted() or not F.ow() then break end
    local mons=remember()
    local px,py=F.pos()
    local best=nil
    for id,o in pairs(mons) do
      if o.visible and o.species > 0 then
        for _,dir in ipairs(DIR) do
          local ax,ay=o.x-dir[1],o.y-dir[2]
          local block=gridBlock(ax,ay)
          local own=gridBlock(px,py)
          if block and own and ((block >> 10) & 3)==0
             and ((block >> 12) & 15)==((own >> 12) & 15) then
            local route=findRoute(px,py,ax,ay,{})
            if route and #route <= 14 then
              local beh=metatileBehavior(ax,ay)
              local penalty=((beh==2 or beh==3) and 6 or 0)
              local score=#route+penalty
              if not best or score<best.score then
                best={id=id,species=o.species,route=route,
                      face=dir[3],x=ax,y=ay,score=score}
              end
            end
          end
        end
      end
    end
    if not best then
      F.idle(30)
    elseif #best.route > 0 then
      -- Re-plan after EVERY step because OWEs move autonomously.
      local routeStep=best.route[1]
      F.step(routeStep.dir)
      checkEngaged()
    else
      -- Require the SAME live OWE still be adjacent before pressing A.
      local mon=generated()[best.id]
      if mon and mon.species==best.species and
         math.abs(mon.x-px)+math.abs(mon.y-py)==1 then
        local face=nil
        for _,d in ipairs(DIR) do
          if px+d[1]==mon.x and py+d[2]==mon.y then face=d[3] end
        end
        if face then
          F.face(face)
          F.press("A",2)
          checkEngaged()
          F.idle(12)
          F.L(string.format("  OWE interaction attempt=%d id=%d pos=(%d,%d) lastTalked=%d",
                            attempt,best.id,px,py,F.r16(S.gSpecialVar_LastTalked)))
        end
      end
    end
    if engagedId then break end
  end

  if not engagedId then
    F.L(string.format("  no generated OWE engagement; cb2=0x%08X battlers=%d lastTalked=%d",
                      F.cb2(),F.battlers(),F.r16(S.gSpecialVar_LastTalked)))
    F.shot("owe_interaction_not_engaged")
    return false,false,"no generated local ID engaged"
  end
  F.shot("generated_owe_interaction")
  -- Scripted OWEs can play a cry and approach before the battle callback.
  for t=1,1200 do
    if battleStarted() then
      F.idle(90)
      local battleSpecies=F.r16(S.gBattleMons+S.BattlePokemon.size)
      F.L(string.format("  real OWE battle id=%d expected=%d battleSpecies=%d battlers=%d",
                        engagedId,engagedSpecies,battleSpecies,F.battlers()))
      F.shot("real_generated_owe_battle")
      return true,battleSpecies==engagedSpecies,
             string.format("id=%d expected=%d battleSpecies=%d",
                           engagedId,engagedSpecies,battleSpecies)
    end
    if t%32==0 then F.press("A",1) else F.idle(1) end
    if t%120==0 and F.reportCrash("owe_battle_wait") then break end
  end
  F.shot("owe_battle_not_started")
  return false,false,string.format("id=%d never started a real battle",engagedId)
end

-- End-to-end battle lifecycle: use the same real button-only RUN sequence
-- exercised by pinned World's KenyaMail.lua. No battle-outcome, HP, flags,
-- party or ROM memory is ever written by the test. A normal loss/whiteout
-- or a stray overworld transition MUST NOT be mistaken for a successful flee.
local function fleeGeneratedLandBattle()
  if F.ow() or F.battlers() < 2 then
    return false,false,false,"no active generated wild battle"
  end
  local sawRunOutcome = false
  local returned = false
  for attempt = 1, 220 do
    if F.reportCrash("generated_owe_flee_" .. attempt) then break end
    if F.outcome() == 4 then sawRunOutcome = true end -- B_OUTCOME_RAN
    if F.ow() then returned = true; break end
    -- B backs out of submenus; Right + Down selects RUN in the
    -- World's 2x2 battle command menu; A confirms. Retry if a faster
    -- wild mon prevents escape on an early turn.
    F.press("B",2);     F.idle(6)
    F.press("Right",2); F.idle(6)
    F.press("Down",2);  F.idle(6)
    F.press("A",2);     F.idle(14)
    if F.outcome() == 4 then sawRunOutcome = true end
    if attempt == 1 or attempt % 25 == 0 then
      F.L(string.format("  OWE escape attempt=%d outcome=%d battlers=%d ow=%s",
                        attempt,F.outcome(),F.battlers(),tostring(F.ow())))
    end
  end
  if F.ow() then returned = true end
  if returned then F.idle(60) end
  local sameRoute = returned and F.grp() == ROUTE29_GROUP
                           and F.mapn() == ROUTE29_MAP
  F.L(string.format("  OWE battle exit: ran=%s overworld=%s sameRoute=%s outcome=%d map=(%d,%d) pos=(%d,%d)",
                    tostring(sawRunOutcome),tostring(returned),tostring(sameRoute),
                    F.outcome(),F.grp(),F.mapn(),F.pos()))
  F.shot(returned and "generated_owe_battle_return" or "generated_owe_exit_failed")
  return sawRunOutcome,returned,sameRoute,
         string.format("ran=%s overworld=%s map=(%d,%d) outcome=%d",
                       tostring(sawRunOutcome),tostring(returned),
                       F.grp(),F.mapn(),F.outcome())
end

-- Confirm the native OWE field update loop resumes AFTER a genuine wild battle,
-- not merely that the battle screen transitioned away. Counter is exported on
-- the disposable instrumentation build only (16-bit wrap is accounted for).
local function checkOWELoopAfterBattle()
  if not F.ow() or F.grp() ~= ROUTE29_GROUP or F.mapn() ~= ROUTE29_MAP then
    return false,"not in Route29 overworld after fight"
  end
  local before=F.r16(S.gM9OWEProbe)
  F.idle(180)
  local after=F.r16(S.gM9OWEProbe)
  local delta=(after-before) & 0xFFFF
  local active=F.ow() and F.grp()==ROUTE29_GROUP and F.mapn()==ROUTE29_MAP
  F.L(string.format("  OWE postbattle update: framesBefore=%d framesAfter=%d delta=%d overworld=%s",
                    before,after,delta,tostring(active)))
  logRuntimeBudget("field-after-real-battle-flee")
  logOWEStages("field-after-real-battle-flee")
  F.shot("generated_owe_postbattle_field")
  return active and delta >= 60,
         string.format("OWE frame delta=%d sameRoute=%s",delta,tostring(active))
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

  -- Find nearby reachable tall/long grass using the in-game map grid.
  -- Walking uses ordinary GBA button inputs; never write player coordinates.
  local tx, ty, predictedGrass = findFieldVantage()
  local walked, walkReason = false, "no reachable grass tiles"
  if tx and predictedGrass > 0 then
    walked, walkReason = reachField(tx, ty)
  end
  local cx, cy = F.pos()
  F.check("player traversed to a connected Route 29 terrestrial spawn area",
          walked and cx == tx and cy == ty and F.ow(),
          string.format("pos=(%d,%d), dest=(%s,%s), ow=%s, reason=%s",
                        cx, cy, tostring(tx), tostring(ty), tostring(F.ow()), walkReason))
  F.shot("route29_field_probe")
  logRuntimeBudget("field-before-spawn")
  logSpawnGuard("field-before-spawn")
  logOWEStages("field-before-spawn")
  local grass = countNearbyGrass(cx, cy)
  F.check("Route 29 vantage point has actual encounter-grass tiles in spawn radius",
          walked and grass > 0, "grass tiles=" .. grass)

  -- Sample actual World object-event table, not the wild encounter config.
  -- 4-second intervals, up to 40 seconds in-game. Wait while stationary so
  -- the engine's mid-step spawn guard cannot artificially suppress spawning.
  local seen, moved, visible, validGfx = {}, false, false, false
  local observed, firstShot = 0, false
  -- 47 is intentionally coprime with 30-frame minimum retry: sampling
  -- every 60 frames previously aliased the countdown to the same value.
  for n = 1, 51 do
    F.idle(47)
    if n == 1 or n == 2 or n == 3 or n == 10 or n == 20 or n == 40 then
      logSpawnGuard("sample-" .. n)
    end
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
  logRuntimeBudget("field-after-2400-frames")
  logSpawnGuard("field-after-2400-frames")
  logOWEStages("field-after-2400-frames")
  F.shot("route29_final_state")
  local battled, speciesMatched, reason = battleWithGeneratedLandOWE()
  F.check("contact with an automatically generated terrestrial OWE starts a real battle",
          battled, reason)
  F.check("real OWE battle opponent species matches the contacted overworld mon",
          battled and speciesMatched, reason)
  -- This is a SEPARATE lifecycle gate. Battle start alone is not completion.
  -- Deliberately emit failed assertions when the OWE battle never started.
  local ran,returned,sameRoute,exitDetail = false,false,false,"no OWE battle"
  if battled and speciesMatched then
    ran,returned,sameRoute,exitDetail=fleeGeneratedLandBattle()
  end
  F.check("generated OWE battle ends by the real RUN action",
          ran,exitDetail)
  F.check("after fleeing a generated OWE the player returns to Route29",
          ran and returned and sameRoute,exitDetail)
  local resumed,updateDetail = false,"battle did not return to Route29"
  if ran and returned and sameRoute then
    resumed,updateDetail=checkOWELoopAfterBattle()
  end
  F.check("terrestrial OWE updater resumes after real battle exit",
          resumed,updateDetail)
  F.finish()
end)
