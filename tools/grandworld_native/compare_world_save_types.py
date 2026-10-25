#!/usr/bin/env python3
"""Compare actual World save ABI between GBA ARM APCS and host GCC i386.

Compile const offsetof/sizeof/alignof tuples into dedicated ELF sections.
The real ARM compiler supplies reference values; don't infer offsets or
change production assertions. Run only on disposable generated World trees.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import tempfile

FIELDS = [
    ("sizeof SaveBlock1", "sizeof(struct SaveBlock1)"),
    ("SaveBlock1.money", "offsetof(struct SaveBlock1, money)"),
    ("SaveBlock1.pcItems", "offsetof(struct SaveBlock1, pcItems)"),
    ("SaveBlock1.bag", "offsetof(struct SaveBlock1, bag)"),
    ("SaveBlock1.pokeblocks", "offsetof(struct SaveBlock1, pokeblocks)"),
    ("SaveBlock1.berryBlenderRecords", "offsetof(struct SaveBlock1, berryBlenderRecords)"),
    ("SaveBlock1.objectEvents", "offsetof(struct SaveBlock1, objectEvents)"),
    ("SaveBlock1.objectEventTemplates", "offsetof(struct SaveBlock1, objectEventTemplates)"),
    ("SaveBlock1.flags", "offsetof(struct SaveBlock1, flags)"),
    ("SaveBlock1.vars", "offsetof(struct SaveBlock1, vars)"),
    ("SaveBlock1.berryTrees", "offsetof(struct SaveBlock1, berryTrees)"),
    ("SaveBlock1.secretBases", "offsetof(struct SaveBlock1, secretBases)"),
    ("SaveBlock1.tvShows", "offsetof(struct SaveBlock1, tvShows)"),
    ("SaveBlock1.mail", "offsetof(struct SaveBlock1, mail)"),
    ("SaveBlock1.oldMan", "offsetof(struct SaveBlock1, oldMan)"),
    ("SaveBlock1.contestWinners", "offsetof(struct SaveBlock1, contestWinners)"),
    ("SaveBlock1.daycare", "offsetof(struct SaveBlock1, daycare)"),
    ("sizeof SaveBlock3", "sizeof(struct SaveBlock3)"),
    ("SaveBlock3.region", "offsetof(struct SaveBlock3, region)"),
    ("sizeof RegionSave", "sizeof(struct RegionSave)"),
    ("alignof RegionSave", "__alignof__(struct RegionSave)"),
    ("sizeof ItemSlot", "sizeof(struct ItemSlot)"),
    ("alignof ItemSlot", "__alignof__(struct ItemSlot)"),
    ("sizeof Pokeblock", "sizeof(struct Pokeblock)"),
    ("alignof Pokeblock", "__alignof__(struct Pokeblock)"),
    ("sizeof ObjectEvent", "sizeof(struct ObjectEvent)"),
    ("alignof ObjectEvent", "__alignof__(struct ObjectEvent)"),
    ("sizeof ObjectEventTemplate", "sizeof(struct ObjectEventTemplate)"),
    ("alignof ObjectEventTemplate", "__alignof__(struct ObjectEventTemplate)"),
    ("sizeof TVShow", "sizeof(TVShow)"),
    ("alignof TVShow", "__alignof__(TVShow)"),
    ("sizeof DaycareMon", "sizeof(struct DaycareMon)"),
    ("alignof DaycareMon", "__alignof__(struct DaycareMon)"),
    ("sizeof DayCare", "sizeof(struct DayCare)"),
    ("alignof DayCare", "__alignof__(struct DayCare)"),
    ("sizeof BerryTree", "sizeof(struct BerryTree)"),
    ("sizeof SaveBlock2", "sizeof(struct SaveBlock2)"),
]
PREFIX = "#include <stddef.h>\n#include <stdint.h>\n#include \"global.h\"\n"
def _run(argv, cwd):
    x = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=90)
    if x.returncode:
        raise RuntimeError((" ".join(argv[:4])) + ": " + x.stderr[:5500])

def read_profile(world, directory, is_arm):
    source = directory / "save_layout_values.c"
    output = directory / ("arm.o" if is_arm else "host.o")
    file = directory / ("gba.bin" if is_arm else "host.bin")
    lines = [PREFIX,
             'const uint32_t gw_layout_probe[] __attribute__((used, section(".gw_layout_probe"))) = {']
    lines += ["    (uint32_t)(" + expr + ")," for _, expr in FIELDS]
    lines += ["};", ""]
    source.write_text("\n".join(lines), encoding="utf-8")
    defs = ["-std=gnu17", "-DMODERN=1", "-DEMERALD=1", "-DALL_REGIONS=1", "-DTESTING=0",
            "-iquote", str(world / "include"), "-iquote", str(world / "src")]
    if is_arm:
        cc = ["arm-none-eabi-gcc", "-mthumb", "-mabi=apcs-gnu", "-march=armv4t"]
        objcopy = "arm-none-eabi-objcopy"
    else:
        cc = ["gcc", "-m32", "-DPORTABLE=1", "-DGW_WORLD_NATIVE=1"]
        objcopy = "objcopy"
    _run(cc + defs + ["-c", str(source), "-o", str(output)], world)
    _run([objcopy, "--dump-section", ".gw_layout_probe=" + str(file), str(output)], world)
    data = file.read_bytes()
    if len(data) != 4 * len(FIELDS):
        raise RuntimeError("unexpected binary section length " + str(len(data)))
    return dict(zip([name for name, _ in FIELDS],
                    struct.unpack("<" + "I" * len(FIELDS), data)))

def compare(world):
    world = Path(world).resolve()
    with tempfile.TemporaryDirectory(prefix="gw-abi-save13-") as d:
        directory = Path(d)
        gba = read_profile(world, directory, True)
        host = read_profile(world, directory, False)
    delta = {k: host[k] - gba[k] for k in gba if host[k] != gba[k]}
    return {"schema":1, "stage":"P2_World_ARM_GBA_vs_native_SaveBlock1_3",
            "gba":gba, "native":host, "differences":delta,
            "matching_fields":len(FIELDS)-len(delta),
            "total_fields":len(FIELDS),
            "save_data_modified":False,
            "assertions_removed":False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--output", default="native-save-abi-dual.json")
    args = p.parse_args()
    try:
        data = compare(args.world)
    except (OSError, ValueError, RuntimeError) as exc:
        p.exit(1, "SAVE ABI DUAL COMPILER PROBE FAILED: %s\n" % exc)
    Path(args.output).write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"total_fields":data["total_fields"],
                      "matching_fields":data["matching_fields"],
                      "differences":data["differences"]}, indent=2))

if __name__ == "__main__":
    main()
