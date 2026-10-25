#!/usr/bin/env python3
"""Route checked World DMA requests to the C host backend in disposable builds.

Modern World normally writes DMA register addresses directly. In a native
process, that would only update shadow register memory and no transfer would
execute. The portable-only override preserves MODERN alignment assertions and
the original GBA implementation.
"""
import argparse
import json
import os
from pathlib import Path
import tempfile

ANCHOR = "#define DmaSetUnchecked(dmaNum, src, dest, control) \\"
ENDING = "\n\n#if MODERN\n// NOTE: Assumes 16-bit DMAs."

def transform(source):
    start = source.find(ANCHOR)
    if start < 0 or source.count(ANCHOR) != 1:
        raise ValueError("World DmaSetUnchecked macro changed")
    end = source.find(ENDING, start)
    if end < 0:
        raise ValueError("World DMA macro section changed")
    original = source[start:end]
    if "dmaRegs[2]" not in original or "REG_ADDR_DMA##dmaNum" not in original:
        raise ValueError("Unexpected World direct DMA macro")
    portable = (
        "#if defined(GW_WORLD_NATIVE)\n"
        "void GwNativeDmaSet(int channel, const volatile void *source, volatile void *dest, u32 control);\n"
        "#define DmaSetUnchecked(dmaNum, src, dest, control) \\\n"
        "    GwNativeDmaSet((dmaNum), (const volatile void *)(uintptr_t)(src), (volatile void *)(uintptr_t)(dest), (control))\n"
        "#else\n" + original + "\n#endif"
    )
    updated = source[:start] + portable + source[end:]
    header_guard = "#define GUARD_GBA_MACRO_H\n"
    if updated.count(header_guard) != 1:
        raise ValueError("World DMA header guard changed")
    # DMA_ENABLE<<16 otherwise promotes signed int 0x8000 and shifts into the
    # sign bit (undefined behavior in C). Native-only unsigned flags preserve
    # the exact hardware value without changing any GBA macro definitions.
    unsigned_enable = (
        header_guard + "\n#if defined(GW_WORLD_NATIVE)\n"
        "#undef DMA_ENABLE\n#define DMA_ENABLE 0x8000u\n#endif\n"
    )
    return updated.replace(header_guard, unsigned_enable, 1)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", default="native-dma-api-overlay.json")
    args = parser.parse_args()
    path = Path(args.world).resolve() / "include/gba/macro.h"
    try:
        before = path.read_text(encoding="utf-8")
        after = transform(before)
        if args.apply:
            fd, tmp = tempfile.mkstemp(prefix=".gw-dma-", dir=path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as file:
                    file.write(after)
                os.replace(tmp, path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
        info = {"schema": 1, "stage": "P1_host_dma_backend",
                "portable_only": True, "applied": args.apply,
                "gba_macro_preserved": True, "game_linked": False}
        Path(args.report).write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(info, indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(1, "DMA OVERLAY REFUSED: %s\n" % exc)

if __name__ == "__main__":
    main()
