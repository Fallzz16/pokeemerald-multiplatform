#!/usr/bin/env python3
"""Expose the actual World/M8 game frame to a future SDL2 event loop.

Applies ONLY to a disposable World checkout, AFTER GBA baseline validation.
GBA AgbMain and its infinite loop remain byte-for-byte equivalent whenever
GW_WORLD_NATIVE is NOT defined. A generated World-frame routine reuses the
existing source of the actual game's core loop; it does not synthesize gameplay.
"""
import argparse
import json
import os
from pathlib import Path
import tempfile

BOOT = ("    gAgbMainLoop_sp = __builtin_frame_address(0);\n"
        "    AgbMainLoop();")
LOOP_START = "void AgbMainLoop(void)\n{\n    for (;;)\n    {\n"
LOOP_END = "        WaitForVBlank();\n    }\n}\n"
NEXT_SECTION = "\nstatic void UpdateLinkAndCallCallbacks(void)\n{"

def transform(source):
    if "void GwWorldFrame(void)" in source or "void GwWorldVBlank(void)" in source:
        raise ValueError("World frame adapter already installed")
    if source.count(BOOT) != 1 or source.count(LOOP_START) != 1:
        raise ValueError("World main bootstrap or frame loop changed")
    if source.count(NEXT_SECTION) != 1:
        raise ValueError("World callbacks section changed")
    start = source.index(LOOP_START)
    after_start = start + len(LOOP_START)
    end = source.find(LOOP_END, after_start)
    following = source.find(NEXT_SECTION, after_start)
    if end < 0 or following < 0 or end + len(LOOP_END) > following:
        raise ValueError("World VBlank loop changed")
    body = source[after_start:end]
    if not body.startswith("        ReadKeys();") or (
            "PlayTimeCounter_Update();" not in body or
            "MapMusicMain();" not in body or
            "UpdateLinkAndCallCallbacks();" not in body or
            "WaitForVBlank();" in body):
        raise ValueError("World frame body no longer matches expected behavior")

    # The native host will call GwWorldFrame followed by GwWorldVBlank once
    # per SDL2 frame. No busy-wait on the emulated GBA VBlank interrupt.
    api = (
        "\n#if defined(GW_WORLD_NATIVE)\n"
        "void GwWorldFrame(void)\n{\n" + body + "}\n\n"
        "void GwWorldVBlank(void)\n{\n    VBlankIntr();\n}\n"
        "#endif\n"
    )
    # Insert immediately after the untouched GBA loop.
    position = end + len(LOOP_END)
    source = source[:position] + api + source[position:]
    boot_native = (
        "#if defined(GW_WORLD_NATIVE)\n"
        "    /* Do not enter the endless GBA loop or save a dead stack frame. */\n"
        "    gAgbMainLoop_sp = NULL;\n"
        "#else\n" + BOOT + "\n#endif"
    )
    return source.replace(BOOT, boot_native, 1)

def run(root, report, apply):
    root = Path(root).resolve()
    file = root / "src/main.c"
    if not file.is_file() or not (root / "src/region_switch.c").exists():
        raise ValueError("expected disposable Pokémon World checkout")
    before = file.read_text(encoding="utf-8")
    after = transform(before)
    if apply:
        fd, staging = tempfile.mkstemp(prefix=".gw-frame-", suffix=".tmp", dir=file.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(after)
            os.replace(staging, file)
        finally:
            if os.path.exists(staging):
                os.unlink(staging)
    outcome = {
        "schema": 1, "stage": "P2_actual_World_frame_extraction",
        "file": "src/main.c", "applied": bool(apply),
        "GBA_loop_preserved": True,
        "native_initialization_returns": True,
        "native_frame_exports": ["GwWorldFrame", "GwWorldVBlank"],
        "game_linked": False, "gameplay_verified": False,
    }
    Path(report).write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    return outcome

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--report", default="native-world-frame.json")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    try:
        print(json.dumps(run(args.world, args.report, args.apply), indent=2))
    except (OSError, ValueError) as e:
        p.exit(1, "FRAME OVERLAY REFUSED: %s\n" % e)

if __name__ == "__main__":
    main()
