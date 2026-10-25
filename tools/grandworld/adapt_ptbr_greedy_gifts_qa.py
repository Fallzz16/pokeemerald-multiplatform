#!/usr/bin/env python3
"""Strictly adapt one English-literal QA assertion for the localized World.

This modifies only the ephemeral test file in the World checkout. The actual
game scripts, their starter gating flags and the original repository are not
modified by this QA adapter. It retains the original English check as well.
"""
import argparse
from pathlib import Path

OLD = 'if "Better leave the others alone" not in birch:'
NEW = ('if "Better leave the others alone" not in birch '
       'and "Voce ja pegou seu POKEMON." not in birch:')
ELM_OLD = 'if "Probably shouldn\'t touch" not in elm:'
ELM_NEW = ('if "Probably shouldn\'t touch" not in elm '
           'and "Provavelmente nao devia tocar!" not in elm:')
QA_PATH = "test/overworld/ValidateGreedyGifts.py"
MAP_PATH = "data/maps/LittlerootTown_ProfessorBirchsLab/scripts.inc"
MARKER = "LittlerootTown_ProfessorBirchsLab_Text_BetterLeaveOthersAlone:"


def apply(world, write=False):
    world = Path(world)
    path = world / QA_PATH
    game_path = world / MAP_PATH
    qa = path.read_text(encoding="utf-8")
    story = game_path.read_text(encoding="utf-8")
    if story.count(MARKER) != 1:
        raise ValueError("Birch original starter lock label missing or duplicated")
    if "Voce ja pegou seu POKEMON." not in story:
        raise ValueError("expected translated Birch starter lock is missing")
    if qa.count(OLD) != 1 or NEW in qa:
        raise ValueError("original English-only QA guard changed or already patched")
    if qa.count(ELM_OLD) != 1 or ELM_NEW in qa:
        raise ValueError("Elm starter protection missing from baseline QA")
    if 'FLAG_JOHTO_STARTER_CHOSEN' not in qa:
        raise ValueError("the Johto flag assertion must remain present")
    updated = qa.replace(OLD, NEW).replace(ELM_OLD, ELM_NEW)
    # These assertions must continue checking the same warnings, now in
    # either original English or the PT-BR ROM. Never remove any conditions.
    if write:
        path.write_text(updated, encoding="utf-8")
    return {"mode": "applied" if write else "preflight", "changed_file": QA_PATH,
            "gameplay_files_modified": 0, "qa_guard_preserved": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(apply(args.world, args.apply))


if __name__ == "__main__":
    main()
