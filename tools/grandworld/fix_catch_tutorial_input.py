#!/usr/bin/env python3
"""Repair upstream mGBA CatchTutorial input interference in an isolated checkout.

Evidence: the unmodified suite reports 14/15, running from Wally's battle;
same-ROM diagnostic with B suppressed for Wally reports 15/15. No assertions,
ROM, battle routines, or gameplay data are modified.
"""
from pathlib import Path
import os
import sys
import tempfile

BEFORE = 'if i % 24 == 0 then F.press("B", 1) end'
AFTER = 'if tag == "kanto" and i % 24 == 0 then F.press("B", 1) end'


def apply(path: Path):
    original = path.read_text(encoding="utf-8")
    if original.count(BEFORE) != 1 or AFTER in original:
        raise ValueError("CatchTutorial upstream input hook drift; refusing patch")
    fixed = original.replace(BEFORE, AFTER, 1)
    # No game assertion or battle logic is removed by this exact replacement.
    if fixed.replace(AFTER, BEFORE, 1) != original:
        raise ValueError("CatchTutorial patch changed unrelated content")
    fd, name = tempfile.mkstemp(prefix=".catch-input-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(fixed)
        os.chmod(name, path.stat().st_mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: fix_catch_tutorial_input.py /isolated/world/test/overworld/lua/CatchTutorial.lua")
    try:
        apply(Path(sys.argv[1]))
    except (ValueError, OSError, UnicodeError) as exc:
        sys.exit("FAIL CLOSED: " + str(exc))
