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
  local walk=F.leg(4,3)
  local x,y=F.pos()
  F.check("real directional inputs can stand directly before trade NPC",
    walk and x==4 and y==3,"position="..x..","..y)
  if not walk then F.finish();return end

  F.face("Up")
  F.press("A",2);F.idle(60)
  F.shot("horse_trader_first_offer")
  local xx,yy=F.pos()
  local block=not F.step("Down")
  local qx,qy=F.pos()
  F.check("talking to the trader locked field movement for real dialogue",
    block and xx==qx and yy==qy and xx==4 and yy==3,
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
