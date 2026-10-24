#!/usr/bin/env python3
"""Extend SIX real World Hub crossings with an ACTUAL Save / reboot / Continue.

No fake warp for the saved leg: the six original gate transitions run first,
followed by the game's Save entry and a reboot of the emulated GBA core.
This is a distinct suite and never weakens the proven 167/167 itinerary.
"""
from pathlib import Path
import os
import sys
import tempfile

OLD_NAME = 'require("lib").new(S, "GrandWorldSixRoutes")'
NEW_NAME = 'require("lib").new(S, "GrandWorldCrossRegionSave")'
END = '''  F.check("GW exactly six directed region transitions completed", passed == #seq,
    "observed=" .. passed .. " expected=" .. #seq)
end'''
NEW_END = '''  F.check("GW exactly six directed region transitions completed", passed == #seq,
    "observed=" .. passed .. " expected=" .. #seq)
  -- The genuine six gate crossings above are a precondition, not mocked.
  F.check("GW cross-region save reached all six gates", passed == #seq)
  if passed ~= #seq then return end
  local beforeParty = gwPartyFingerprint()
  local beforeHero = gwHeroVar()
  F.check("GW cross-region carried Pokemon before Save", F.r8(S.gPartiesCount) == 1)
  F.check("GW cross-region Leaf identity before Save", beforeHero == 3)
  -- Exact same graphical Save/Continue mechanism as StoryProgress's live test.
  F.dismiss(20)
  F.press("Start", 2); F.idle(90)
  local hasSave = F.selectStartIcon(7)
  F.check("GW cross-region real Start-menu Save option", hasSave)
  if not hasSave then return end
  F.press("A", 2); F.idle(90)
  F.press("A", 2); F.idle(90)
  F.press("A", 2); F.idle(600)
  client.reboot_core()
  F.idle(240)
  local loaded = F.boot(1)
  F.check("GW cross-region Continue loads Hoenn bedroom",
    loaded and F.grp() == 1 and F.mapn() == 3,
    "group=" .. F.grp() .. " map=" .. F.mapn())
  if not loaded then return end
  F.check("GW cross-region loaded active Hoenn region",
    F.r8(F.sb2() + S.SaveBlock2.currentRegion) == 3)
  F.check("GW cross-region loaded Pokemon count intact",
    F.r8(S.gPartiesCount) == 1)
  F.check("GW cross-region loaded Pokemon data byte-identical",
    gwPartyFingerprint() == beforeParty)
  F.check("GW cross-region loaded Leaf hero identity",
    gwHeroVar() == beforeHero and beforeHero == 3)
end'''


def build(source: str):
    if source.count(OLD_NAME) != 1 or NEW_NAME in source:
        raise ValueError("six-route suite name drift")
    if source.count(END) != 1:
        raise ValueError("six-route completion anchor drift")
    if source.count('if booted then mayJourney(); gwRunSixRoutes() end') != 1:
        raise ValueError("six-route caller unexpectedly changed")
    updated = source.replace(OLD_NAME, NEW_NAME, 1).replace(END, NEW_END, 1)
    if updated.count('F.check("GW cross-region') != 9:
        raise ValueError("required saved-trip assertions changed")
    return updated


def prepare(source: Path, destination: Path):
    if destination.exists():
        raise ValueError("cross-region save suite already exists")
    result = build(source.read_text(encoding="utf-8"))
    fd, tmp = tempfile.mkstemp(prefix=".gw-cross-save-", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(result)
        os.replace(tmp, destination)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: extend_cross_region_save_qa.py GrandWorldSixRoutes.lua GrandWorldCrossRegionSave.lua")
    try:
        prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    except (ValueError, OSError, UnicodeError) as exc:
        sys.exit("FAIL CLOSED: " + str(exc))
