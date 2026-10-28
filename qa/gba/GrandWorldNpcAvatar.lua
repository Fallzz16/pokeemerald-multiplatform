-- M9: authentic Oak avatar selection -> persistent appearance -> player object gfx.
-- The World engine is compiled for ARM GBA and driven only by actual joypad input.
-- No save/RAM writes, no forced screen/task state, no ROM assets exported.
local here=(debug.getinfo(1,"S").source:sub(2)):match("^(.*[/\\])") or ""
package.path=here.."?.lua;"..package.path
local S=require("symbols")
local F=require("lib").new(S,"GrandWorldNpcAvatar")
local cfg=dofile(here.."gw_npc_avatar_target.lua")
assert(cfg.skinId>0 and cfg.skinId<=192 and cfg.graphicsId>0 and cfg.page>=0 and cfg.row>=0 and cfg.row<6)

local function var(id)
  return F.r16(F.sb1()+S.SaveBlock1.vars+(id-0x4000)*2)
end
local function activeTask(symbol)
  for i=0,S.Task.count-1 do
    local base=S.gTasks+i*S.Task.stride
    if F.r8(base+S.Task.isActive)~=0 and
       (F.r32(base+S.Task.func)&~1)==(symbol&~1) then return true end
  end
  return false
end
local function waitTask(symbol,limit)
  for f=1,limit do
    if activeTask(symbol) then return true end
    joypad.set(f%18==1 and {A=true} or {})
    emu.frameadvance()
  end
  F.shot("npc_menu_timeout")
  return false
end
local function key(k)F.press(k,2);F.idle(16)end
local function playerGfx()
  -- World constants: LOCALID_PLAYER=255, ObjectEvent graphicsId=u16 at +4.
  -- Only live and active objects are accepted, not a coincidental NPC gfx.
  for i=0,15 do
    local p=S.gObjectEvents+i*S.ObjectEvent.stride
    if F.r8(p+S.ObjectEvent.localId)==255 and
       (F.r8(p)&1)==1 then
       return F.r16(p+S.ObjectEvent.graphicsId)
    end
  end
  return -1
end
F.run(function()
  client.speedmode(800)
  F.check("exact-ROM source exports the genuine NPC menu task",
    S.GW_AvatarMenuInput>=0x08000000 and
    S.gTasks>=0x02000000 and S.gObjectEvents>=0x02000000)
  local menu=waitTask(S.GW_AvatarMenuInput,120000)
  F.check("real Oak NPC appearance menu reached with joypad",menu)
  if not menu then F.finish();return end
  F.check("classico is default first row",F.mcur()==0)
  F.shot("npc_avatar_menu_first_page")
  for _=1,cfg.page do key("R") end
  F.check("pagination kept the GBA NPC menu interactive",activeTask(S.GW_AvatarMenuInput))
  for _=1,cfg.row do key("Down") end
  F.check("real cursor reached source-indexed NPC",F.mcur()==cfg.row,
          "row="..F.mcur().." expect="..cfg.row)
  F.shot("npc_avatar_selected_row")
  key("A")
  F.check("NPC appearance index committed through GBA input",
    var(0x40E5)==cfg.skinId,"saved="..var(0x40E5).." expected="..cfg.skinId)
  F.check("legacy hero identity independent from NPC appearance",var(0x40FB)==0)
  F.check("gender preserved by appearance menu",
    F.r8(F.sb2()+S.SaveBlock2.playerGender)==0)
  local entered=F.boot(100)
  F.check("GBA reached real three-region hub after Oak",entered and F.ow() and F.grp()==100)
  if not entered then F.finish();return end
  F.check("NPC appearance survived NewGame ClearSav1",var(0x40E5)==cfg.skinId)
  F.check("actual PLAYER object uses chosen NPC graphics ID",
    playerGfx()==cfg.graphicsId,
    string.format("live gfx=%d expected=%d",playerGfx(),cfg.graphicsId))
  F.check("six-hero identity still persisted in SaveBlock1",var(0x40FB)==0)
  F.check("no fatal screen while selecting and loading NPC",
    not F.reportCrash("npc_avatar_final"))
  F.shot("npc_avatar_actual_player_in_region_hub")
  -- Optional full battery-save round-trip: only used in disposable CI runner.
  -- These are REAL Start/A inputs, following World's tested StoryProgress.lua
  -- wheel path. No memory writes or savestates are used to fake persistence.
  if os.getenv("PW_NPC_SAVE_ROUNDTRIP") == "1" then
    -- Native World uses a reorderable six-icon start wheel. Selecting a
    -- FIXED offset (old SaveHarvest approach) now opens Story instead of Save!
    -- Match World's proven StoryProgress.lua: real USM Save icon ID is 7.
    F.press("Start",2); F.idle(90)
    local foundSave = F.selectStartIcon(7)
    F.check("source-identified Save icon available in live Start menu",
      foundSave)
    if not foundSave then F.finish(); return end
    F.shot("npc_save_icon_selected")
    for i=1,3 do
      F.press("A",2); F.idle(90)
      F.shot("npc_save_confirmation_"..i)
    end
    F.idle(600) -- let the real Flash Save dialog finish writing
    F.check("original NPC ID unchanged after in-game Save inputs",
      var(0x40E5)==cfg.skinId)
    F.check("six-hero identity preserved after Save inputs",
      var(0x40FB)==0)
    F.shot("npc_avatar_saved_using_start_menu")
    -- A battery file is only proof when the separate runner confirms that
    -- mGBA wrote it to flash AND another process successfully loads it.
  end
  F.finish()
end)
