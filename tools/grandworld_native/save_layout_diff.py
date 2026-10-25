#!/usr/bin/env python3
"""Measure real GBA APCS and x86 save layouts by extracting compiled object constants.
Never edits ROM, save, or source. Uses actual World generated headers.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import tempfile

FIELDS = {
    "SaveBlock1.size": "sizeof(struct SaveBlock1)",
    "SaveBlock1.playerParty": "offsetof(struct SaveBlock1, playerParty)",
    "SaveBlock1.money": "offsetof(struct SaveBlock1, money)",
    "SaveBlock1.pcItems": "offsetof(struct SaveBlock1, pcItems)",
    "SaveBlock1.bag": "offsetof(struct SaveBlock1, bag)",
    "SaveBlock1.flags": "offsetof(struct SaveBlock1, flags)",
    "SaveBlock1.vars": "offsetof(struct SaveBlock1, vars)",
    "SaveBlock1.berryTrees": "offsetof(struct SaveBlock1, berryTrees)",
    "SaveBlock1.secretBases": "offsetof(struct SaveBlock1, secretBases)",
    "SaveBlock1.playerRoomDecorations": "offsetof(struct SaveBlock1, playerRoomDecorations)",
    "SaveBlock1.tvShows": "offsetof(struct SaveBlock1, tvShows)",
    "SaveBlock1.pokeNews": "offsetof(struct SaveBlock1, pokeNews)",
    "SaveBlock1.mail": "offsetof(struct SaveBlock1, mail)",
    "SaveBlock1.oldMan": "offsetof(struct SaveBlock1, oldMan)",
    "SaveBlock1.dewfordTrends": "offsetof(struct SaveBlock1, dewfordTrends)",
    "SaveBlock1.contestWinners": "offsetof(struct SaveBlock1, contestWinners)",
    "SaveBlock1.daycare": "offsetof(struct SaveBlock1, daycare)",
    "SecretBase.size": "sizeof(struct SecretBase)",
    "SecretBaseParty.size": "sizeof(struct SecretBaseParty)",
    "ContestWinner.size": "sizeof(struct ContestWinner)",
    "DayCare.size": "sizeof(struct DayCare)",
    "Pokevial.size": "sizeof(struct Pokevial)",
    "SaveBlock3.reservedQuestData": "offsetof(struct SaveBlock3, reservedQuestData)",
    "SaveBlock2.size": "sizeof(struct SaveBlock2)",
    "SaveBlock2.followerSlot": "offsetof(struct SaveBlock2, followerSlot)",
    "SaveBlock3.size": "sizeof(struct SaveBlock3)",
    "SaveBlock3.region": "offsetof(struct SaveBlock3, region)",
    "RegionSave.size": "sizeof(struct RegionSave)",
    "WarpData.size": "sizeof(struct WarpData)",
    "BerryTree.size": "sizeof(struct BerryTree)",
    "DaycareMon.size": "sizeof(struct DaycareMon)",
    "ObjectEvent.size": "sizeof(struct ObjectEvent)",
    "Pokemon.size": "sizeof(struct Pokemon)",
}

def measure(world):
    world = Path(world).resolve()
    if not (world / "include/global.h").is_file():
        raise ValueError("World checkout missing")
    source = '#include "global.h"\n#include <stddef.h>\n'
    source += 'const unsigned int gw_save_layout[] __attribute__((used, section(".gw_save_layout"))) = {\n'
    source += ",\n".join("    (unsigned int)(" + x + ")" for x in FIELDS.values())
    source += "\n};\n"
    values = {}
    with tempfile.TemporaryDirectory(prefix="gw-save-layout-") as temporary:
        root = Path(temporary)
        input_file = root / "save_layout.c"
        input_file.write_text(source, encoding="utf-8")
        for name, compiler, converter in (
            ("gba_arm_apcs", ["arm-none-eabi-gcc", "-mthumb", "-march=armv4t", "-mabi=apcs-gnu"], "arm-none-eabi-objcopy"),
            ("host_i386", ["gcc", "-m32", "-DPORTABLE=1", "-DGW_WORLD_NATIVE=1"], "objcopy"),
        ):
            obj = root / (name + ".o")
            raw = root / (name + ".bin")
            cmd = [*compiler, "-std=gnu17", "-DMODERN=1", "-DEMERALD=1", "-DALL_REGIONS=1",
                   "-DTESTING=0", "-iquote", str(world / "include"), "-c",
                   str(input_file), "-o", str(obj)]
            result = subprocess.run(cmd, cwd=world, capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise RuntimeError(name + ": " + result.stderr[:2500])
            result = subprocess.run([converter, "--dump-section", ".gw_save_layout=" + str(raw), str(obj)],
                                    cwd=world, capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise RuntimeError(name + " objcopy: " + result.stderr[:1000])
            binary = raw.read_bytes()
            if len(binary) != 4 * len(FIELDS):
                raise ValueError("unexpected exported ABI byte count")
            values[name] = dict(zip(FIELDS, struct.unpack("<" + "I" * len(FIELDS), binary)))
    changes = {key: {"gba": values["gba_arm_apcs"][key], "host": values["host_i386"][key],
                     "delta": values["host_i386"][key] - values["gba_arm_apcs"][key]}
               for key in FIELDS if values["gba_arm_apcs"][key] != values["host_i386"][key]}
    return {"schema": 1, "stage": "P2_verified_save_layout_differences",
            "sources_unchanged": True, "assertions_disabled": False,
            "measurements": values, "differences": changes,
            "all_equal": not changes, "full_save_tested": False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", required=True)
    parser.add_argument("--output", default="native-save-layout.json")
    args = parser.parse_args()
    result = measure(args.world)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["differences"], indent=2))

if __name__ == "__main__":
    main()
