-- Grand World GBA: first real wild battle completion tests (FLEE and CAPTURE).
-- NO writes to battle memory, RNG, monster count, or capture verdict. Only in-game
-- Debug -> Set Party/Give Item setup, then physical GBA inputs in real grass.
-- Run with GW_CYCLE_MODE=FLEE or CAPTURE on separate disposable mGBA sessions.
local here=(debug.getinfo(1,"S").source:sub(2)):match("^(.*[/\\])") or ""
package.path=here.."?.lua;"..package.path
local S=require("symbols")
-- Exact callbacks generated from THIS cartridge ELF; the function name occurs
-- in several controller files, so picking the first address would be unsafe.
local ACTION_FUNCS=dofile(here.."battle_action_callbacks.lua") -- interactive handlers, after DMA
local mode=os.getenv("GW_CYCLE_MODE")
assert(mode=="FLEE" or mode=="CAPTURE", "use GW_CYCLE_MODE=FLEE or CAPTURE")
local F=require("lib").new(S,"GrandWorldWild"..(mode=="FLEE" and "Flee" or "Capture"))
local MASTER_BALL=4
local ROUTE_GROUP,ROUTE_MAP=83,3
local ACTION_MENU_CURSOR=3
local PLAYER_CONTROLLER=0
local function tap(key)
  F.press(key,2);F.idle(13)
end
local function activeActionMenu()
  if S.gBattlerControllerFuncs<=0x02000000 or #ACTION_FUNCS==0 then return false end
  local now=F.r32(S.gBattlerControllerFuncs+PLAYER_CONTROLLER*4)&~1
  for _,fn in ipairs(ACTION_FUNCS) do
    if now==(fn&~1) then return true end
  end
  return false
end
-- A only advances story/battle intro when an action menu is NOT ready.
-- Checks every frame BEFORE pressing, so cannot accidentally choose FIGHT.
local function untilAction(limit)
  for n=1,limit do
    if activeActionMenu() then return true end
    joypad.set(n%48==1 and {A=true} or {})
    emu.frameadvance()
    if n%300==0 and F.reportCrash("await_battle_actions") then return false end
  end
  return activeActionMenu()
end
local function partyCount()
  return F.r8(S.gPartiesCount)
end
local function setTeam()
  F.dbg();F.sel(2);F.sel(9);F.idle(125);F.bOut(8);F.idle(80)
  return partyCount()==1
end
local function giveMasterBall()
  F.dbg();F.sel(3);F.sel(0)
  -- Debug item number spinner starts at 1: three genuine UP presses -> ID 4.
  for _=1,3 do tap("Up") end
  tap("A") -- item number confirmed
  tap("A") -- quantity defaults to one
  F.idle(130);F.bOut(8);F.idle(50)
  -- Bag slot is a real item entry, NOT an injected backpack fixture.
  local balls=F.r32(S.gBagPockets+S.BagPocket.stride+S.BagPocket.itemsPtr)
  if balls<0x02000000 or balls>=0x02040000 then return false end
  for i=0,F.pocketCap(1)-1 do
    if F.r16(balls+i*4)==MASTER_BALL then return true end
  end
  return false
end
-- Decode the actual metatile as in the existing EncountersIncenseLink suite.
-- Don't infer grass from the tile's colour or from a hardcoded rectangle.
local function behavior(x,y)
  local b=S.gBackupMapLayout
  local w=F.r32(b+S.BackupMapLayout.width)
  local p=F.r32(b+S.BackupMapLayout.map)
  if w==0 or w>512 or p<0x02000000 or p>=0x02040000 then return -1 end
  local ax,ay=x+S.BackupMapLayout.mapOffset,y+S.BackupMapLayout.mapOffset
  if ax<0 or ay<0 then return -1 end
  local id=F.r16(p+(ax+ay*w)*2)&S.Metatiles.idMask
  local layout=F.r32(S.gMapHeader+S.MapHeader.mapLayout)
  local p1=F.r32(layout+S.MapLayout.primaryTileset)
  local p2=F.r32(layout+S.MapLayout.secondaryTileset)
  local split=S.Metatiles.inPrimary
  if (F.r8(p1+S.Tileset.flags1)&S.Tileset.hasFrlgAttributesBit)~=0
    or F.r8(layout+S.MapLayout.isFrlg)~=0
    or F.r8(layout+S.MapLayout.isJohto)~=0 then
    split=S.Metatiles.inPrimaryFrlg
  end
  local tileset,localid=p1,id
  if id>=split then tileset,localid=p2,id-split end
  local attrs=F.r32(tileset+S.Tileset.metatileAttributes)
  if (F.r8(tileset+S.Tileset.flags1)&S.Tileset.hasFrlgAttributesBit)~=0 then
    return F.r32(attrs+localid*4)&S.Metatiles.behaviorMaskFrlg
  end
  return F.r16(attrs+localid*2)&S.Metatiles.behaviorMask
