-- Unverified step-3 QA: are candidate same-route land tables backed by a
-- REAL grass-behaviour tile in the actual experimental GBA map layout?
-- This checks tile existence, NOT tile reachability, catches or biome plausibility.
-- Generated proposed_grass_routes.lua is from this exact integrated World layout
-- and the same candidate-route-additions.json that produced the experimental ROM.
local here=(debug.getinfo(1,"S").source:sub(2)):match("^(.*[/\\])") or ""
package.path=here.."?.lua;"..package.path
local S=require("symbols")
local F=require("lib").new(S,"GrandWorldProposedGrassTiles")
local routes=dofile(here.."proposed_grass_routes.lua")
assert(#routes>0 and #routes<=36,"invalid proposed route list")

local function digits(n)
  return (n//100)%10,(n//10)%10,n%10
end

-- Use the same real map/metatile memory decoder as the already-passing
-- Route37 spontaneous encounter suite. 2 = MB_TALL_GRASS.
local function behavior(x,y)
  local b=S.gBackupMapLayout
  local w=F.r32(b+S.BackupMapLayout.width)
  local p=F.r32(b+S.BackupMapLayout.map)
  if w<1 or w>512 or p<0x02000000 or p>=0x02040000 then return -1 end
  local ax,ay=x+S.BackupMapLayout.mapOffset,y+S.BackupMapLayout.mapOffset
  if ax<0 or ay<0 then return -1 end
  local id=F.r16(p+(ax+ay*w)*2)&S.Metatiles.idMask
  local layout=F.r32(S.gMapHeader+S.MapHeader.mapLayout)
  if layout<0x08000000 or layout>=0x0A000000 then return -1 end
  local p1=F.r32(layout+S.MapLayout.primaryTileset)
  local p2=F.r32(layout+S.MapLayout.secondaryTileset)
  local split=S.Metatiles.inPrimary
  if (F.r8(p1+S.Tileset.flags1)&S.Tileset.hasFrlgAttributesBit)~=0
    or F.r8(layout+S.MapLayout.isFrlg)~=0
    or F.r8(layout+S.MapLayout.isJohto)~=0 then
    split=S.Metatiles.inPrimaryFrlg
  end
  local ts,localId=p1,id
  if id>=split then ts,localId=p2,id-split end
  local attrs=F.r32(ts+S.Tileset.metatileAttributes)
  if (F.r8(ts+S.Tileset.flags1)&S.Tileset.hasFrlgAttributesBit)~=0 then
    return F.r32(attrs+localId*4)&S.Metatiles.behaviorMaskFrlg
  end
  return F.r16(attrs+localId*2)&S.Metatiles.behaviorMask
end

local function countGrass()
  local base=S.gBackupMapLayout
  local width=F.r32(base+S.BackupMapLayout.width)
  local height=F.r32(base+S.BackupMapLayout.height)
  -- A completely unbounded scan could read outside actual EWRAM on a bad map.
  if width<1 or width>512 or height<1 or height>512
     or width*height>35000 then return -1,width,height end
  local count=0
  for y=0,height-1 do
    for x=0,width-1 do
      if behavior(x,y)==2 then count=count+1 end
    end
  end
  return count,width,height
end

F.run(function()
  client.speedmode(800)
  local started=F.boot(100)
  F.check("GBA booted into RegionHub before map grass survey",started and F.ow())
  if not started then F.finish();return end

  local seen={}
  for i,r in ipairs(routes) do
    local unique=r.group..":"..r.map
    F.check("candidate "..i.." has unique map ID",seen[unique]==nil)
    seen[unique]=true
    local gh,gt,go=digits(r.group)
    local mh,mt,mo=digits(r.map)
    local ok=F.warpTo(gh,gt,go,mh,mt,mo,0,0,0,r.group,r.map,"candidate_"..i)
    F.check("candidate "..i.." reached actual map "..r.name,
      ok and F.grp()==r.group and F.mapn()==r.map)
    if ok then
      local count,width,height=countGrass()
      F.L(string.format("  [grass-tile-survey] %s %s: %d tall grass tiles in map %dx%d",
        r.name,r.species,count,width,height))
      F.check("candidate "..i.." has at least one real tall-grass tile",
        count>0,"map="..r.name.." grass_count="..count.." size="..width.."x"..height)
      if i==1 or i==#routes then F.shot("candidate_"..i.."_tile_survey") end
    else
      F.check("candidate "..i.." grass cannot be certified without a warp",false)
    end
    if F.reportCrash("survey_"..i) then break end
  end
  -- This survey is NOT a capture/encounter rate proof nor an approval of
  -- land species such as sea fish in grass. Do not label release green.
  F.finish()
end)
