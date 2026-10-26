-- Step-3 acceptance gate: encounter SPECIES_QWILFISH from a newly proposed
-- grass table on Route32 in the real M8+PT-BR ARM GBA cartridge.
-- No RNG patch, no battle-state write, no artificial wild-mon creation.
-- The game must randomly choose the candidate species from live walking.
-- This proves a narrow implementation path; does NOT approve fish on land.
local here=(debug.getinfo(1,"S").source:sub(2)):match("^(.*[/\\])") or ""
package.path=here.."?.lua;"..package.path
local S=require("symbols")
local F=require("lib").new(S,"GrandWorldCandidateQwilfish")
local battle=dofile(here.."candidate_battle_rom_symbols.lua")
assert(battle.expected_species>0 and battle.battle_mon_stride>=40)
assert(#battle.action_callbacks>=2)
local GROUP,MAP=battle.group,battle.map
local WANTED=battle.expected_species
local LIMIT=75
local DIRS={{0,-1,"Up"},{1,0,"Right"},{0,1,"Down"},{-1,0,"Left"}}

local function pressed(k)
  F.press(k,2);F.idle(15)
end

local function field()
  local b=S.gBackupMapLayout
  local width=F.r32(b+S.BackupMapLayout.width)
  local height=F.r32(b+S.BackupMapLayout.height)
  local base=F.r32(b+S.BackupMapLayout.map)
  local mw,mh=width-15,height-14
  assert(mw>0 and mh>0 and mw<500 and mh<500 and mw*mh<35000)
  assert(base>=0x02000000 and base<0x02040000)
  return {w=width, h=height, mw=mw, mh=mh, base=base}
end

local function block(ctx,x,y)
  if x<0 or y<0 or x>=ctx.mw or y>=ctx.mh then return nil end
  return F.r16(ctx.base+2*((x+7)+(y+7)*ctx.w))
end

local function walkable(ctx,x,y)
  local v=block(ctx,x,y)
  return v~=nil and ((v>>10)&3)==0
end

local function behavior(ctx,x,y)
  local v=block(ctx,x,y)
  if not v then return -1 end
  local id=v&S.Metatiles.idMask
  local layout=F.r32(S.gMapHeader+S.MapHeader.mapLayout)
  local p1=F.r32(layout+S.MapLayout.primaryTileset)
  local p2=F.r32(layout+S.MapLayout.secondaryTileset)
  local split=S.Metatiles.inPrimary
  if (F.r8(p1+S.Tileset.flags1)&S.Tileset.hasFrlgAttributesBit)~=0
     or F.r8(layout+S.MapLayout.isFrlg)~=0
     or F.r8(layout+S.MapLayout.isJohto)~=0 then
    split=S.Metatiles.inPrimaryFrlg
  end
  local ts,localid=p1,id
  if id>=split then ts,localid=p2,id-split end
  local attrs=F.r32(ts+S.Tileset.metatileAttributes)
  if (F.r8(ts+S.Tileset.flags1)&S.Tileset.hasFrlgAttributesBit)~=0 then
    return F.r32(attrs+localid*4)&S.Metatiles.behaviorMaskFrlg
  end
  return F.r16(attrs+localid*2)&S.Metatiles.behaviorMask
end

local function nearestGrass(ctx,sx,sy)
  if sx<0 or sy<0 or sx>=ctx.mw or sy>=ctx.mh then return nil end
  -- BFS over ROM-loaded field collision flags. Navigation still has to
  -- succeed with actual controller input before counting as accessible.
  local q,seen,parents,head={{sx,sy}},{[sx..":"..sy]=true},{},1
  while q[head] and head<=12000 do
    local p=q[head];head=head+1
    if behavior(ctx,p[1],p[2])==2 and walkable(ctx,p[1],p[2]) then
      local result,k={},p[1]..":"..p[2]
      while parents[k] do
        local n=parents[k]
        table.insert(result,1,n[2])
        k=n[1]
      end
      return result,p[1],p[2]
    end
    for _,d in ipairs(DIRS) do
      local x,y=p[1]+d[1],p[2]+d[2]
      local key=x..":"..y
      if not seen[key] and walkable(ctx,x,y) then
        seen[key]=true
        parents[key]={p[1]..":"..p[2],d[3]}
        q[#q+1]={x,y}
      end
    end
  end
  return nil
end

local function actionLive()
  local addr=F.r32(S.gBattlerControllerFuncs)&~1
  for _,a in ipairs(battle.action_callbacks) do
    if addr==(a&~1) then return true end
  end
  return false
end

local function awaitActions(limit)
  for n=1,limit do
    if actionLive() then return true end
    joypad.set(n%48==1 and {A=true} or {})
    emu.frameadvance()
    if n%500==0 and F.reportCrash("action_wait") then return false end
  end
  return actionLive()
end

local function flee()
  for n=1,5 do
    if not awaitActions(13000) then return false end
    local cursor=F.r8(S.gActionSelectionCursor)
    if cursor~=0 then
      -- Only the FIGHT cursor is currently understood; refuse to simulate.
      F.L("  action menu cursor not reset to FIGHT: "..cursor)
      return false
    end
    pressed("Down");pressed("Right")
    if F.r8(S.gActionSelectionCursor)~=3 then return false end
    pressed("A")
    for t=1,15000 do
      if F.ow() then return true end
      joypad.set(t%30==1 and {A=true} or {})
      emu.frameadvance()
      if t%300==0 and F.reportCrash("run_attempt") then return false end
      if t>90 and actionLive() then break end
    end
  end
  return F.ow()
end

F.run(function()
  client.speedmode(800)
  local ok=F.boot(100)
  F.check("experimental GBA booted with active overworld",ok and F.ow() and F.grp()==100)
  if not ok then F.finish();return end

  -- Legal debug party is created through the real in-game menu, not memory.
  F.dbg();F.sel(2);F.sel(9);F.idle(125);F.bOut(8);F.idle(75)
  F.check("live debug UI prepared legal battling Pokémon",F.r8(S.gPartiesCount)==1)
  local gh,gt,go=(GROUP//100)%10,(GROUP//10)%10,GROUP%10
  local mh,mt,mo=(MAP//100)%10,(MAP//10)%10,MAP%10
  local warped=F.warpTo(gh,gt,go,mh,mt,mo,0,0,0,GROUP,MAP,"candidate_Qwilfish")
  F.check("in-game warp reached the actual proposed Route32 map",
    warped and F.ow() and F.grp()==GROUP and F.mapn()==MAP)
  if not warped then F.finish();return end

  local ctx=field()
  local ox,oy=F.pos()
  local route,tx,ty=nearestGrass(ctx,ox,oy)
  F.check("actual map collision graph contains a route to tall grass",
    route~=nil,"warp=("..ox..","..oy..")")
  if not route then F.finish();return end
  F.L(string.format("  grass plan: from (%d,%d) to (%d,%d) in %d tiles",ox,oy,tx,ty,#route))
  local landSteps,battleCount,found=0,0,false
  local visitedReachable=false
  local previous=nil
  local pathCursor=1
  local blocked=0
  local limitTicks=0
  while battleCount<LIMIT and limitTicks<4500 do
    limitTicks=limitTicks+1
    if F.ow() then
      local x,y=F.pos()
      local current=behavior(ctx,x,y)
      if current==2 then visitedReachable=true end
      local dir
      if pathCursor<=#route then
        dir=route[pathCursor];pathCursor=pathCursor+1
      else
        -- Once in grass, alternate between adjacent collision-free grass
        -- tiles (real footsteps); if no grass neighbour, find the next.
        for _,d in ipairs(DIRS) do
          local nx,ny=x+d[1],y+d[2]
          if behavior(ctx,nx,ny)==2 and walkable(ctx,nx,ny)
              and (previous==nil or nx~=previous[1] or ny~=previous[2]) then
            dir=d[3];break
          end
        end
        if not dir then
          for _,d in ipairs(DIRS) do
            if behavior(ctx,x+d[1],y+d[2])==2 and walkable(ctx,x+d[1],y+d[2]) then
              dir=d[3];break
            end
          end
        end
        if not dir then
          route,tx,ty=nearestGrass(ctx,x,y)
          if not route then break end
          pathCursor=1
          dir=route[pathCursor];pathCursor=pathCursor+1
        end
      end
      if not dir then break end
      local x0,y0=x,y
      local move=F.step(dir)
      F.idle(30)
      local xx,yy=F.pos()
      if xx~=x0 or yy~=y0 then
        previous={x0,y0}
        blocked=0
        if behavior(ctx,xx,yy)==2 then
          landSteps=landSteps+1;visitedReachable=true
        end
      elseif F.ow() then
        blocked=blocked+1
        if blocked>3 then
          F.L("  collision/event blocked repeated live walk")
          break
        end
      end
    else
      -- Triggered by the actual walking loop, not a battle generator.
      if not awaitActions(15000) then break end
      battleCount=battleCount+1
      local species=F.r16(S.gBattleMons+battle.battle_mon_stride)
      F.L(string.format("  real grass battle %d: enemy species ID %d target=%d",
        battleCount,species,WANTED))
      if species==WANTED then found=true;F.shot("qwilfish_encountered") end
      local escaped=flee()
      if not escaped then
        F.L("  battle did not return to the overworld; cannot continue");break
      end
      if found then break end
    end
    if limitTicks%500==0 and F.reportCrash("grass_cycle") then break end
  end
  F.check("actual joypad reached a grass tile from the route warp",
    visitedReachable,"tile_steps="..landSteps)
  F.check("at least one wild encounter was initiated by real footsteps",
    battleCount>=1,"battles="..battleCount)
  F.check("new proposed Qwilfish was actually chosen by wild encounter RNG",
    found,"battles="..battleCount.." target_species="..WANTED)
  F.check("each inspected battle ended via the RUN menu and returned to field",
    F.ow())
  F.check("the tested route and party remain intact",
    F.grp()==GROUP and F.mapn()==MAP and F.r8(S.gPartiesCount)==1)
  F.check("no fatal screen detected while sampling real grass",
    not F.reportCrash("done"))
  F.shot("final_real_candidate")
  F.finish()
end)
