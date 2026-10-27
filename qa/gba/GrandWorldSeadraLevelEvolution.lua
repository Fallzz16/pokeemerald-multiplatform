-- M9 targeted acceptance: real Horsea (116) -> Seadra (117) level evolution.
-- Debug is used only to grant a legal Horsea Lv31 and one Rare Candy.
-- Level-up and evolution must happen from actual Bag/party UI on real ARM GBA.
-- No RAM party, level, flags, item or RNG writes. Never distribute ROMs/saves.
local here=(debug.getinfo(1,"S").source:sub(2)):match("^(.*[/\\])") or ""
package.path=here.."?.lua;"..package.path
local S=require("symbols")
local F=require("lib").new(S,"GrandWorldSeadraLevelEvolution")
local HORSEA,SEADRA,RARE_CANDY=116,117,102
local SUB0={0,0,0,0,0,0,1,1,2,3,2,3,1,1,2,3,2,3,1,1,2,3,2,3}
local function partySpecies()
  local mon=S.gParties
  local p=F.r32(mon);local ot=F.r32(mon+4)
  return (F.r32(mon+32+SUB0[(p%24)+1]*12)~p~ot)&0x7FF
end
local function partyLevel() return F.r8(S.gParties+84) end
local function itemQuantity()
  local b=S.gBagPockets
  local ptr=F.r32(b+S.BagPocket.itemsPtr)
  if ptr<0x02000000 or ptr>=0x02040000 then return 0 end
  local n=0
  for i=0,F.pocketCap(0)-1 do
    if F.r16(ptr+i*4)==RARE_CANDY then
      -- Quantity is encrypted on game SRAM; presence is enough here.
      n=n+1
    end
  end
  return n
end
local function addHorseaLevel31()
  F.dbg();F.sel(3);F.sel(1)
  F.spin(1,1,5) -- debug species spinner is one-based -> HORSEA(116)
  F.spin(0,3,1) -- actual level31
  F.idle(140);F.bOut(7);F.idle(70)
end
local function addRareCandy()
  F.dbg();F.sel(3);F.sel(0)
  F.spin(1,0,1) -- debug item spinner is one-based -> RARE_CANDY(102)
  F.press("A",2);F.idle(50) -- quantity one
  F.idle(140);F.bOut(7);F.idle(80)
end
F.run(function()
  client.speedmode(800)
  local boot=F.boot(100)
  F.check("fresh disposable pinned GBA PT-BR boots into RegionHub",boot and F.ow() and F.grp()==100)
  if not boot then F.finish();return end
  F.check("fresh game party is empty",F.r8(S.gPartiesCount)==0)
  addHorseaLevel31()
  F.check("debug UI prepared one legal Pokemon",F.r8(S.gPartiesCount)==1)
  F.check("prepared species is encrypted real Horsea 116",partySpecies()==HORSEA)
  F.check("prepared Horsea has real level 31",partyLevel()==31)
  if partySpecies()~=HORSEA or partyLevel()~=31 then F.shot("setup_horsea_failed");F.finish();return end
  addRareCandy()
  local before=itemQuantity()
  F.check("one Rare Candy exists in actual Bag Items pocket",before==1)
  F.shot("horse31_rare_candy_preuse")
  if before~=1 then F.finish();return end
  F.press("Start",2);F.idle(90)
  local bagIcon=F.selectStartIcon(2) -- pinned Usm_Icons: USM_ICO_BAG=2
  F.check("selected real Bag icon in graphical Start wheel",bagIcon)
  if not bagIcon then F.shot("start_bag_missing");F.finish();return end
  F.press("A",2);F.idle(190)
  F.shot("bag_items_pocket")
  -- First new item in an otherwise empty Items pocket; normal A -> Use -> party.
  F.press("A",2);F.idle(80)
  F.shot("candy_context_use")
  F.press("A",2);F.idle(190)
  F.shot("choose_horsea_from_party")
  F.press("A",2);F.idle(120)
  F.shot("candy_used_party")
  local evolved=false
  for f=1,16000 do
    if F.r8(S.gPartiesCount)==1 and partySpecies()==SEADRA and partyLevel()>=32 then
      evolved=true;break
    end
    joypad.set(f%40==1 and {A=true} or {})
    emu.frameadvance()
    if f%750==0 and F.reportCrash("seadra_evolution") then break end
  end
  F.check("real candy action consumed the original Bag item",itemQuantity()==0)
  F.check("actual Horsea level advanced from 31 to 32",partyLevel()==32)
  F.check("real GBA evolution changed encrypted species into Seadra 117",partySpecies()==SEADRA)
  F.check("evolution kept exactly one party Pokemon",F.r8(S.gPartiesCount)==1)
  F.check("evolution produced no fatal GBA game screen",not F.reportCrash("seadra_final"))
  F.shot("seadra_level32_result")
  F.finish()
end)
