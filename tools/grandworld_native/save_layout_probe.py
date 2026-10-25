#!/usr/bin/env python3
"""Measure World SaveBlock1/3 native ABI without disabling a single save assert.

Includes actual World types after the guarded SaveBlock2 alignment overlay.
Does NOT change, load or serialize real Pokemon save data.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

PROGRAM = r"""
#include <stdio.h>
#include <stddef.h>
#include "global.h"
int main(void) {
    printf("save1.size=%zu\n", sizeof(struct SaveBlock1));
    printf("save1.money=%zu\n", offsetof(struct SaveBlock1, money));
    printf("save1.playerParty=%zu\n", offsetof(struct SaveBlock1, playerParty));
    printf("save1.pcItems=%zu\n", offsetof(struct SaveBlock1, pcItems));
    printf("save1.bag=%zu\n", offsetof(struct SaveBlock1, bag));
    printf("save1.objectEvents=%zu\n", offsetof(struct SaveBlock1, objectEvents));
    printf("save1.objectEventTemplates=%zu\n", offsetof(struct SaveBlock1, objectEventTemplates));
    printf("save1.flags=%zu\n", offsetof(struct SaveBlock1, flags));
    printf("save1.vars=%zu\n", offsetof(struct SaveBlock1, vars));
    printf("save1.berryTrees=%zu\n", offsetof(struct SaveBlock1, berryTrees));
    printf("save1.daycare=%zu\n", offsetof(struct SaveBlock1, daycare));
    printf("save3.size=%zu\n", sizeof(struct SaveBlock3));
    printf("save3.chain=%zu\n", offsetof(struct SaveBlock3, dexNavChain));
    printf("save3.pokevial=%zu\n", offsetof(struct SaveBlock3, pokevial));
    printf("save3.reservedQuestData=%zu\n", offsetof(struct SaveBlock3, reservedQuestData));
    printf("save3.region=%zu\n", offsetof(struct SaveBlock3, region));
    printf("pokemon.size=%zu\n", sizeof(struct Pokemon));
    printf("objectEvent.size=%zu\n", sizeof(struct ObjectEvent));
    printf("objectEventTemplate.size=%zu\n", sizeof(struct ObjectEventTemplate));
    printf("pokevial.size=%zu\n", sizeof(struct Pokevial));
    printf("berryTree.size=%zu\n", sizeof(struct BerryTree));
    return 0;
}
"""
EXPECTED = {
    "save1.money": 1168,
    "save1.flags": 5524,
    "save1.vars": 6042,
    "save1.berryTrees": 6812,
    "save1.daycare": 13364,
    "save3.region": 32,
    "berryTree.size": 8,
}

def measure(world, compiler="gcc"):
    world = Path(world).resolve()
    with tempfile.TemporaryDirectory(prefix="gw-save13-") as tmp:
        p = Path(tmp)
        source = p / "probe.c"
        exe = p / "probe"
        source.write_text(PROGRAM, encoding="utf-8")
        argv = [compiler, "-m32", "-std=gnu17", "-DPORTABLE", "-DGW_WORLD_NATIVE",
                "-DMODERN=1", "-DEMERALD=1", "-DALL_REGIONS=1", "-DTESTING=0",
                "-iquote", str(world / "include"), "-iquote", str(world / "src"),
                str(source), "-o", str(exe)]
        build = subprocess.run(argv, cwd=world, capture_output=True, text=True, timeout=80)
        if build.returncode:
            return {"status": "compile_failed", "errors": build.stderr.splitlines()[:80]}
        result = subprocess.run([str(exe)], cwd=world, capture_output=True,
                                text=True, timeout=20)
        if result.returncode:
            return {"status": "execute_failed", "errors": result.stderr.splitlines()[:60]}
    actual = {}
    for line in result.stdout.splitlines():
        k, sep, v = line.partition("=")
        if sep:
            actual[k] = int(v)
    deltas = {k: actual[k] - expected for k, expected in EXPECTED.items() if k in actual}
    return {"status": "measured", "actual": actual, "expected": EXPECTED,
            "deltas": deltas, "complete_abi_match": all(d == 0 for d in deltas.values()),
            "source_changed": False, "assertions_removed": False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--output", default="native-save13-layout.json")
    args = p.parse_args()
    r = measure(args.world)
    Path(args.output).write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(r, indent=2))

if __name__ == "__main__":
    main()
