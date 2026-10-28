-- GBA native menu regression: default CLASSICO, L/R wrap and B cancel.
-- Real joypad only; no save writes, cheats or RAM modifications.
local here=(debug.getinfo(1,"S").source:sub(2)):match("^(.*[/\\])") or ""
package.path=here.."?.lua;"..package.path
local S=require("symbols")
local F=require("lib").new(S,"GrandWorldNpcAvatarClassic")
local cfg=dofile(here.."gw_npc_avatar_target.lua")
assert(cfg.skinId==0 and cfg.graphicsId>=0)
local function avatarVar(id)
  return F.r16(F.sb1()+S.SaveBlock1.vars+(id-0x4000)*2)
end
local function pickerActive()
  for i=0,S.Task.count-1 do
    local b=S.gTasks+i*S.Task.stride
    if F.r8(b+S.Task.isActive)~=0 and
       (F.r32(b+S.Task.func)&~1)==(S.GW_AvatarMenuInput&~1) then
      return true
    end
  end
  return false
end
local function findPlayerGfx()
  for i=0,15 do
    local o=S.gObjectEvents+i*S.ObjectEvent.stride
    if F.r8(o+S.ObjectEvent.localId)==255 and (F.r8(o)&1)==1 then
      return F.r16(o+S.ObjectEvent.graphicsId)
    end
  end
  return -1
end
local function key(k) F.press(k,2); F.idle(16) end
F.run(function()
  local found=false
  for i=1,120000 do
    if pickerActive() then found=true; break end
    joypad.set(i%18==1 and {A=true} or {})
    emu.frameadvance()
  end
  F.check("reached real NPC picker using GBA controls",found)
  if not found then F.finish();return end
  F.check("new game defaults to classic appearance",avatarVar(0x40E5)==0)
  F.check("initial cursor starts on CLASSICO",F.mcur()==0)
  key("L") -- wrap from page 0 to final page 32
  F.check("L-wrap stays in live picker",pickerActive())
  key("Down") -- last page contains just SAGE; cursor cannot move past row0
  F.check("last page has one selectable row",F.mcur()==0)
  key("R") -- wrap back to first page
  F.check("R-wrap returns safely to first-page cursor",pickerActive() and F.mcur()==0)
  F.shot("npc_avatar_classic_after_wrap")
  key("B") -- permanently retain CLASSICO, do not pick SAGE by mistake
  F.check("B cancel retains classic skin",avatarVar(0x40E5)==0)
  F.check("legacy six-hero identity remains selected",avatarVar(0x40FB)==0)
  local arrived=F.boot(100)
  F.check("classic protagonist enters real Region Hub",arrived and F.ow() and F.grp()==100)
  if not arrived then F.finish();return end
  F.check("classic PLAYER graphics are original Brendan",
    findPlayerGfx()==cfg.graphicsId,
    "live gfx="..findPlayerGfx().." expected="..cfg.graphicsId)
  F.check("no fatal GBA screen after B cancel and L/R wrapping",
    not F.reportCrash("npc_avatar_classic"))
  F.shot("npc_avatar_original_hero_unchanged")
  F.finish()
end)
