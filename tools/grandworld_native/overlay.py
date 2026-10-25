#!/usr/bin/env python3
"""Experimental World host-memory header overlay for a disposable checkout.

Applied only AFTER the pinned GBA reference has been built and validated.
This is P1 infrastructure, not a linked game or a working ROM replacement.
"""
import argparse
import json
from pathlib import Path
import os
import tempfile

DEFINES = {
    '#define ARM_FUNC __attribute__((target("arm")))':
      '#ifdef PORTABLE\n#define ARM_FUNC\n#else\n#define ARM_FUNC __attribute__((target("arm")))\n#endif',
    '#define SOUND_INFO_PTR (*(struct SoundInfo **)0x3007FF0)':
      '#ifdef PORTABLE\nextern struct SoundInfo *GW_SOUND_INFO_PTR;\n#define SOUND_INFO_PTR GW_SOUND_INFO_PTR\n#else\n#define SOUND_INFO_PTR (*(struct SoundInfo **)0x3007FF0)\n#endif',
    '#define INTR_CHECK     (*(u16 *)0x3007FF8)':
      '#ifdef PORTABLE\nextern unsigned short GW_INTR_CHECK;\n#define INTR_CHECK GW_INTR_CHECK\n#else\n#define INTR_CHECK     (*(u16 *)0x3007FF8)\n#endif',
    '#define INTR_VECTOR    (*(void **)0x3007FFC)':
      '#ifdef PORTABLE\nextern void *GW_INTR_VECTOR;\n#define INTR_VECTOR GW_INTR_VECTOR\n#else\n#define INTR_VECTOR    (*(void **)0x3007FFC)\n#endif',
    '#define PLTT          0x5000000':
      '#ifdef PORTABLE\nextern unsigned char GW_PLTT[0x400];\n#define PLTT GW_PLTT\n#else\n#define PLTT          0x5000000\n#endif',
    '#define VRAM      0x6000000':
      '#ifdef PORTABLE\nextern unsigned char VRAM_[0x18000];\n#define VRAM ((uintptr_t)VRAM_)\n#else\n#define VRAM      0x6000000\n#endif',
    '#define OAM      0x7000000':
      '#ifdef PORTABLE\nextern unsigned char GW_OAM[0x400];\n#define OAM GW_OAM\n#else\n#define OAM      0x7000000\n#endif',
}
IO = {
    '#define REG_BASE 0x4000000 // I/O register base address':
      '#ifdef PORTABLE\nextern unsigned char GW_REG_BASE[0x400];\n#define REG_BASE ((uintptr_t)GW_REG_BASE)\n#else\n#define REG_BASE 0x4000000 // I/O register base address\n#endif'
}

def replace_exact(src, replacements):
    for before, after in replacements.items():
        if src.count(before) != 1:
            raise ValueError("World header changed or overlay already applied: " + before)
        src = src.replace(before, after)
    return src

def generate(world):
    world = Path(world)
    d = world / 'include/gba/defines.h'
    i = world / 'include/gba/io_reg.h'
    if not d.is_file() or not i.is_file():
        raise RuntimeError("World headers missing")
    return {d: replace_exact(d.read_text(), DEFINES),
            i: replace_exact(i.read_text(), IO)}

def apply(world, report, commit_changes):
    world = Path(world).resolve()
    mapping = generate(world)
    if commit_changes:
        staged = {}
        try:
            for target, data in mapping.items():
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                                 prefix=target.name+".gwtmp-", delete=False) as f:
                    f.write(data)
                    staged[target] = Path(f.name)
            for target, temp in staged.items():
                os.replace(temp, target)
        finally:
            for temp in staged.values():
                temp.unlink(missing_ok=True)
    summary = {"schema": 1, "stage": "P1_portable_headers",
               "applied_to_disposable_source": commit_changes,
               "patched_headers": [str(path.relative_to(world)) for path in mapping],
               "world_gba_untouched": not commit_changes,
               "native_linked": False}
    Path(report).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--report", default="native-overlay-report.json")
    args = p.parse_args()
    try:
        print(json.dumps(apply(args.world, args.report, args.apply), indent=2))
    except (OSError, ValueError, RuntimeError) as exc:
        p.exit(1, "overlay rejected: %s\n" % exc)

if __name__ == "__main__":
    main()
