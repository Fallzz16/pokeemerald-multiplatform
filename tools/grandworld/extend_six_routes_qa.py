#!/usr/bin/env python3
"""Six real World Hub gate directions with an unchanged, shared carried Pokemon.

Extends the separate GrandWorldHubParty Lua suite, preserving all its asserts
and the pinned upstream HubPassReCross. Fully exercises six region transitions
by talking to the real hub attendants and using the HUB PASS between visits.

Failure is *diagnostic*, never automatically release certification: scripted
intro locks and first-badge destination choices can expose additional bugs.
"""
from pathlib import Path
import os
import sys
import tempfile

NAME = 'require("lib").new(S, "GrandWorldHubParty")'
NEW_NAME = 'require("lib").new(S, "GrandWorldSixRoutes")'
HELPERS = r'''
-- M8 cross-region itinerary: exact six ordered directed pairs, genuine Hub Pass
-- and gate scripts; no write to SetCurrentRegion or synthetic map-teleport here.
local function gwRunSixRoutes()
  if not mapIs(MAY2F_G, MAY2F_M) then
    F.check("GW six-route baseline ends inside May bedroom", false, where())
    return
  end
  local seq = {
    { "Hoenn to Kanto", 3, 1, 11, 38, 1 },
    { "Kanto to Johto", 1, 2, 16, 76, 4 },
    { "Johto to Hoenn", 2, 3, 21, 1, 3 },
    { "Hoenn to Johto", 3, 2, 16, 76, 4 },
    { "Johto to Kanto", 2, 1, 11, 38, 1 },
    { "Kanto to Hoenn", 1, 3, 21, 1, 3 },
  }
  local passed = 0
  for n, item in ipairs(seq) do
    local name, origin, target, x, destG, destM =
      item[1], item[2], item[3], item[4], item[5], item[6]
    local tag = "six_route_" .. n
    local actual = F.r8(F.sb2() + S.SaveBlock2.currentRegion)
    F.check("GW " .. name .. ": entered from persisted origin",
      actual == origin, "origin=" .. actual .. " expected=" .. origin)
    local before = gwPartyFingerprint()
    F.dismiss(15)
    local returned = hubPassOut(tag)
    F.check("GW " .. name .. ": real HUB PASS took us to the hub", returned, where())
    if not returned then return end
    gwTravelProbe(name .. " HUB PASS exit", before, 3)
    local routeOK = F.route({ {16,4}, {x,4}, {x,3} }, tag .. "_attendant")
    F.check("GW " .. name .. ": reached destination attendant", routeOK, where())
    if not routeOK then return end
    F.face("Up")
    F.press("A", 3)
    F.idle(60)
    local yes = yesNo(0, tag .. "_yes")
    F.check("GW " .. name .. ": accepted the real travel confirmation", yes, where())
    if not yes then return end
    local warped = mashToMap(destG, destM, tag .. "_warp", 180)
    F.check("GW " .. name .. ": arrived in destination starting home", warped, where())
    if not warped then return end
    F.check("GW " .. name .. ": persisted active region updated",
      F.r8(F.sb2() + S.SaveBlock2.currentRegion) == target,
      "current=" .. F.r8(F.sb2() + S.SaveBlock2.currentRegion) ..
      " expected=" .. target)
    gwTravelProbe(name .. " arrival", before, 3)
    passed = passed + 1
  end
  F.check("GW exactly six directed region transitions completed", passed == #seq,
    "observed=" .. passed .. " expected=" .. #seq)
end
'''


def build(source: str) -> str:
    if source.count(NAME) != 1:
        raise ValueError("GrandWorldHubParty suite identifier drift")
    text = source.replace(NAME, NEW_NAME)
    anchor = 'local function maleJourney()'
    if text.count(anchor) != 1:
        raise ValueError("unable to add six-direction itinerary")
    text = text.replace(anchor, HELPERS + "\n" + anchor)
    end = '  if booted then mayJourney() end\n  F.finish()'
    if text.count(end) != 1:
        raise ValueError("unexpected upstream suite completion sequence")
    text = text.replace(
        end, '  if booted then mayJourney(); gwRunSixRoutes() end\n  F.finish()')
    if text.count("gwRunSixRoutes()") != 2:
        raise ValueError("missing cross-region itinerary invocation")
    for origin, target in (("Hoenn", "Kanto"), ("Kanto", "Johto"),
                           ("Johto", "Hoenn"), ("Hoenn", "Johto"),
                           ("Johto", "Kanto"), ("Kanto", "Hoenn")):
        if text.count(f'"{origin} to {target}"') != 1:
            raise ValueError(f"missing directed travel {origin} to {target}")
    return text


def prepare(src: Path, dst: Path):
    if dst.exists():
        raise ValueError("GrandWorldSixRoutes output exists; refusing overwrite")
    text = build(src.read_text(encoding="utf-8"))
    fd, tmp = tempfile.mkstemp(prefix=".gw-routes-", dir=dst.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(tmp, dst)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: extend_six_routes_qa.py GrandWorldHubParty.lua GrandWorldSixRoutes.lua")
    try:
        prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    except (ValueError, OSError, UnicodeError) as exc:
        sys.exit("FAIL CLOSED: " + str(exc))
