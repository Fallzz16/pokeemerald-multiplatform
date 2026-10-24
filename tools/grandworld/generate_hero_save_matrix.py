#!/usr/bin/env python3
"""Create six real-save mGBA permutations from the proven StoryProgress-based QA.

The player identity is deliberately prepared in persistent vars (not selected
through Oak's menu). This tests save/Continue, gender and team byte integrity
for every protagonist, not character artwork or the six-choice intro UI.
"""
from pathlib import Path
import os
import sys
import tempfile

HEROES = (
    ("Brendan", 0, 0),
    ("May", 1, 1),
    ("Red", 2, 0),
    ("Leaf", 3, 1),
    ("Ethan", 4, 0),
    ("Lyra", 5, 1),
)

def once(text, original, replacement):
    if text.count(original) != 1:
        raise ValueError(f"GrandWorldHeroSave source drift: {original[:64]!r} matches {text.count(original)}")
    return text.replace(original, replacement, 1)

def render(text, name, slot, gender):
    suite = "GrandWorldSave" + name
    text = once(text,
        "require('lib').new(S,'GrandWorldHeroSave')",
        "require('lib').new(S,'" + suite + "')")
    text = once(text,
        "  setVar(0x40FB, 2) -- Red identity, *not* simulated hero-picker coverage",
        "  F.w8(F.sb2() + S.SaveBlock2.playerGender, " + str(gender) + ") -- staged test gender\n"
        "  setVar(0x40FB, " + str(slot) + ") -- " + name + " identity, NOT tested via intro menu")
    text = once(text, "  setVar(0x40FC, 2) -- original outfit slot",
                "  setVar(0x40FC, " + str(slot) + ") -- matching 0..5 outfit slot")
    text = once(text,
        "F.check('GW hero identity staged in persistent region-global var', gwHero() == 2)",
        "F.check('GW " + name + " identity staged in region-global var', gwHero() == " + str(slot) + ")")
    text = once(text,
        "gwBeforeSaveHero == 2 and #gwBeforeSaveParty == S.Pokemon.size",
        "gwBeforeSaveHero == " + str(slot) + " and #gwBeforeSaveParty == S.Pokemon.size")
    text = once(text,
        "F.check('GW before save: team and Red hero are nonempty and intact',",
        "F.check('GW before save: team and " + name + " hero are nonempty and intact',")
    text = once(text,
        "F.check('GW real save/Continue preserved Red hero identity',",
        "F.check('GW real save/Continue preserved " + name + " hero identity',")
    text = once(text,
        "  F.check('GW real save/Continue preserved party count',",
        "  F.check('GW real save/Continue preserved " + name + " gender',\n"
        "    F.r8(F.sb2() + S.SaveBlock2.playerGender) == " + str(gender) + ")\n"
        "  F.check('GW real save/Continue preserved party count',")
    if text.count("GW real save/Continue preserved") != 4:
        raise ValueError("all four mandatory save/Continue checks must exist")
    return text


def prepare(source: Path, directory: Path):
    original = source.read_text(encoding="utf-8")
    outputs = [(directory / ("GrandWorldSave" + name + ".lua"),
                render(original, name, slot, gender))
               for name, slot, gender in HEROES]
    if any(path.exists() for path, _ in outputs):
        raise ValueError("one or more hero suite outputs already exist")
    written = []
    try:
        for destination, content in outputs:
            fd, tmp = tempfile.mkstemp(prefix=".gw-hero-", dir=directory)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                os.replace(tmp, destination)
                written.append(destination)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        raise
    return [path.name for path, _ in outputs]

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: generate_hero_save_matrix.py GrandWorldHeroSave.lua /world/test/overworld/lua")
    try:
        paths = prepare(Path(sys.argv[1]), Path(sys.argv[2]))
        print("Generated six independent Save/Continue suites:", ", ".join(paths))
    except (OSError, ValueError, UnicodeError) as exc:
        sys.exit("FAIL CLOSED: " + str(exc))
