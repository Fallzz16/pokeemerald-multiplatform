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
