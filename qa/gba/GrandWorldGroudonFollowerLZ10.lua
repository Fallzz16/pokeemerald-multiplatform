-- Targeted, REAL mGBA rendering probe for 64x64 Groudon LZ10 overworld frames.
-- The one Groudon is obtained through World's original Give Pokemon debug UI,
-- in a disposable emulator session. No saved file, synthetic OW object or game
-- asset is created. Live sprite pixels are verified in OBJ VRAM.
local here = (debug.getinfo(1,"S").source:sub(2)):match("^(.*[/\\])") or ""
package.path = here .. "?.lua;" .. package.path
local S = require("symbols")
local F = require("lib").new(S, "GrandWorldGroudonFollowerLZ10")

local SPECIES_GROUDON = 383
local FOLLOWER_LOCAL_ID = 254
local OBJ_EVENT_MON = 0x4000
local VRAM_OBJ = 0x06010000
local FRAME_BYTES = 2048
local EXPECTED_HASHES = {__GROUDON_FNV_LIST__}
local EXPECTED = {}
for i,hash in ipairs(EXPECTED_HASHES) do EXPECTED[hash] = i end
assert(#EXPECTED_HASHES == 6, "must provide all 6 original Groudon frame hashes")

local function findFollower()
  for i=0,15 do
    local addr=S.gObjectEvents+i*S.ObjectEvent.stride
    if (F.r8(addr) & 1) ~= 0
        and F.r8(addr+S.ObjectEvent.localId)==FOLLOWER_LOCAL_ID then
      return {
        address=addr,
        gfx=F.r16(addr+S.ObjectEvent.graphicsId),
        visible=(F.r8(addr+S.ObjectEvent.flags1)&0x20)==0,
        sprite=F.r8(addr+0x23), -- pinned include/global.fieldmap.h:ObjectEvent.spriteId
      }
    end
  end
  return nil
end

local function copyFNV(start)
  local hash=2166136261
  for i=0,FRAME_BYTES-1 do
    hash = ((hash ~ F.r8(start+i))*16777619) & 0xFFFFFFFF
  end
  return hash
end

local function snapshot(tag)
  local f=findFollower()
  if not f or not f.visible or f.gfx ~= OBJ_EVENT_MON+SPECIES_GROUDON then
    return false,"Groudon follower absent/invisible/incorrect graphics",nil
  end
  if f.sprite>=S.Sprite.count or (F.r16(S.gSprites+f.sprite*S.Sprite.stride+S.Sprite.inUse)&1)==0 then
    return false,"follower lacks live native sprite",nil
  end
  local addr=S.gSprites+f.sprite*S.Sprite.stride
  -- struct Sprite begins with GBA OAM attributes, attr2 at +4, tile index 10 bits.
  local tile=F.r16(addr+4)&0x03FF
  local vr=VRAM_OBJ+tile*32
  if tile>960 then return false,"64-tile frame overflows native OBJ VRAM",nil end
  local hash=copyFNV(vr)
  local frame=EXPECTED[hash]
  F.L(string.format("GROUDON_FRAME tag=%s sprite=%d tile=%d hash=0x%08X frame=%s",
    tag,f.sprite,tile,hash,tostring(frame)))
  if not frame then return false,"unrecognized 64x64 pixel bytes in native OBJ VRAM",hash end
  return true,"frame="..tostring(frame),hash
end

F.run(function()
  if not F.boot(100) then F.check("real World GBA boot",false);F.finish();return end
  F.check("real World GBA boot", F.ow())
  F.idle(40)
  -- Give X (root row 3) > Pokemon Basic (row 1).
  -- The spinner floors to 1: spin(3,8,2) means species 383.
  F.dbg();F.sel(3);F.sel(1);F.idle(20)
  F.spin(3,8,2);F.idle(20)
  F.spin(0,1,0);F.idle(80) -- level 11; exact level is not under test.
  F.bOut(8);F.idle(40)
  F.check("debug Give Pokemon created a native party",F.r8(S.gPartiesCount)>0,
          "party count="..F.r8(S.gPartiesCount))

  -- Enter a route using real warp debug UI; the game creates the follower.
  local warped=F.warpTo(0,7,5,0,0,2,0,0,0,75,2,"groudon_route29")
  F.check("real warp entered Route 29",warped and F.grp()==75 and F.mapn()==2)
  if not warped then F.finish();return end
  F.idle(80)

  local follower
  local steps={"Down","Left","Right","Up","Down","Right","Left","Down",
               "Up","Down","Left","Right","Up","Down","Right","Left"}
  local checked=0
  local good=0
  local bad=0
  local firstShot=false
  local frames={}
  for i=1,#steps do
    F.step(steps[i]);F.idle(28)
    if F.reportCrash("groudon_frame_"..i) then break end
    follower=findFollower()
    if follower and follower.visible and follower.gfx==OBJ_EVENT_MON+SPECIES_GROUDON then
      local ok,info,hash=snapshot("step-"..i)
      checked=checked+1
      if ok then
        good=good+1
        frames[hash]=true
        if not firstShot then F.shot("groudon_64x64_lz10_visible");firstShot=true end
      else
        bad=bad+1
        F.L("  FRAME REJECTED: "..info)
      end
    end
  end
  follower=findFollower()
  F.check("Groudon appears as native active visible follower",
    follower~=nil and follower.visible and follower.gfx==OBJ_EVENT_MON+SPECIES_GROUDON,
    follower and string.format("gfx=0x%X sprite=%d visible=%s",
      follower.gfx,follower.sprite,tostring(follower.visible)) or "absent")
  F.check("at least four GPU frame observations",checked>=4,
    "observations="..checked)
  F.check("all sampled GBA OBJ VRAM Groudon pixels match an original 64x64 frame",
    good>0 and bad==0,"good="..good.." bad="..bad)
  local distinct=0
  for _ in pairs(frames) do distinct=distinct+1 end
  F.check("Groudon animates across at least two distinct original frames",
    distinct>=2,"distinct frames="..distinct)
  F.check("actual mGBA screenshot captured",firstShot)
  local crash=F.reportCrash("groudon_final")
  F.check("Groudon frame switching does not crash the ARM/GBA game",not crash,
    crash or "clean")
  F.finish()
end)
