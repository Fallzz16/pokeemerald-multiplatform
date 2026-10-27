-- REAL battery-save reload validation for the permanent M9 GBA NPC appearance.
-- First process saves using Start-menu buttons. Second mGBA process AUTOBOOTS
-- that same disposable 128-KiB flash image, never a savestate or RAM edit.
local here=(debug.getinfo(1,"S").source:sub(2)):match("^(.*[/\\])") or ""
package.path=here.."?.lua;"..package.path
local S=require("symbols")
local F=require("lib").new(S,"GrandWorldNpcAvatarContinue")
local cfg=dofile(here.."gw_npc_avatar_target.lua")
assert(cfg.skinId>0 and cfg.skinId<=192 and cfg.graphicsId>0)

local function value(id)
  return F.r16(F.sb1()+S.SaveBlock1.vars+(id-0x4000)*2)
end
local function playerGfx()
  for i=0,15 do
    local o=S.gObjectEvents+i*S.ObjectEvent.stride
    if F.r8(o+S.ObjectEvent.localId)==255 and (F.r8(o)&1)==1 then
      return F.r16(o+S.ObjectEvent.graphicsId)
    end
  end
  return -1
end
local function menuTaskActive()
  for i=0,S.Task.count-1 do
    local t=S.gTasks+i*S.Task.stride
    if F.r8(t+S.Task.isActive)~=0
       and (F.r32(t+S.Task.func)&~1)==(S.GW_AvatarMenuInput&~1) then
      return true
    end
  end
  return false
end

F.run(function()
  F.check("same ARM build exports exact M9 NPC menu code",
    S.GW_AvatarMenuInput>=0x08000000)
  local entered=F.boot(100)
  F.check("continue booted real Region Hub with flash save",
    entered and F.ow() and F.grp()==100)
  if not entered then F.finish();return end
  F.check("NPC appearance survived full emulator restart and flash reload",
    value(0x40E5)==cfg.skinId,
    "loaded="..value(0x40E5).." expected="..cfg.skinId)
  F.check("original protagonist identity remains unchanged after Continue",
    value(0x40FB)==0)
  F.check("original protagonist gender remains unchanged after Continue",
    F.r8(F.sb2()+S.SaveBlock2.playerGender)==0)
  F.check("reloaded active player object renders chosen NPC",
    playerGfx()==cfg.graphicsId,
    "loaded gfx="..playerGfx().." expected gfx="..cfg.graphicsId)
  F.check("Continue does not reopen new-game NPC picker",
    not menuTaskActive())
  F.check("no fatal error after reloading a permanent NPC skin",
    not F.reportCrash("npc_avatar_continue"))
  F.shot("npc_avatar_flash_continue_world")
  F.finish()
end)
