#!/usr/bin/env python3
"""Produce a diagnostic-only CatchTutorial variant; never replace the release test.

Hypothesis: pressing B while observing Wally's scripted tutorial interrupts it
and causes the 'got away safely' outcome, concealing expected dialogue.
The variant changes only that input for Wally; all 15 assertions remain intact.
"""
from pathlib import Path
import sys

def prepare(source: Path, destination: Path) -> None:
    original = source.read_text(encoding="utf-8")
    before = 'if i % 24 == 0 then F.press("B", 1) end'
    after = 'if tag == "kanto" and i % 24 == 0 then F.press("B", 1) end'
    if original.count(before) != 1 or after in original:
        raise ValueError("unexpected upstream CatchTutorial sampling logic")
    if destination.exists():
        raise ValueError("diagnostic file already exists; refusing overwrite")
    destination.write_text(original.replace(before, after), encoding="utf-8")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: diagnose_catch_tutorial.py SOURCE.lua DIAGNOSTIC.lua")
    try:
        prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError) as exc:
        sys.exit(f"FAIL CLOSED: {exc}")
