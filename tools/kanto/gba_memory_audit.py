#!/usr/bin/env python3
"""Inspect GBA object .bss/.common symbol sizes; never inspect player saves.

This report is advisory, not a substitute for GNU ld region placement. Linker
alignment and archive BSS can affect actual IWRAM use.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

SYMBOL = re.compile(r"^(.*?):\s*(\d+)\s+(\d+)\s+([BbCc])\s+(\S+)\s*$")


def parse_nm(output):
    entries = []
    for line in output.splitlines():
        match = SYMBOL.match(line)
        if not match:
            continue
        path, address, size, kind, name = match.groups()
        size = int(size)
        if size <= 0:
            continue
        entries.append({"object": path, "symbol": name, "bytes": size,
                        "kind": kind.upper()})
    return entries


def inspect(objdir, binary):
    files = sorted(Path(objdir).rglob("*.o"))
    results = []
    for index in range(0, len(files), 100):
        chunk = files[index:index + 100]
        proc = subprocess.run(
            [binary, "-S", "--radix=d", "--print-file-name",
             "--defined-only", *map(str, chunk)],
            check=True, capture_output=True, text=True, timeout=35)
        results.extend(parse_nm(proc.stdout))
    results.sort(key=lambda row: row["bytes"], reverse=True)
    return {
        "mode": "ADVISORY_ARM_BSS_SYMBOL_SIZES_NOT_LINKER_MEMORY_MAP",
        "objects_scanned": len(files),
        "sum_bss_and_common_symbol_bytes": sum(row["bytes"] for row in results),
        "largest": results[:60],
        "note": "Excludes ARM archives and padding; use ld output for exact IWRAM/ROM sizes.",
    }


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--objdir", required=True)
    cli.add_argument("--output", required=True)
    cli.add_argument("--nm", default="arm-none-eabi-nm")
    args = cli.parse_args()
    report = inspect(args.objdir, args.nm)
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"BSS candidates: {report['objects_scanned']} objects, "
          f"{report['sum_bss_and_common_symbol_bytes']} symbol bytes")
    for row in report["largest"][:15]:
        print(f"{row['bytes']:>9} B  {row['symbol']}  {row['object']}")


if __name__ == "__main__":
    main()
