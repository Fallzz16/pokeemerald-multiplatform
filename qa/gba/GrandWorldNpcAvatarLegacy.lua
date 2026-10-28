-- Compatibility regression: a PRE-M9 World migration fixture must not
-- silently acquire an NPC skin when loaded into the M9 GBA build.
-- Read-only; uses an original tracked test fixture, never a player's save.
local here=(debug.getinfo(1,"S").source:sub(2)):match("^(.*[/\\])") or ""
package.path=here.."?.lua;"..package.path
local S=require("symbols")
local F=require("lib").new(S,"GrandWorldNpcAvatarLegacy")
local function value(id)
  return F.r16(F.sb1()+S.SaveBlock1.vars+(id-0x4000)*2)
end
local function playerGfx()
  for i=0,15 do
    local p=S.gObjectEvents+i*S.ObjectEvent.stride
    if F.r8(p+S.ObjectEvent.localId)==255 and (F.r8(p)&1)==1 then
      return F.r16(p+S.ObjectEvent.graphicsId)
    end
  end
  return -1
end
local function pickerActive()
  for i=0,S.Task.count-1 do
    local p=S.gTasks+i*S.Task.stride
    if F.r8(p+S.Task.isActive)~=0
       and (F.r32(p+S.Task.func)&~1)==(S.GW_AvatarMenuInput&~1) then
      return true
    end
  end
  return false
end
F.run(function()
  F.check("new build contains original M9 NPC appearance code",S.GW_AvatarMenuInput>=0x08000000)
  -- Original v7.srm is a REAL saved position in Oldale Center (group 2,
  -- map 2, tile 7,4), not the new-game Region Hub. This makes the gate
  -- non-vacuous: a silently rejected save MUST NOT pass.
  local loaded=F.boot(2,true)
  F.check("old v7 fixture actually Continue-loaded, not rejected into New Game",
    loaded and F.ow() and F.grp()==2 and F.mapn()==2)
  if not loaded then F.finish();return end
  local x,y=F.pos()
  F.check("old save preserves harvested Oldale Center position",x==7 and y==4,
    "loaded pos="..x..","..y)
  F.check("old World save version migrated through native layout ladder",
    F.r8(F.sb2()+S.SaveBlock2.saveVersion)==S.SAVE_FORMAT_VERSION)
  F.check("unused original save variable resolves to CLASSICO",
    value(0x40E5)==0,"raw legacy 0x40E5="..value(0x40E5))
  F.check("original player graphics are live after loading old save",
    playerGfx()>=0,"player gfx="..playerGfx())
  F.check("legacy Continue never reopens new-game NPC picker",not pickerActive())
  F.check("no fatal screen when loading old World save",
    not F.reportCrash("npc_avatar_legacy"))
  F.shot("npc_avatar_old_world_save_classic")
  F.finish()
end)
