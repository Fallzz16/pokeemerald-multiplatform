-- Fresh GBA PT-BR acceptance: original Silph Co. 7F Lapras gift.
-- DO NOT count a debug warp as normal campaign/story reachability.
-- No SaveBlock/party/flag/RNG writes, no scripted Pokemon injection.
local here=(debug.getinfo(1,"S").source:sub(2)):match("^(.*[/\\])") or ""
package.path=here.."?.lua;"..package.path
local S=require("symbols")
local F=require("lib").new(S,"GrandWorldSilphLaprasGift")
local GROUP,MAP=35,53 -- exact pinned World map_groups.json
local FLAG_GOT_LAPRAS=0xA40+0x246 -- source expression, checked by CI
local SPECIES_LAPRAS=131
local function receivedFlag()
  local base=F.sb1()+S.SaveBlock1.flags
  return (F.r8(base+(FLAG_GOT_LAPRAS>>3))&(1<<(FLAG_GOT_LAPRAS&7)))~=0
end
local function giftNpc()
  for _,e in ipairs(F.objdump()) do
    if e.x==0 and e.y==7 then return e end
  end
end
local SUB0={0,0,0,0,0,0,1,1,2,3,2,3,1,1,2,3,2,3,1,1,2,3,2,3}
local function firstPartySpecies()
  local mon=S.gParties
  local p=F.r32(mon)
  local ot=F.r32(mon+4)
  local encrypted=F.r32(mon+32+SUB0[(p%24)+1]*12)
  return (encrypted~p~ot)&0x7FF
end
local GOAL_X,GOAL_Y=1,7 -- stand next to original (0,7) worker, face left
local DIRS={{"Up",0,-1},{"Left",-1,0},{"Right",1,0},{"Down",0,1}}
local function liveMap()
  local b=S.gBackupMapLayout
  local width=F.r32(b+S.BackupMapLayout.width)
  local height=F.r32(b+S.BackupMapLayout.height)
  local ptr=F.r32(b+S.BackupMapLayout.map)
  local w,h=width-15,height-14
  if w<1 or h<1 or w>500 or h>500 or w*h>35000
     or ptr<0x02000000 or ptr>=0x02040000 then return nil end
  local function pass(x,y)
    if x<0 or y<0 or x>=w or y>=h then return false end
    local tile=F.r16(ptr+2*((x+7)+(y+7)*width))
    return (tile&0x0C00)==0
  end
  return w,h,pass
end
local function bfs(w,h,pass,blocked)
  local x0,y0=F.pos()
  if x0<0 or y0<0 or x0>=w or y0>=h then return nil end
  local key=function(x,y) return y*w+x end
  local start=key(x0,y0)
  local q,seen,prev,head={{x0,y0,start}},{[start]=true},{},1
  local finish
  while q[head] do
    local v=q[head];head=head+1
    if v[1]==GOAL_X and v[2]==GOAL_Y then finish=v[3];break end
    for _,d in ipairs(DIRS) do
      local x,y=v[1]+d[2],v[2]+d[3]
      local k=key(x,y)
      if not seen[k] and not blocked[k] and pass(x,y) then
        seen[k]=true
        prev[k]={v[3],d[1]}
        q[#q+1]={x,y,k}
      end
    end
  end
  if not finish then return nil end
  local out={}
  while finish~=start do
    local p=prev[finish]
    if not p then return nil end
    table.insert(out,1,p[2])
    finish=p[1]
  end
  return out
end
local function walkToGift()
  local w,h,pass=liveMap()
  if not w then return false end
  local blocked={}
  for attempt=1,180 do
    local route=bfs(w,h,pass,blocked)
    if not route then return false end
    if #route==0 then return true end
    local dir=route[1]
    local x0,y0=F.pos()
    F.step(dir);F.idle(13)
    local x1,y1=F.pos()
    if not F.ow() then return false end
    if x1==x0 and y1==y0 then
      for _,d in ipairs(DIRS) do
        if d[1]==dir then blocked[(y0+d[3])*w+x0+d[2]]=true end
      end
      F.L(string.format("  blocked at (%d,%d) %s",x0,y0,dir))
    end
  end
  return false
end
F.run(function()
  client.speedmode(800)
  local boot=F.boot(100)
  F.check("fresh pinned PT-BR ARM GBA boots into RegionHub",boot and F.ow() and F.grp()==100)
  if not boot then F.finish();return end
  F.check("fresh game begins with no party Pokemon",F.r8(S.gPartiesCount)==0)
  -- Enter via an ORIGINAL map warp (from Silph Co. 11F); only test setup
  -- uses the game's Debug warp, then all movement/talking is real joypad.
  local warp=F.warpTo(0,3,5,0,5,3,0,0,1,GROUP,MAP,"silph_gift")
  F.check("warp entered real Silph Co. 7F map",warp and F.ow() and F.grp()==GROUP and F.mapn()==MAP)
  if not warp then F.finish();return end
  F.check("original Lapras gift worker spawned at (0,7)",giftNpc()~=nil)
  F.check("gift flag initially unset",not receivedFlag())
  if not giftNpc() or receivedFlag() then F.finish();return end
  local reached=walkToGift()
  local x,y=F.pos()
  F.check("real input walked to worker adjacent tile",reached and x==GOAL_X and y==GOAL_Y)
  if not reached then F.shot("gift_path_blocked");F.finish();return end
  F.face("Left")
  F.press("A",2);F.idle(65)
  F.shot("lapras_worker_first_contact")
  local received=false
  for frame=1,5500 do
    if F.r8(S.gPartiesCount)==1 and firstPartySpecies()==SPECIES_LAPRAS then
      received=true;break
    end
    joypad.set(frame%38==1 and {A=true} or {})
    emu.frameadvance()
    if frame%500==0 and F.reportCrash("gift_advance") then break end
  end
  F.check("actual NPC givemon added Lapras to player's party",received)
  F.check("first encrypted party Pokemon is species 131 Lapras",
          F.r8(S.gPartiesCount)>0 and firstPartySpecies()==SPECIES_LAPRAS)
  F.shot("lapras_party_receipt")
  -- B safely declines nickname prompts; never edit any save/flag manually.
  for frame=1,4000 do
    if receivedFlag() then break end
    joypad.set(frame%38==1 and {B=true} or {})
    emu.frameadvance()
    if frame%500==0 and F.reportCrash("gift_nickname") then break end
  end
  F.check("original script set persistent Lapras gift flag",receivedFlag())
  F.check("gift preserved one party member",F.r8(S.gPartiesCount)==1)
  F.check("returned to Silph Co. 7F overworld",F.ow() and F.grp()==GROUP and F.mapn()==MAP)
  F.check("gift caused no fatal in-game screen",not F.reportCrash("gift_finish"))
  F.shot("lapras_final")
  F.finish()
end)
