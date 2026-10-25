#!/usr/bin/env python3
"""P2 guard three ARM-only functions in disposable World native builds.

Keeps original ARM code unchanged without GW_WORLD_NATIVE:
  - Random32Core: same existing SFC32 C recurrence, not a new RNG.
  - MultiBootWaitCycles: bounded host wait only; GBA cable transport unsupported.
  - MusicPlayerJumpTableCopy: never-used ARM BIOS SWI excluded on host.
This code does not enable GBA wireless/multiboot or test full game audio.
"""
import argparse
import json
import os
from pathlib import Path
import tempfile

RANDOM_START = "static u32 NAKED Random32Core(void)\n{"
RANDOM_END = "\nu32 Random32(void)\n{"
MBOOT_START = "NAKED\nstatic void MultiBootWaitCycles(u32 cycles)\n{"
MBOOT_END = "\nstatic void MultiBootWaitSendDone(void)\n{"
M4A_ORIGINAL = """static void UNUSED MusicPlayerJumpTableCopy(void)
{
    asm("swi 0x2A");
}
"""


def wrap(source, begin, end, needle, native):
    if source.count(begin) != 1 or source.count(end) != 1:
        raise ValueError("pinned ARM function anchors moved")
    first = source.index(begin)
    last = source.index(end, first + len(begin))
    original = source[first:last]
    if needle not in original or "#if defined(GW_WORLD_NATIVE)" in original:
        raise ValueError("original ARM implementation changed")
    return source[:first] + (
        "#if defined(GW_WORLD_NATIVE)\n"
        + native + "\n#else\n"
        + original.rstrip("\n")
        + "\n#endif\n\n"
        + source[last:].lstrip("\n")
    )


def transform_random(source):
    return wrap(
        source, RANDOM_START, RANDOM_END, 'asm(".thumb',
        """static u32 Random32Core(void)
{
    /* SFC32 is already implemented and used by Random2_32/SeedRng.
     * Its unsigned operations match the original GBA assembler sequence. */
    return _SFC32_Next_Stream(&gRngValue, STREAM1);
}"""
    )


def transform_multiboot(source):
    return wrap(
        source, MBOOT_START, MBOOT_END, 'asm_unified(',
        """static void MultiBootWaitCycles(u32 cycles)
{
    /* No GBA serial hardware is emulated. This is a bounded host delay
     * for unsupported cable mode, not a claim of working multiboot. */
    volatile u32 remaining = cycles > 100000u ? 100000u : cycles;
    while (remaining > 0)
        --remaining;
}"""
    )


def transform_m4a(source):
    if source.count(M4A_ORIGINAL) != 1:
        raise ValueError("unused ARM SWI thunk changed or already patched")
    native = """static void UNUSED MusicPlayerJumpTableCopy(void)
{
#if !defined(GW_WORLD_NATIVE)
    asm("swi 0x2A");
#else
    /* Unused GBA software interrupt; cannot execute on x86. */
#endif
}
"""
    return source.replace(M4A_ORIGINAL, native, 1)


TRANSFORMS = (
    ("src/random.c", transform_random),
    ("src/multiboot.c", transform_multiboot),
    ("src/m4a.c", transform_m4a),
)


def apply(world, report, edit=False):
    root = Path(world).resolve()
    if not (root / "src/main.c").is_file():
        raise ValueError("World checkout missing")
    changes = []
    # Validate all three originals before mutating ANY source.
    for relative, transformer in TRANSFORMS:
        target = root / relative
        original = target.read_text(encoding="utf-8")
        patched = transformer(original)
        changes.append((target, patched))
    if edit:
        for target, patched in changes:
            fd, name = tempfile.mkstemp(dir=target.parent, prefix=".gw-arm-", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as output:
                    output.write(patched)
                os.replace(name, target)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
    result = {"schema": 1, "stage": "P2_real_World_ARM_C_function_adapters",
              "applied": bool(edit), "sources": [p for p, _ in TRANSFORMS],
              "GBA_paths_preserved": True, "new_random_algorithm": False,
              "RFU_multiboot_emulated": False, "gameplay_verified": False}
    Path(report).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--output", default="native-world-arm-functions.json")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    try:
        print(json.dumps(apply(args.world, args.output, args.apply), indent=2))
    except (OSError, ValueError) as exc:
        p.exit(1, "WORLD ARM FUNCTIONS REFUSED: %s\n" % exc)


if __name__ == "__main__":
    main()
