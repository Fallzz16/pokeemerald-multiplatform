#!/usr/bin/env python3
"""Extend upstream StoryProgress with ROM-bound *actual game save/Continue* probes.

The original suite saves using the graphical Start menu, calls
client.reboot_core(), and selects Continue. We add legal party seeding and
checks of the same Pokemon bytes and VAR_PLAYER_CHARACTER before/after that
real save. We do not claim the player's intro hero-menu selection was tested.
"""
from pathlib import Path
import os
import sys
import tempfile

IDENTITY_HELPERS = r'''
-- Grand World M8: save/Continue probes, not synthetic emulator savestates.
local function gwHero()
  return F.r16(F.sb1() + S.SaveBlock1.vars + (0x40FB - 0x4000) * 2)
end
local function gwParty()
  local bytes = {}
  for i = 0, S.Pokemon.size - 1 do
    bytes[#bytes + 1] = string.char(F.r8(S.gParties + i))
  end
  return table.concat(bytes)
end
'''

REPLACEMENTS = [
    (
        "local S=require('symbols');local F=require('lib').new(S,'StoryProgress')",
        "local S=require('symbols');local F=require('lib').new(S,'GrandWorldHeroSave')",
    ),
    (
        "F.run(function()",
        IDENTITY_HELPERS + "\nF.run(function()",
    ),
    (
        "  enter()\n  F.check('fresh hub has deliberate Kanto default'",
        '''  -- Use the game's own debug-party creation; it creates a valid Pokemon,
  -- not a hand-written or checksum-invalid party buffer.
  F.dbg(); F.sel(2); F.sel(9); F.idle(120); F.bOut(6); F.idle(60)
  F.check('GW legal party seeded for save/Continue', F.r8(S.gPartiesCount) == 1,
    'party_count=' .. tostring(F.r8(S.gPartiesCount)))
  setVar(0x40FB, 2) -- Red identity, *not* simulated hero-picker coverage
  setVar(0x40FC, 2) -- original outfit slot
  F.check('GW hero identity staged in persistent region-global var', gwHero() == 2)
  enter()
  F.check('fresh hub has deliberate Kanto default\'''',
    ),
    (
        "  -- Save through the real menu, reboot, Continue, then resolve existing progress.",
        '''  -- Save through the real menu, reboot, Continue, then resolve existing progress.
  local gwBeforeSaveParty = gwParty()
  local gwBeforeSaveHero = gwHero()
  F.check('GW before save: team and Red hero are nonempty and intact',
    F.r8(S.gPartiesCount) == 1 and gwBeforeSaveHero == 2 and #gwBeforeSaveParty == S.Pokemon.size)''',
    ),
    (
        "  F.check('Continue returns to saved region',F.boot(39))",
        '''  F.check('Continue returns to saved region',F.boot(39))
  F.check('GW real save/Continue preserved Red hero identity',
    gwHero() == gwBeforeSaveHero,
    'before=' .. tostring(gwBeforeSaveHero) .. ' after=' .. tostring(gwHero()))
  F.check('GW real save/Continue preserved party count',
    F.r8(S.gPartiesCount) == 1,
    'count=' .. tostring(F.r8(S.gPartiesCount)))
  F.check('GW real save/Continue preserved Pokemon bytes',
    gwParty() == gwBeforeSaveParty)''',
    ),
]


def build(source: str) -> str:
    result = source
    for anchor, replacement in REPLACEMENTS:
        count = result.count(anchor)
        if count != 1:
            raise ValueError(f"StoryProgress upstream drift: {anchor[:60]!r} count={count}")
        result = result.replace(anchor, replacement, 1)
    if result.count("GW real save/Continue preserved") != 3:
        raise ValueError("save/Continue assertions changed")
    return result


def prepare(source: Path, destination: Path) -> None:
    if destination.exists():
        raise ValueError("destination already exists")
    rendered = build(source.read_text(encoding="utf-8"))
    fd, tmp = tempfile.mkstemp(prefix=".gw-save-", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(rendered)
        os.replace(tmp, destination)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: extend_story_save_qa.py StoryProgress.lua GrandWorldHeroSave.lua")
    try:
        prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError, UnicodeError) as exc:
        sys.exit("FAIL CLOSED: " + str(exc))
