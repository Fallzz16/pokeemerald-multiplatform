-- New unverified GBA acceptance: does the EXPERIMENTAL grass-table Qwilfish
-- actually spawn through walking in Route 32? No battle/RNG/party/species RAM
-- writes. In-game debug menu is used only for the legal starting party & warp.
-- This probe is separate from the 33/33 green capture/flee suites.
local here=(debug.getinfo(1,"S").source:sub(2)):match("^(.*[/\\])") or ""
package.path=here.."?.lua;"..package.path
local S=require("symbols")
local F=require("lib").new(S,"GrandWorldExperimentalQwilfish")
local config=dofile(here.."experimental_species_target.lua")
local callbacks=dofile(here.."battle_action_callbacks.lua")
local TARGET_SPECIES=211 -- SPECIES_QWILFISH (pinned World include/constants/species.h)
local BATTLE_TYPE_TRAINER=(1<<3)
local MAX_BATTLES=110
local MAX_STEPS=6500
assert(config.species=="SPECIES_QWILFISH" and config.mapName=="MAP_ROUTE32"
       and config.slot==5 and config.group>=0 and config.map>=0)
assert(config.monStride>=40 and config.monStride<512 and config.monStride%2==0)
assert(#callbacks>=2 and #callbacks<=8)

local function tap(k) F.press(k,2); F.idle(14) end
local function digits(v) return (v//100)%10,(v//10)%10,v%10 end
local function actionLive()
  local fn=F.r32(S.gBattlerControllerFuncs)
  for _,addr in ipairs(callbacks) do
    if (fn&~1)==(addr&~1) then return true end
  end
  return false
end
local function waitAction(maxFrames)
  for i=1,maxFrames do
    if actionLive() then return true end
    joypad.set(i%45==1 and {A=true} or {})
    emu.frameadvance()
    if i%600==0 and F.reportCrash("battle_action_wait") then return false end
  end
  return false
end
local function flee()
  if not waitAction(13000) then return false end
  F.idle(22)
  tap("Down"); tap("Right")
  if F.r8(S.gActionSelectionCursor)~=3 then return false end
  tap("A")
  for i=1,19000 do
    if F.ow() then return true end
    if actionLive() then
      -- Enemy may prevent the first escape. Attempt normal RUN again.
      tap("Down");tap("Right");tap("A")
    else
      joypad.set(i%35==1 and {A=true} or {})
      emu.frameadvance()
    end
    if i%800==0 and F.reportCrash("flee") then return false end
  end
  return F.ow()
end
local function tileData()
  local base=S.gBackupMapLayout
  local stride=F.r32(base+S.BackupMapLayout.width)
  local height=F.r32(base+S.BackupMapLayout.height)
  local ptr=F.r32(base+S.BackupMapLayout.map)
  local w,h=stride-15,height-14
  if w<1 or h<1 or w>500 or h>500 or w*h>35000 or
     ptr<0x02000000 or ptr>=0x02040000 then return nil end
  local layout=F.r32(S.gMapHeader+S.MapHeader.mapLayout)
  if layout<0x08000000 or layout>=0x0A000000 then return nil end
  local p1=F.r32(layout+S.MapLayout.primaryTileset)
  local p2=F.r32(layout+S.MapLayout.secondaryTileset)
  local split=S.Metatiles.inPrimary
  if (F.r8(p1+S.Tileset.flags1)&S.Tileset.hasFrlgAttributesBit)~=0 or
      F.r8(layout+S.MapLayout.isFrlg)~=0 or
      F.r8(layout+S.MapLayout.isJohto)~=0 then split=S.Metatiles.inPrimaryFrlg end
  local function cell(x,y)
    if x<0 or y<0 or x>=w or y>=h then return false,false end
    local v=F.r16(ptr+(x+7+(y+7)*stride)*2)
    local id=v&S.Metatiles.idMask
    local ts,ix=p1,id
    if id>=split then ts,ix=p2,id-split end
    local attrs=F.r32(ts+S.Tileset.metatileAttributes)
    local mb
    if (F.r8(ts+S.Tileset.flags1)&S.Tileset.hasFrlgAttributesBit)~=0 then
      mb=F.r32(attrs+ix*4)&S.Metatiles.behaviorMaskFrlg
    else
      mb=F.r16(attrs+ix*2)&S.Metatiles.behaviorMask
    end
    return (v&0x0C00)==0,mb==2
  end
  return w,h,cell
end
local DIRS={
  {"Up",0,-1},{"Down",0,1},{"Left",-1,0},{"Right",1,0}
}
local function bfsToGrass(w,h,cell,blocked)
  local sx,sy=F.pos()
  if sx<0 or sx>=w or sy<0 or sy>=h then return nil,"warp outside map" end
  local function key(x,y) return y*w+x end
  local start=key(sx,sy)
  local seen={[start]=true}
  local queue={{sx,sy,start}}
  local parent={}
  local head=1
  local goal
  while head<=#queue do
    local n=queue[head];head=head+1
    local _,isGrass=cell(n[1],n[2])
    if isGrass then goal=n[3];break end
    for _,dir in ipairs(DIRS) do
      local x,y=n[1]+dir[2],n[2]+dir[3]
      if x>=0 and y>=0 and x<w and y<h then
        local id=key(x,y)
        local pass=cell(x,y)
        if pass and not seen[id] and not blocked[id] then
          seen[id]=true;parent[id]={n[3],dir[1]}
          queue[#queue+1]={x,y,id}
        end
      end
    end
  end
  if not goal then return nil,"no traversable path to any grass in raw map grid" end
  local path={}
  while goal~=start do
    local p=parent[goal]
    if not p then return nil,"broken path parent" end
    table.insert(path,1,p[2])
    goal=p[1]
  end
  return path
end
local function firstGrassNeighbor(x,y,cell,blocked,w)
  for _,d in ipairs(DIRS) do
    local nx,ny=x+d[2],y+d[3]
    local pass,grass=cell(nx,ny)
    if pass and grass and not blocked[ny*w+nx] then return d[1],nx,ny end
  end
  return nil
end
local function visitBattle()
  local ok=waitAction(14000)
  if not ok then return nil,false end
  F.idle(24)
  local count=F.battlers()
  local flags=F.battleFlags()
  if count<2 or (flags&BATTLE_TYPE_TRAINER)~=0 then return nil,false end
  local species=F.r16(S.gBattleMons+config.monStride)
  return species,true
end

F.run(function()
  client.speedmode(800)
  local boot=F.boot(100)
  F.check("real GBA experimental cartridge boots",boot and F.ow() and F.grp()==100)
  if not boot then F.finish();return end
  F.dbg();F.sel(2);F.sel(9);F.idle(130);F.bOut(8);F.idle(65)
  F.check("legitimate in-game debug party exists",F.r8(S.gPartiesCount)==1)
  local gh,gt,go=digits(config.group)
  local mh,mt,mo=digits(config.map)
  local warped=F.warpTo(gh,gt,go,mh,mt,mo,0,0,0,config.group,config.map,"route32")
  F.check("real warp reached Route32",warped and F.grp()==config.group and F.mapn()==config.map)
  if not warped then F.finish();return end
  local w,h,cell=tileData()
  F.check("real Route32 has bounded map grid and tilesets",w~=nil)
  if not w then F.finish();return end
  F.L(string.format("real Route32 map=%dx%d, checking raw collision and grass tiles",w,h))
  local blocked,walked,battles,match=false,0,0,false
  blocked={}
  local visitedGrass=false
  local lastReason="not started"

  for rounds=1,MAX_STEPS do
    if F.reportCrash("route32_cycle") then lastReason="GBA fatal screen";break end
    if F.grp()~=config.group or F.mapn()~=config.map then
      lastReason="changed map unexpectedly";break
    end
    if not F.ow() then
      battles=battles+1
      local species,isWild=visitBattle()
      if not isWild then lastReason="failed to inspect natural wild battle";break end
      F.L(string.format("NATURAL WILD BATTLE #%d: species=%d target=%d steps=%d",
        battles,species,TARGET_SPECIES,walked))
      if species==TARGET_SPECIES then match=true;F.shot("real_qwilfish_encounter");break end
      if not flee() then lastReason="real RUN could not restore field";break end
      if battles>=MAX_BATTLES then lastReason="encounter attempt budget reached";break end
    else
      local x,y=F.pos()
      local _,onGrass=cell(x,y)
      if onGrass then visitedGrass=true end
      local direction,tx,ty
      if not onGrass then
        local path,reason=bfsToGrass(w,h,cell,blocked)
        if not path then lastReason=reason;break end
        direction=path[1]
        if not direction then lastReason="path says grass but metatile disagrees";break end
      else
        direction,tx,ty=firstGrassNeighbor(x,y,cell,blocked,w)
        if not direction then
          -- A single grass tile can still trigger an encounter by walking
          -- out and returning. Never call StartWildEncounter or edit RNG.
          for _,d in ipairs(DIRS) do
            local p=cell(x+d[2],y+d[3])
            if p and not blocked[(y+d[3])*w+x+d[2]] then
              direction=d[1];break
            end
          end
        end
        if not direction then lastReason="grass patch has no walkable neighbor";break end
      end
      local dx,dy=0,0
      for _,d in ipairs(DIRS) do if d[1]==direction then dx,dy=d[2],d[3] end end
      local nextKey=(y+dy)*w+x+dx
      local moved=F.step(direction)
      F.idle(25)
      walked=walked+1
      local xx,yy=F.pos()
      if xx>=0 and yy>=0 and xx<w and yy<h then
        local _,nowGrass=cell(xx,yy)
        if nowGrass then visitedGrass=true end
      end
      if not F.ow() then
        -- An encounter might interrupt movement. Inspect it next iteration.
      elseif not moved then
        blocked[nextKey]=true
        if walked>200 and not visitedGrass then
          lastReason="couldn't reach grass after many real steps";break
        end
      end
    end
    if battles>=MAX_BATTLES or walked>=MAX_STEPS then break end
  end
  F.check("controller physically reached tall grass on candidate Route32",visitedGrass,
    "walked="..walked.." encounters="..battles)
  F.check("natural battle was encountered without forcing RNG or battle RAM",battles>0,
    "battles="..battles)
  F.check("target new-table Qwilfish (species 211) appeared in actual battle",match,
    "observed encounters="..battles.." steps="..walked.." last="..lastReason)
  F.check("no engine fatal screen while testing this route",not F.reportCrash("route32_final"))
  if match then F.L("TRUE runtime evidence: wild Route32 species 211 (Qwilfish) on experimental cartridge") end
  F.finish()
end)
