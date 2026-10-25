#!/usr/bin/env python3
"""Compare byte representations of World save-field types on host and ARM GBA.

The host compilation uses the PORTABLE four-byte alignments proven by the
isolated ABI probe; ARM uses the *actual World* -mabi=apcs-gnu convention.
This proves the sample fields' byte encodings, not full SaveBlock migration.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def run(commands, label):
    for argv in commands:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=45)
        if result.returncode:
            raise RuntimeError(label + ": " + result.stderr[:3000])


def compare(source, cc="gcc", arm_cc="arm-none-eabi-gcc",
            objcopy="objcopy", arm_objcopy="arm-none-eabi-objcopy"):
    source = Path(source).resolve()
    if not source.is_file():
        raise ValueError("ABI C test source is missing")
    details = {"stage": "P1_portable_abi_byte_comparison",
               "arm_abi": "apcs-gnu", "native_pointer_bits": 32,
               "matches": {}, "full_save_verified": False}
    with tempfile.TemporaryDirectory(prefix="gw-abi-bytes-") as tmp:
        d = Path(tmp)
        host = d / "host.o"
        arm = d / "arm.o"
        run([
            [cc, "-m32", "-std=c11", "-DPORTABLE", "-c", str(source), "-o", str(host)],
            [arm_cc, "-mthumb", "-mabi=apcs-gnu", "-march=armv4t", "-std=c11",
             "-c", str(source), "-o", str(arm)],
        ], "ABI compilers")
        for section, expected in ((".gw_times", 24), (".gw_dome", 20)):
            native_file, gba_file = d / "host.bin", d / "gba.bin"
            run([
                [objcopy, "--dump-section", section + "=" + str(native_file), str(host)],
                [arm_objcopy, "--dump-section", section + "=" + str(gba_file), str(arm)],
            ], "ABI sections")
            host_bytes = native_file.read_bytes()
            arm_bytes = gba_file.read_bytes()
            details["matches"][section] = {
                "host_bytes": len(host_bytes), "arm_bytes": len(arm_bytes),
                "exact_match": host_bytes == arm_bytes,
                "expected_bytes": expected,
            }
            if len(host_bytes) != expected or len(arm_bytes) != expected or host_bytes != arm_bytes:
                raise RuntimeError(section + ": native/ARM save field bytes do not match")
    details["sample_field_encodings_match"] = True
    return details


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", default="tools/grandworld_native/tests/abi_bytes.c")
    p.add_argument("--report", default="native-abi-bitfield-report.json")
    args = p.parse_args()
    result = compare(args.source)
    Path(args.report).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
