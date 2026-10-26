-- Targeted ROM-bound wild battle test. REAL walking, NO forced battle or RNG RAM edits.
-- Runs on a disposable PT-BR .gba through the pinned mGBA headless runner.
-- Checks the gap left by source-only rules and prior table-only World tests.
local here = (debug.getinfo(1, "S").source:sub(2)):match("^(.*[/\\])") or ""
package.path = here .. "?.lua;" .. package.path
local S = require("symbols")
local F = require("lib").new(S, "GrandWorldWildStep")

-- Same tile-decoder as the proven EncountersIncenseLink.lua; the map's
-- metatile behavior is more discriminating than a screenshot of green pixels.
local function behavior(x, y)
  local back = S.gBackupMapLayout
  local width = F.r32(back + S.BackupMapLayout.width)
  local tiles = F.r32(back + S.BackupMapLayout.map)
  if width < 1 or width > 512 or tiles < 0x02000000 or tiles >= 0x02040000 then
    return nil
  end
  local mx, my = x + S.BackupMapLayout.mapOffset, y + S.BackupMapLayout.mapOffset
  if mx < 0 or my < 0 then return nil end
  local id = F.r16(tiles + (mx + my * width) * 2) & S.Metatiles.idMask
  local layout = F.r32(S.gMapHeader + S.MapHeader.mapLayout)
  local first = F.r32(layout + S.MapLayout.primaryTileset)
  local second = F.r32(layout + S.MapLayout.secondaryTileset)
  local split = S.Metatiles.inPrimary
  if (F.r8(first + S.Tileset.flags1) & S.Tileset.hasFrlgAttributesBit) ~= 0
      or F.r8(layout + S.MapLayout.isFrlg) ~= 0
      or F.r8(layout + S.MapLayout.isJohto) ~= 0 then
    split = S.Metatiles.inPrimaryFrlg
  end
  local ts, localId = first, id
  if id >= split then ts, localId = second, id - split end
  local attrs = F.r32(ts + S.Tileset.metatileAttributes)
  if (F.r8(ts + S.Tileset.flags1) & S.Tileset.hasFrlgAttributesBit) ~= 0 then
    return F.r32(attrs + localId * 4) & S.Metatiles.behaviorMaskFrlg
  end
  return F.r16(attrs + localId * 2) & S.Metatiles.behaviorMask
end

local function hasLandHeader(grp, num)
  -- Same actual World header layout validated by EncountersIncenseLink.
  for i = 0, 512 do
    local ptr = S.gWildMonHeaders + i * 84
    local g, m = F.r8(ptr), F.r8(ptr + 1)
    if g == 255 and m == 255 then return false end
    if g == grp and m == num then return F.r32(ptr + 4) >= 0x08000000 end
  end
  return false
end

F.run(function()
  client.speedmode(800)
  local booted = F.boot(100)
  F.check("fresh PT-BR ROM reached controllable RegionHub", booted and F.ow() and F.grp() == 100)
  if not booted then F.finish(); return end

  -- Existing World debug action creates a checksum-valid party member.
  -- This stages a legal team, NEVER a battle or overworld Pokemon encounter.
  F.dbg(); F.sel(2); F.sel(9); F.idle(120); F.bOut(6); F.idle(60)
  F.check("legal party prepared through the in-game debug menu",
    F.r8(S.gPartiesCount) == 1, "party=" .. F.r8(S.gPartiesCount))

  -- Route 37 has a real entry warp and a previously documented walkable,
  -- wild-grass corridor x=17 between y=10 and y=21.
  local warped = F.warpTo(0,8,3,0,0,3,0,0,0,83,3,"wild_route37")
  F.check("real game warp setup reached Route 37", warped and F.grp() == 83 and F.mapn() == 3)
  if not warped then F.finish(); return end
  F.check("Route 37 carries nonempty real land encounter data", hasLandHeader(83, 3))

  local road, grass = 0, 0
  local battle, grassAtStart, localIdAtStart = false, false, 255
  local sawFatal = false
  local obstacle = false
  for sweep = 1, 24 do
    local dir = sweep % 2 == 1 and "Down" or "Up"
    local goal = dir == "Down" and 21 or 10
    for _ = 1, 14 do
      if not F.ow() then break end
      local x, y = F.pos()
      if y == goal then break end
      local moved = F.step(dir)
      -- Metatile is observed BEFORE callback transition and battle scene setup.
      local nx, ny = F.pos()
      local mb = behavior(nx, ny)
      if mb == 2 then grass = grass + 1
      elseif mb ~= nil then road = road + 1 end
      F.idle(24)
      if F.reportCrash("wild_step") then sawFatal = true; break end
      if not F.ow() then
        battle = true
        grassAtStart = mb == 2
        localIdAtStart = F.r8(S.gSpecialVar_LastTalked)
        F.L(string.format("REAL WILD TRIGGER at (%d,%d) metatile=%s prior=(%d,%d) localId=%d",
          nx, ny, tostring(mb), x, y, localIdAtStart))
        F.shot("wild_encounter_trigger")
        break
      end
      if not moved and nx == x and ny == y then obstacle = true; break end
    end
    if battle or obstacle or sawFatal then break end
  end
  F.check("walking really entered grass on Route 37", grass >= 3, "grass_steps=" .. grass)
  F.check("walking also sampled non-grass tiles", road >= 1, "non_grass_steps=" .. road)
  F.check("movement did not stick on a collision or fatal screen", not obstacle and not sawFatal)
  F.check("a spontaneous battle started from real GBA walking", battle)
  F.check("battle started on an actual tall-grass metatile", battle and grassAtStart)
  F.check("encounter was not triggered by touching an overworld wild sprite",
    battle and localIdAtStart == 0, "last_talked_local_id=" .. localIdAtStart)
  if battle then
    -- Wait for the REAL battle scene to finish its transition. No fake battle flags.
    F.idle(250)
  end
  F.check("actual battle initialized at least two battlers",
    battle and F.battlers() >= 2, "battlers=" .. F.battlers())
  F.check("no engine fatal assertion during the actual encounter",
    not sawFatal and not F.reportCrash("battle_started"))
  F.shot("final")
  F.finish()
end)
