-- Original level evolution, real GBA PT-BR ROM, genuine BAG Rare Candy use.
-- Debug Give Pokemon/Item is fixture setup only. No RAM writes or forced evolution.
-- Do not rerun the already-approved Bagon->Horsea trade or other World suites.
local here=(debug.getinfo(1,"S").source:sub(2)):match("^(.*[/\\])") or ""
package.path=here.."?.lua;"..package.path
local S=require("symbols")
local F=require("lib").new(S,"GrandWorldHorseaSeadraEvolution")
local HORSEA,SEADRA,RARE_CANDY=116,117,102
local SUB0={0,0,0,0,0,0,1,1,2,3,2,3,1,1,2,3,2,3,1,1,2,3,2,3}
local function monSpecies()
  local mon=S.gParties
  local p=F.r32(mon)
  local ot=F.r32(mon+4)
  local a=mon+32+SUB0[(p%24)+1]*12
  return (F.r32(a)~p~ot)&0x7FF
end
-- sizeof(BoxPokemon) == 80; status u32 at +80, level u8 at +84.
-- Verified against original include/pokemon.h by CI preflight.
local function monLevel() return F.r8(S.gParties+84) end
local function tap(k)
  F.press(k,2)
  F.idle(24)
end
local function giveHorsea31()
  F.dbg();F.sel(3);F.sel(1)
  -- Original UI's species spinner begins at ID 1 (115 increments = Horsea 116).
  F.spin(1,1,5)
  F.spin(0,3,1) -- level 31, two-digit level input
  F.idle(130);F.bOut(7);F.idle(90)
end
local function giveRareCandy()
  F.dbg();F.sel(3);F.sel(0)
  -- Game's Give Item spinner begins at 1: spin(1,0,1) -> ITEM_RARE_CANDY=102.
  F.spin(1,0,1)
  tap("A") -- default amount 1
  F.idle(120);F.bOut(7);F.idle(90)
end
local function cursorItem()
  local pocket=F.r8(S.gBagPosition+5)
  if pocket~=0 then return 0,pocket,-1 end
  local p=F.r32(S.gBagPockets+0*S.BagPocket.stride+S.BagPocket.itemsPtr)
  local cur=F.r16(S.gBagPosition+8)
  local scroll=F.r16(S.gBagPosition+18)
  local slot=cur+scroll
  if p<0x02000000 or p>=0x02040000 or slot<0 or slot>=F.pocketCap(0)
    then return 0,pocket,slot end
  return F.r16(p+4*slot),pocket,slot
end
local function hasCandyInBag()
  local p=F.r32(S.gBagPockets+S.BagPocket.itemsPtr)
  if p<0x02000000 or p>=0x02040000 then return false end
  for i=0,F.pocketCap(0)-1 do
    if F.r16(p+4*i)==RARE_CANDY then return true end
  end
  return false
end
local function openBag()
  tap("Start")
  if not F.selectStartIcon(2) then return false end
  tap("A")
  F.idle(150)
  return F.cb2()==S.CB2_BagMenuRun
end
local function chooseCandy()
  for _=1,6 do
    if F.r8(S.gBagPosition+5)==0 then break end
    tap("Right");F.idle(45)
  end
  if F.r8(S.gBagPosition+5)~=0 then return false end
  for _=1,90 do
    local item=cursorItem()
    if item==RARE_CANDY then return true end
    tap("Down")
  end
  return cursorItem()==RARE_CANDY
end
F.run(function()
  client.speedmode(800)
  local started=F.boot(100)
  F.check("new ARM GBA PT-BR boots into real RegionHub",started and F.ow() and F.grp()==100)
  if not started then F.finish();return end
  giveHorsea31()
  F.check("Debug Give Pokemon adds exactly one party mon",F.r8(S.gPartiesCount)==1)
  F.check("source-valid party mon is real encrypted Horsea",monSpecies()==HORSEA,
    "species="..monSpecies())
  F.check("Horsea starts precisely at level 31",monLevel()==31,"level="..monLevel())
  if monSpecies()~=HORSEA or monLevel()~=31 then F.shot("bad_horsea_setup");F.finish();return end
  giveRareCandy()
  F.check("original debug UI put real Rare Candy 102 in Items pocket",hasCandyInBag())
  if not hasCandyInBag() then F.shot("no_candy");F.finish();return end
  local bag=openBag()
  F.check("graphical Start menu opens real GBA Bag",bag)
  if not bag then F.shot("bag_not_open");F.finish();return end
  F.check("bag switched to Items pocket zero",F.r8(S.gBagPosition+5)==0)
  local found=chooseCandy()
  local item,pocket,slot=cursorItem()
  F.check("real bag cursor selected Rare Candy ID 102",found and item==RARE_CANDY,
    string.format("pocket=%d slot=%d item=%d",pocket,slot,item))
  if not found then F.shot("candy_not_selected");F.finish();return end
  F.shot("rare_candy_in_real_bag")
  tap("A") -- open item context
  F.idle(65)
  tap("A") -- choose USE (menu first command)
  F.idle(170)
  F.shot("candy_party_target_prompt")
  -- Select the only real party slot. No gSpecialVar_ItemId/party edits.
  tap("A")
  F.idle(100)
  F.check("game's selected item is the real Rare Candy",F.r16(S.gSpecialVar_ItemId)==RARE_CANDY,
    "item="..F.r16(S.gSpecialVar_ItemId))
  local seenLevel32,seenSeadra=false,false
  for frame=1,22000 do
    if monLevel()>=32 then seenLevel32=true end
    if monSpecies()==SEADRA then seenSeadra=true end
    if seenSeadra and F.ow() then break end
    joypad.set(frame%48==1 and {A=true} or {})
    emu.frameadvance()
    if frame%700==0 and F.reportCrash("seadra_evolution") then break end
  end
  F.check("original Rare Candy raised Horsea to at least level 32",
    seenLevel32,"level="..monLevel())
  F.check("actual species became Seadra 117 after real evolution",
    seenSeadra and monSpecies()==SEADRA,"species="..monSpecies())
  F.check("evolution preserved precisely one party Pokemon",F.r8(S.gPartiesCount)==1)
  F.check("normal game returned to RegionHub overworld",F.ow() and F.grp()==100)
  F.check("no fatal GBA screen after evolution",not F.reportCrash("seadra_finish"))
  F.shot("seadra_evolved")
  F.finish()
end)
