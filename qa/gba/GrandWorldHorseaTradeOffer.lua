-- Step-3 acceptance: make the ORIGINAL Horsea-for-Bagon trade NPC
-- accessible with real joypad on a fresh, disposable PT-BR GBA ROM.
-- This checks first-contact offer and safe decline, NOT trade completion.
-- No save flags, NPC position, scripts, or Pokemon are written to RAM.
local here=(debug.getinfo(1,"S").source:sub(2)):match("^(.*[/\\])") or ""
package.path=here.."?.lua;"..package.path
local S=require("symbols")
local F=require("lib").new(S,"GrandWorldHorseaTradeOffer")
local OFFER_FLAG=0x9A
local GROUP,MAP=7,4   -- derived from pinned map_groups.json in the CI preflight.

local function tradeCompleted()
  local id=OFFER_FLAG
  local base=F.sb1()+S.SaveBlock1.flags
  return (F.r8(base+(id>>3))&(1<<(id&7)))~=0
end

local function trader()
  for _,v in ipairs(F.objdump()) do
    if v.x==4 and v.y==2 then return v end
  end
  return nil
end

-- Compute a real field route around furniture and object collisions, instead
-- of the lib.leg axis-first helper, which correctly stopped at (4,6).
local GOALS={
  {4,3,"Up"}, {5,2,"Left"}, {3,2,"Right"}, {4,1,"Down"},
}
local DIRS={
  {"Up",0,-1},{"Left",-1,0},{"Right",1,0},{"Down",0,1},
}
local function grid()
  local b=S.gBackupMapLayout
  local width=F.r32(b+S.BackupMapLayout.width)
  local height=F.r32(b+S.BackupMapLayout.height)
  local ptr=F.r32(b+S.BackupMapLayout.map)
  local w,h=width-15,height-14
  if w<1 or h<1 or w>500 or h>500 or w*h>35000
    or ptr<0x02000000 or ptr>=0x02040000 then return nil end
  local function passable(x,y)
    if x<0 or y<0 or x>=w or y>=h then return false end
    local block=F.r16(ptr+2*((x+7)+(y+7)*width))
    return (block&0x0C00)==0
  end
  return w,h,passable
end

local function npcPath(w,h,passable,blocked)
  local sx,sy=F.pos()
  if sx<0 or sy<0 or sx>=w or sy>=h then return nil end
  local function key(x,y) return y*w+x end
  local start=key(sx,sy)
  local q,seen,parent,head={{sx,sy,start}},{[start]=true},{},1
  local finish,goal
  while q[head] do
    local v=q[head];head=head+1
    for _,t in ipairs(GOALS) do
      if v[1]==t[1] and v[2]==t[2] then finish=v[3];goal=t;break end
    end
    if finish then break end
    for _,d in ipairs(DIRS) do
      local x,y=v[1]+d[2],v[2]+d[3]
      local k=key(x,y)
      if not seen[k] and not blocked[k] and passable(x,y) then
        seen[k]=true;parent[k]={v[3],d[1]}
        q[#q+1]={x,y,k}
      end
    end
  end
  if not finish then return nil end
  local steps={}
  while finish~=start do
    local p=parent[finish]
    if not p then return nil end
    table.insert(steps,1,p[2])
    finish=p[1]
  end
  return steps,goal
end

local function reachTrader()
  local w,h,passable=grid()
  if not w then return false,nil,nil,nil end
  local blocked,lastDir={},nil
  local reverse={Up="Down",Down="Up",Left="Right",Right="Left"}
  for attempt=1,85 do
    local path,goal=npcPath(w,h,passable,blocked)
    if not path then
      F.L("  npc-path exhausted collision graph after "..attempt.." attempts")
      return false,nil,nil,nil
    end
    if #path==0 then
      return true,goal[3],lastDir and reverse[lastDir] or nil,goal
    end
    local dir=path[1]
    local x0,y0=F.pos()
    F.step(dir);F.idle(15)
    local x1,y1=F.pos()
    if not F.ow() then return false,nil,nil,nil end
    if x1==x0 and y1==y0 then
      for _,d in ipairs(DIRS) do
        if d[1]==dir then
          blocked[(y0+d[3])*w+x0+d[2]]=true
          F.L(string.format("  blocked NPC/furniture at (%d,%d) -> %s",x0,y0,dir))
        end
      end
    else
      lastDir=dir
    end
  end
  return false,nil,nil,nil
end

F.run(function()
  client.speedmode(800)
  local started=F.boot(100)
  F.check("fresh PT-BR GBA booted in the RegionHub",started and F.ow() and F.grp()==100)
  if not started then F.finish();return end

  F.dbg();F.sel(2);F.sel(9);F.idle(125);F.bOut(8);F.idle(75)
  F.check("game debug menu prepared a legal party member",F.r8(S.gPartiesCount)==1)

  local warped=F.warpTo(0,0,7,0,0,4,0,0,0,GROUP,MAP,"pacifidlog_horsea")
  F.check("real GBA warp reached Pacifidlog trade house",
    warped and F.ow() and F.grp()==GROUP and F.mapn()==MAP)
  if not warped then F.finish();return end

  F.check("the original trade completion flag starts unset",not tradeCompleted())
  local npc=trader()
  F.check("trade NPC is spawned at real map object coordinates",
    npc~=nil,"npc="..tostring(npc and npc.i or "missing"))
  local walk,facing,back,goal=reachTrader()
  local x,y=F.pos()
  F.check("real joypad navigation reached a tile adjacent to the Horsea trader",
    walk and goal~=nil and x==goal[1] and y==goal[2],
    "position="..x..","..y)
  if not walk then F.shot("horse_trade_path_blocked");F.finish();return end

  F.face(facing)
  F.press("A",2);F.idle(60)
  F.shot("horse_trader_first_offer")
  local xx,yy=F.pos()
  local block=(back~=nil) and not F.step(back)
  local qx,qy=F.pos()
  F.check("dialogue with actual trader locks movement along known open path",
    block and xx==qx and yy==qy,
    string.format("before=(%d,%d) after=(%d,%d)",xx,yy,qx,qy))
  F.check("talking without Bagon never marks Horsea trade completed",
    not tradeCompleted())

  -- B cancels/dismisses script dialogue; never select a positive trade.
  F.bOut(8);F.idle(90)
  F.check("declining a trade does not grant extra party Pokémon",
    F.r8(S.gPartiesCount)==1)
  F.check("trade completion flag remains unset after safe cancellation",
    not tradeCompleted())
  F.shot("horse_trader_declined")
  F.check("no fatal GBA screen during first-contact trade offer",
    not F.reportCrash("horse_trade_offer"))
  F.finish()
end)