end
local function realWalkEncounter()
  local stepped,triggerGrass=0,false
  for sweep=1,28 do
    local dir=sweep%2==1 and "Down" or "Up"
    local endpoint=dir=="Down" and 21 or 10
    for n=1,18 do
      if not F.ow() then return true,stepped,triggerGrass end
      local x,y=F.pos()
      if y==endpoint then break end
      local nextY=y+(dir=="Down" and 1 or -1)
      local targetMb=behavior(x,nextY)
      -- Press a normal GBA direction; never call the battle generator.
      local moved=F.step(dir)
      F.idle(45)
      local x2,y2=F.pos()
      if targetMb==2 then stepped=stepped+1 end
      if not F.ow() then
        F.L(string.format("encounter after %d grass steps: attempted (%d,%d) mb=%d at (%d,%d)",
          stepped,x,nextY,targetMb,x2,y2))
        return true,stepped,targetMb==2
      end
      if not moved and x==x2 and y==y2 then
        F.L("blocked walking at "..x..","..y);return false,stepped,false
      end
      if n==18 and F.reportCrash("wild_walk") then return false,stepped,false end
    end
  end
  return false,stepped,false
end
local function comeBackToMap(limit)
  for n=1,limit do
    if F.ow() then return true end
    joypad.set(n%25==1 and {A=true} or {})
    emu.frameadvance()
    if n%400==0 and F.reportCrash("await_field_return") then return false end
  end
  return F.ow()
end

F.run(function()
  client.speedmode(800)
  local started=F.boot(100)
  F.check("fresh disposable PT-BR GBA starts in Hub",started and F.ow() and F.grp()==100)
  if not started then F.finish();return end
  F.check("valid battle party prepared with actual debug UI",setTeam())
  if mode=="CAPTURE" then
    F.check("Master Ball given by in-game UI and present in real Bag",giveMasterBall())
  end
  local reached=F.warpTo(0,8,3,0,0,3,0,0,0,ROUTE_GROUP,ROUTE_MAP,"cycle37")
  F.check("reached real Route 37 grass corridor",reached and F.grp()==ROUTE_GROUP and F.mapn()==ROUTE_MAP)
  if not reached then F.finish();return end
  F.check("team remained legal before wild battle",partyCount()==1)
  local entered,steps,grass=realWalkEncounter()
  F.check("walking covered at least one real grass tile",steps>0,"grass steps="..steps)
  F.check("physical walking triggered a battle without memory forcing",entered)
  F.check("the wild battle originated at a grass tile",entered and grass)
  if not entered then F.finish();return end
  local live=untilAction(16000)
  F.check("player's real interactive battle action handler became live",live)
  if not live then F.finish();return end
  F.idle(24)
  F.check("battle initialized its actual player and opponent",F.battlers()>=2,
    "battlers="..F.battlers())
  F.check("normal battle action selection starts at FIGHT",
    F.r8(S.gActionSelectionCursor)==0)
  F.shot("action_menu_"..mode)
  if mode=="FLEE" then
    tap("Down");tap("Right")
    F.check("GBA controller selected RUN action",
      F.r8(S.gActionSelectionCursor)==ACTION_MENU_CURSOR,
      "cursor="..F.r8(S.gActionSelectionCursor))
    tap("A")
    local returned=comeBackToMap(16000)
    F.check("real RUN action returned to overworld",returned)
    F.check("flee did not alter party count",partyCount()==1)
    F.check("flee returns to the same route",F.grp()==ROUTE_GROUP and F.mapn()==ROUTE_MAP)
  else
    tap("Right")
    F.check("GBA controller selected BAG action",F.r8(S.gActionSelectionCursor)==1,
      "cursor="..F.r8(S.gActionSelectionCursor))
    tap("A")
    F.idle(180)
    local battleCallback=F.cb2()
    F.check("battle BAG UI opened outside normal action menu",not activeActionMenu())
    -- The debug-created single Master Ball is the first entry in the Balls pocket.
    -- Navigate with physical R to the Poke Balls pocket; choose the first item
    -- and the first 'Use' context option, never inject gSpecialVar_ItemId.
    tap("Right");F.idle(130)
    F.shot("battle_balls")
    tap("A");F.idle(65)
    tap("A");F.idle(250)
    F.check("actual BAG selected Master Ball, not a fake item id",
      F.r16(S.gSpecialVar_ItemId)==MASTER_BALL,
      "selected item="..F.r16(S.gSpecialVar_ItemId))
    local returned=comeBackToMap(22000)
    F.check("Master Ball battle eventually returned to overworld",returned)
    F.check("wild Pokémon was added by game's catch logic",partyCount()==2,
      "party="..partyCount())
    F.check("captured Pokémon returns player to same route",
      F.grp()==ROUTE_GROUP and F.mapn()==ROUTE_MAP)
  end
  F.check("battle cycle produced no GBA fatal screen",not F.reportCrash("cycle_end"))
  F.shot("battle_end_"..mode)
  F.finish()
end)
