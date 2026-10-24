#!/usr/bin/env python3
"""Extend the pinned World HubPassReCross mGBA scenario with *real hub gate*
party-byte and hero-variable persistence probes. Never modify the upstream suite.

This is field/warp-only coverage: no actual game save/reload, starter selection,
other-region gate or avatar-animation validation is claimed by the assertions.
"""
from pathlib import Path
import os
import sys
import tempfile

HELPERS = r'''
-- Grand World M8: one real Pokemon, full byte-for-byte integrity over hub travel.
local GW_HERO = 0x40FB
local function gwPartyFingerprint()
  local bytes = {}
  for i = 0, S.Pokemon.size - 1 do
    bytes[#bytes + 1] = string.char(F.r8(S.gParties + i))
  end
  return table.concat(bytes)
end

local function gwTravelProbe(label, fingerprint, hero)
  F.check("GW " .. label .. ": exactly one carried Pokemon",
    F.r8(S.gPartiesCount) == 1, "count=" .. tostring(F.r8(S.gPartiesCount)))
  F.check("GW " .. label .. ": Pokemon bytes unchanged",
    gwPartyFingerprint() == fingerprint)
  F.check("GW " .. label .. ": protagonist identity retained",
    varGet(GW_HERO) == hero,
    "hero=" .. tostring(varGet(GW_HERO)) .. " expected=" .. tostring(hero))
end

local function gwPrepareSinglePokemon()
  -- The existing game's real debug Set Party code creates legal Pokemon.
  -- Retain the first and clear only extra slots, so the introductory gate
  -- retains a free slot for the new-region starter.
  F.dbg(); F.sel(2); F.sel(9); F.idle(120); F.bOut(6); F.idle(60)
  local n = F.r8(S.gPartiesCount)
  if not F.check("GW debug provided a legal team before hub traversal",
                 n >= 1 and n <= 6, "initial=" .. tostring(n)) then
    return nil
  end
  F.check("GW Pokemon struct size is 100", S.Pokemon.size == 100)
  if S.Pokemon.size ~= 100 then return nil end
  for slot = 1, 5 do
    for i = 0, S.Pokemon.size - 1 do
      F.w8(S.gParties + slot * S.Pokemon.size + i, 0)
    end
  end
  F.w8(S.gPartiesCount, 1)
  return gwPartyFingerprint()
end
'''

# Anchor each side of a real scripted hub roundtrip. Inject a separately named
# suite, preserving the original upstream HubPassReCross unchanged.
REPLACEMENTS = [
    (
        'local hubPass\nlocal booted = false',
        'local hubPass\nlocal booted = false\n' + HELPERS,
    ),
    (
        '  F.w16(F.sb1() + S.SaveBlock1.registeredItem, hubPass)\n  F.press("Select", 2); F.idle(90)\n  -- Cursor rests on NO by design',
        '''  local gwPartyMale = gwPrepareSinglePokemon()
  if not gwPartyMale then return end
  varSet(GW_HERO, 2) -- Red identity, male; do not fake name-menu coverage
  gwTravelProbe("before male hub return", gwPartyMale, 2)
  F.w16(F.sb1() + S.SaveBlock1.registeredItem, hubPass)
  F.press("Select", 2); F.idle(90)
  -- Cursor rests on NO by design''',
    ),
    (
        '  F.shot("s1_back_in_hub")',
        '  F.shot("s1_back_in_hub")\n  gwTravelProbe("in hub from male room", gwPartyMale, 2)',
    ),
    (
        '  F.shot("s1_after_recross")',
        '  F.shot("s1_after_recross")\n  gwTravelProbe("after real male Hoenn re-cross", gwPartyMale, 2)',
    ),
    (
        '  F.w8(F.sb2() + S.SaveBlock2.playerGender, 1)   -- FEMALE',
        '''  F.w8(F.sb2() + S.SaveBlock2.playerGender, 1)   -- FEMALE
  varSet(GW_HERO, 3) -- Leaf identity for female gate probe
  local gwPartyFemale = gwPartyFingerprint()
  gwTravelProbe("before female scripted hub return", gwPartyFemale, 3)''',
    ),
    (
        '  if not inHub then F.shot("s4_no_hub"); return end',
        '''  if not inHub then F.shot("s4_no_hub"); return end
  gwTravelProbe("female returned to hub", gwPartyFemale, 3)''',
    ),
    (
        '  F.check("S4 first cross as MAY landed in MAY\'s 2F, so the gate took the FEMALE branch",',
        '''  gwTravelProbe("female first gate to Hoenn", gwPartyFemale, 3)
  F.check("S4 first cross as MAY landed in MAY's 2F, so the gate took the FEMALE branch",''',
    ),
    (
        '  F.shot("s5_after_recross")',
        '  F.shot("s5_after_recross")\n  gwTravelProbe("female second real Hoenn gate", gwPartyFemale, 3)',
    ),
]


def build(source: str) -> str:
    oldname = 'require("lib").new(S, "HubPassReCross")'
    if source.count(oldname) != 1:
        raise ValueError("unexpected original HubPassReCross suite identifier")
    result = source.replace(oldname, 'require("lib").new(S, "GrandWorldHubParty")')
    for anchor, replacement in REPLACEMENTS:
        if result.count(anchor) != 1:
            raise ValueError(f"upstream hub suite drift at {anchor[:65]!r}: {result.count(anchor)}")
        result = result.replace(anchor, replacement, 1)
    if result.count('gwTravelProbe(') != 8:  # declaration + seven actual checkpoints
        raise ValueError("travel assertion checkpoints unexpectedly changed")
    return result


def prepare(source: Path, destination: Path) -> None:
    if destination.exists():
        raise ValueError("destination already exists; refusing overwrite")
    rendered = build(source.read_text(encoding="utf-8"))
    fd, tmp = tempfile.mkstemp(prefix=".gw-hub-", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(rendered)
        os.replace(tmp, destination)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: extend_hub_party_qa.py HubPassReCross.lua GrandWorldHubParty.lua")
    try:
        prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError, UnicodeError) as exc:
        sys.exit(f"FAIL CLOSED: {exc}")
