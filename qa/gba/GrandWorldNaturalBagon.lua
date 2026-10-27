-- M9: original land-table Bagon in Meteor Falls cave; no candidate table edits.
-- Real ARM GBA emulator movement, authentic RNG, actual Master Ball via Bag.
-- Debug party/item/warp setup only; NO battle/RNG/species/save injection.
local here=(debug.getinfo(1,"S").source:sub(2)):match("^(.*[/\\])") or ""
package.path=here.."?.lua;"..package.path
local S=require("symbols")
local F=require("lib").new(S,"GrandWorldNaturalBagon")
local config=dofile(here.."bagon_cave_target.lua")
local callbacks=dofile(here.."battle_action_callbacks.lua")
local BAGON,MASTER_BALL=371,4
local GROUP,MAP=24,3
local MAX_BATTLES,MAX_STEPS=80,4200
assert(config.group==GROUP and config.map==MAP and config.species=="SPECIES_BAGON")
assert(config.monStride>=40 and config.monStride<512 and config.monStride%2==0)
assert(#callbacks>=2 and #callbacks<=8)
local function tap(k) F.press(k,2); F.idle(16) end
local function activeBattleMenu()
  local fn=F.r32(S.gBattlerControllerFuncs)&~1
  for _,v in ipairs(callbacks) do if fn==(v&~1) then return true end end
  return false
end
local function untilAction(limit)
  for i=1,limit do
    if activeBattleMenu() then return true end
    joypad.set(i%45==1 and {A=true} or {})
    emu.frameadvance()
    if i%600==0 and F.reportCrash("bagon_wait_action") then return false end
  end
  return false
end
local function escapeWild()
  if not untilAction(13000) then return false end
  F.idle(22);tap("Down");tap("Right")
  if F.r8(S.gActionSelectionCursor)~=3 then return false end
  tap("A")
  for i=1,17000 do
    if F.ow() then F.idle(90);return true end
    if activeBattleMenu() then tap("Down");tap("Right");tap("A")
    else joypad.set(i%35==1 and {A=true} or {});emu.frameadvance() end
    if i%900==0 and F.reportCrash("bagon_run") then return false end
  end
  return false
end
local function giveBall()
  F.dbg();F.sel(3);F.sel(0)
  for _=1,3 do tap("Up") end -- original debug item spinner starts at ID1
  tap("A");tap("A")
  F.idle(130);F.bOut(8);F.idle(55)
  local balls=F.r32(S.gBagPockets+S.BagPocket.stride+S.BagPocket.itemsPtr)
  if balls<0x02000000 or balls>=0x02040000 then return false end
  for i=0,F.pocketCap(1)-1 do
    if F.r16(balls+4*i)==MASTER_BALL then return true end
  end
  return false
end
local function liveGrid()
  local b=S.gBackupMapLayout
  local stride=F.r32(b+S.BackupMapLayout.width)
  local height=F.r32(b+S.BackupMapLayout.height)
  local map=F.r32(b+S.BackupMapLayout.map)
  local w,h=stride-15,height-14
  if w<1 or h<1 or w>500 or h>500 or w*h>35000
     or map<0x02000000 or map>=0x02040000 then return nil end
  local function pass(x,y)
    if x<0 or y<0 or x>=w or y>=h then return false end
    return (F.r16(map+2*((x+7)+(y+7)*stride))&0x0C00)==0
  end
  return w,h,pass
end
local DIRS={{"Up",0,-1},{"Left",-1,0},{"Right",1,0},{"Down",0,1}}
local function farthestPath(w,h,pass,blocked)
  local sx,sy=F.pos()
  if sx<0 or sy<0 or sx>=w or sy>=h then return nil end
  local key=function(x,y)return y*w+x end
  local start=key(sx,sy)
  local q,seen,prev,head={{sx,sy,start,0}},{[start]=true},{},1
  local goal,dist=start,0
  while q[head] do
    local cur=q[head];head=head+1
    if cur[4]>dist then dist=cur[4];goal=cur[3] end
    for _,d in ipairs(DIRS) do
      local x,y=cur[1]+d[2],cur[2]+d[3]
      local k=key(x,y)
      if not seen[k] and not blocked[k] and pass(x,y) then
        seen[k]=true;prev[k]={cur[3],d[1]}
        q[#q+1]={x,y,k,cur[4]+1}
      end
    end
  end
  if dist==0 then return nil end
  local path={}
  while goal~=start do
    local p=prev[goal]
    if not p then return nil end
    table.insert(path,1,p[2]);goal=p[1]
  end
  return path,dist
end
local function captureBagon()
  if not activeBattleMenu() and not untilAction(3000) then return false,false end
  F.idle(22)
  tap("Right") -- BAG
  if F.r8(S.gActionSelectionCursor)~=1 then return false,false end
  tap("A");F.idle(170)
  tap("Right");F.idle(125) -- Balls pocket (real Bag)
  F.shot("real_bag_balls")
  tap("A");F.idle(70)
  tap("A");F.idle(250)
  local selected=F.r16(S.gSpecialVar_ItemId)==MASTER_BALL
  F.L("  actual BAG item ID="..F.r16(S.gSpecialVar_ItemId))
  for i=1,26000 do
    if F.ow() then return selected,true end
    joypad.set(i%25==1 and {A=true} or {})
    emu.frameadvance()
    if i%800==0 and F.reportCrash("bagon_capture") then break end
  end
  return selected,false
end
F.run(function()
  client.speedmode(800)
  local boot=F.boot(100)
  F.check("original M8 PT-BR GBA boots into RegionHub",boot and F.ow() and F.grp()==100)
  if not boot then F.finish();return end
  F.dbg();F.sel(2);F.sel(9);F.idle(125);F.bOut(8);F.idle(85)
  F.check("real debug setup provides one legal battle party mon",F.r8(S.gPartiesCount)==1)
  local hasBall=giveBall()
  F.check("Master Ball provided through native in-game debug Bag UI",hasBall)
  if not hasBall then F.finish();return end
  local warp=F.warpTo(0,2,4,0,0,3,0,0,0,GROUP,MAP,"meteor_falls")
  F.check("original Meteor Falls B1F 2R map entered by real warp",warp and F.grp()==GROUP and F.mapn()==MAP)
  if not warp then F.finish();return end
  local w,h,pass=liveGrid()
  F.check("actual underground collision grid is valid",w~=nil)
  if not w then F.finish();return end
  local walked,movedCount,battles,seenBagon,selectedBall,captured=0,0,0,false,false,false
  -- A joystick direction attempt is NOT proof the avatar changed tiles.
  -- Keep independent movement and distinct-coordinate observations so
  -- a blocked controller fixture cannot masquerade as cave exploration.
  local uniquePositions={[select(2,F.pos())*w+select(1,F.pos())]=true}
  local distinctPositions=1
  local blocked,lastPath,pathi={},{},1
  for iter=1,MAX_STEPS do
    if F.reportCrash("meteor_exploration") then break end
    if F.grp()~=GROUP or F.mapn()~=MAP then F.L("  left Meteor Falls unexpectedly");break end
    if not F.ow() then
      battles=battles+1
      if not untilAction(14000) then F.L("  action callback not ready");break end
      F.idle(24)
      if F.battlers()<2 or (F.battleFlags()&(1<<3))~=0 then F.L("  not a wild battle");break end
      local species=F.r16(S.gBattleMons+config.monStride)
      F.L(string.format("NATURAL METEOR WILD #%d: opponent=%d, steps=%d",battles,species,walked))
      if species==BAGON then
        seenBagon=true;F.shot("original_wild_bagon_spotted")
        selectedBall,captured=captureBagon()
        break
      end
      if not escapeWild() then F.L("  normal RUN failed");break end
      blocked={};lastPath={};pathi=1
      if battles>=MAX_BATTLES then break end
    else
      if pathi>#lastPath then
        local newPath,dist=farthestPath(w,h,pass,blocked)
        if not newPath then F.L("  no traversable cave path");break end
        lastPath=newPath;pathi=1
      end
      local dir=lastPath[pathi];pathi=pathi+1
      local x0,y0=F.pos()
      local moved=F.step(dir);F.idle(23)
      walked=walked+1
      local nowX,nowY=F.pos()
      if moved and (nowX~=x0 or nowY~=y0) then
        movedCount=movedCount+1
        local key=nowY*w+nowX
        if not uniquePositions[key] then
          uniquePositions[key]=true
          distinctPositions=distinctPositions+1
        end
      end
      if not F.ow() then -- authentic encounter interrupted walking
      elseif not moved then
        local dx,dy=0,0
        for _,d in ipairs(DIRS) do if d[1]==dir then dx,dy=d[2],d[3] end end
        blocked[(y0+dy)*w+x0+dx]=true;lastPath={};pathi=1
      end
    end
  end
  F.L(string.format("CAVE MOVEMENT: attempted=%d verified_moved=%d unique_tiles=%d, wild_battles=%d",
    walked,movedCount,distinctPositions,battles))
  F.check("player physically walked traversable original cave floor",movedCount>=2 and distinctPositions>=2,
    string.format("attempts=%d actual_moves=%d unique_tiles=%d",
      walked,movedCount,distinctPositions))
  F.check("real cave movement triggered at least one natural wild battle",battles>0,
    "battles="..battles)
  F.check("unmodified original land encounter naturally produced Bagon 371",seenBagon,
    "battles="..battles)
  F.check("battle Bag really selected Master Ball item ID 4",selectedBall)
  F.check("real ball animation/catch returned control to game field",captured)
  F.check("captured Bagon added to player's actual party",F.r8(S.gPartiesCount)==2,
    "party="..F.r8(S.gPartiesCount))
  F.check("player returned to original Meteor Falls map",F.ow() and F.grp()==GROUP and F.mapn()==MAP)
  F.check("no fatal GBA screen occurred during Bagon capture",not F.reportCrash("bagon_final"))
  if seenBagon then F.L("TRUE naturally met original Bagon 371 at Meteor Falls; no RNG forcing") end
  F.shot("natural_bagon_capture_end")
  F.finish()
end)
