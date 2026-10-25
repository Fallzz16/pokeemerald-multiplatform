#!/usr/bin/env python3
"""Investigate World save ABI differences using an isolated C probe.

Never patches the real World source or removes production assertions.
Only a temporary copy of global.h skips ONE size assertion so the diagnostic
can print native struct sizes. A matching size alone does NOT prove save safety.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import textwrap

ASSERTION = "STATIC_ASSERT(sizeof(struct SaveBlock2) == 0xF2C, SaveBlock2SizeUnchanged);"

PROGRAM = r"""
#include <stdio.h>
#include <stddef.h>
#include "global.h"
int main(void) {
    printf("saveblock2=%zu\n", sizeof(struct SaveBlock2));
    printf("saveblock2.frontier=%zu\n", offsetof(struct SaveBlock2, frontier));
    printf("saveblock2.playerName=%zu\n", offsetof(struct SaveBlock2, playerName));
    printf("saveblock2.pokedex=%zu\n", offsetof(struct SaveBlock2, pokedex));
    printf("saveblock2.apprentices=%zu\n", offsetof(struct SaveBlock2, apprentices));
    printf("saveblock2.hallRecords1P=%zu\n", offsetof(struct SaveBlock2, hallRecords1P));
    printf("saveblock2.playerApprentice=%zu\n", offsetof(struct SaveBlock2, playerApprentice));
    printf("saveblock2.berryCrush=%zu\n", offsetof(struct SaveBlock2, berryCrush));
    printf("saveblock2.hallRecords2P=%zu\n", offsetof(struct SaveBlock2, hallRecords2P));
    printf("saveblock2.contestLinkResults=%zu\n", offsetof(struct SaveBlock2, contestLinkResults));
    printf("frontier.bytes=%zu\n", sizeof(struct BattleFrontier));
    printf("frontier.towerRecords=%zu\n", offsetof(struct BattleFrontier, towerRecords));
    printf("frontier.towerInterview=%zu\n", offsetof(struct BattleFrontier, towerInterview));
    printf("frontier.challengeStatus=%zu\n", offsetof(struct BattleFrontier, challengeStatus));
    printf("frontier.domeTrainers=%zu\n", offsetof(struct BattleFrontier, domeTrainers));
    printf("frontier.rentalMons=%zu\n", offsetof(struct BattleFrontier, rentalMons));
    printf("frontier.battlePoints=%zu\n", offsetof(struct BattleFrontier, battlePoints));
    printf("towerRecord.bytes=%zu\n", sizeof(struct EmeraldBattleTowerRecord));
    printf("towerPokemon.bytes=%zu\n", sizeof(struct BattleTowerPokemon));
    printf("towerInterview.bytes=%zu\n", sizeof(struct BattleTowerInterview));
    return 0;
}
"""

def diagnose(world, compiler):
    world = Path(world).resolve()
    header = world / "include/global.h"
    text = header.read_text(encoding="utf-8")
    if text.count(ASSERTION) != 1:
        raise ValueError("expected GBA save layout assertion not found")
    text = text.replace(ASSERTION, "#ifndef GW_ABI_DIAGNOSTIC\n" + ASSERTION + "\n#endif")
    configurations = [
        ("gcc32", []),
        ("gcc32-short-enums", ["-fshort-enums"]),
        ("gcc32-packed-2", ["-fpack-struct=2"]),
        ("gcc32-packed-1", ["-fpack-struct=1"]),
        ("gcc32-ms-bitfields", ["-mms-bitfields"]),
    ]
    result = {"stage": "P1_save_abi_diagnostic", "expected_bytes": 0xF2C,
              "production_save_assertion_changed": False, "profiles": []}
    with tempfile.TemporaryDirectory(prefix="gw-abi-") as tmp:
        d = Path(tmp)
        (d / "global.h").write_text(text, encoding="utf-8")
        (d / "abi_size.c").write_text(PROGRAM, encoding="utf-8")
        for name, flags in configurations:
            exe = d / (name + ".bin")
            command = [compiler, "-m32", "-std=gnu99", "-DPORTABLE", "-DMODERN=1",
                       "-DALL_REGIONS=1", "-DGW_ABI_DIAGNOSTIC=1",
                       *flags, "-iquote", str(d),
                       "-iquote", str(world / "include"),
                       "-iquote", str(world / "src"),
                       str(d / "abi_size.c"), "-o", str(exe)]
            proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, timeout=45)
            item = {"profile": name, "compile_success": proc.returncode == 0,
                    "compiler_errors": proc.stderr.splitlines()[:25]}
            if proc.returncode == 0:
                run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=20)
                item["ran"] = run.returncode == 0
                item["observed"] = run.stdout.splitlines()
                if item["ran"]:
                    measurements = {}
                    for entry in item["observed"]:
                        key, sep, value = entry.partition("=")
                        if sep and value.isdigit():
                            measurements[key] = int(value)
                    item["values"] = measurements
                    expected = {
                        "saveblock2": 0xF2C,
                        "saveblock2.playerName": 0,
                        "saveblock2.pokedex": 0x18,
                        "saveblock2.playerApprentice": 0xB0,
                        "saveblock2.apprentices": 0xDC,
                        "saveblock2.berryCrush": 0x1EC,
                        "saveblock2.hallRecords1P": 0x21C,
                        "saveblock2.hallRecords2P": 0x57C,
                        "saveblock2.contestLinkResults": 0x624,
                        "saveblock2.frontier": 0x64C,
                        "frontier.bytes": 0x8E0,
                        "frontier.towerRecords": 0x738 - 0x64C,
                        "frontier.towerInterview": 0xBEB - 0x64C,
                        "frontier.challengeStatus": 0xCA8 - 0x64C,
                        "frontier.domeTrainers": 0xD24 - 0x64C,
                        "frontier.rentalMons": 0xE70 - 0x64C,
                        "frontier.battlePoints": 0xEB8 - 0x64C,
                        "towerRecord.bytes": 0xEC,
                    }
                    item["layout_deltas"] = {
                        key: observed - expected[key]
                        for key, observed in measurements.items() if key in expected
                    }

            result["profiles"].append(item)
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--compiler", default="gcc")
    p.add_argument("--output", default="native-abi-report.json")
    args = p.parse_args()
    data = diagnose(args.world, args.compiler)
    Path(args.output).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()
