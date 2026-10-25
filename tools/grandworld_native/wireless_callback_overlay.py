#!/usr/bin/env python3
"""Port three ARM callback tail-jumps, not GBA wireless hardware.

The original GBA librfu_intr.c uses naked ARM bx r2/r1/r0 trampolines to call
handlers with the existing argument registers. A native host cannot assemble
these ARM instructions. This exact-anchor overlay substitutes ordinary C
callback invocation only under GW_WORLD_NATIVE; the ARM bodies stay intact.
This does not implement an RFU device or promise wireless multiplayer.
Only run in a disposable, pre-validated World source checkout.
"""
import argparse
import json
import os
from pathlib import Path
import tempfile

ORIGINAL = """NAKED
#if __STDC_VERSION__ < 202311L
static void Callback_Dummy_M(int reqCommandId, int error, void (*callbackM)())
#else
static void Callback_Dummy_M(int reqCommandId, int error, void (*callbackM)(...))
#endif
{
    asm("bx r2");
}

NAKED
static void Callback_Dummy_S(u16 reqCommandId, void (*callbackS)(u16))
{
    asm("bx r1");
}

NAKED
static void Callback_Dummy_ID(void (*callbackId)(void))
{
    asm("bx r0");
}
"""

HOST = """#if defined(GW_WORLD_NATIVE)
/* C calls match the argument registers forwarded by the GBA tail jumps.
 * RFU transport itself remains unavailable until separately implemented. */
#if __STDC_VERSION__ < 202311L
static void Callback_Dummy_M(int reqCommandId, int error, void (*callbackM)())
#else
static void Callback_Dummy_M(int reqCommandId, int error, void (*callbackM)(...))
#endif
{
    if (callbackM != NULL)
        callbackM(reqCommandId, error);
}

static void Callback_Dummy_S(u16 reqCommandId, void (*callbackS)(u16))
{
    if (callbackS != NULL)
        callbackS(reqCommandId);
}

static void Callback_Dummy_ID(void (*callbackId)(void))
{
    if (callbackId != NULL)
        callbackId();
}
#else
""" + ORIGINAL + """#endif
"""


def transform(source):
    if source.count(ORIGINAL) != 1 or "/* C calls match the argument registers" in source:
        raise ValueError("World RFU callback code changed or overlay already applied")
    return source.replace(ORIGINAL, HOST, 1)


def apply(world, report, edit=False):
    root = Path(world).resolve()
    source = root / "src/librfu_intr.c"
    if not source.is_file() or not (root / "src/main.c").is_file():
        raise ValueError("disposable World checkout missing")
    original = source.read_text(encoding="utf-8")
    updated = transform(original)
    if edit:
        fd, name = tempfile.mkstemp(dir=source.parent, prefix=".gw-rfu-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as output:
                output.write(updated)
            os.replace(name, source)
        finally:
            if os.path.exists(name):
                os.unlink(name)
    result = {"schema": 1, "stage": "P2_native_only_RFU_callback_trampolines",
              "applied": bool(edit), "GBA_assembly_preserved": True,
              "GBA_wireless_emulation_supported": False,
              "modified_real_saves": False}
    Path(report).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--output", default="native-rfu-callbacks.json")
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    try:
        print(json.dumps(apply(args.world, args.output, args.apply), indent=2))
    except (ValueError, OSError) as exc:
        p.exit(1, "RFU CALLBACK OVERLAY REFUSED: %s\n" % exc)


if __name__ == "__main__":
    main()
