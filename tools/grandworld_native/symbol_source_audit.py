#!/usr/bin/env python3
"""Map unresolved real M8 C symbols to original non-C source labels.

This diagnostic does not generate assets, definitions, placeholders or stubs.
An occurrence of a source label is only a candidate owner, NOT proof that
the native assembler has produced the symbol or that a game can boot.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

LABEL = re.compile(r"^\s*([A-Za-z_][\w.]*)\s*:(?::)?(?:\s|$)", re.MULTILINE)

def undefined_symbols(obj, nm="nm"):
    run = subprocess.run([nm, "-u", str(obj)], capture_output=True,
                         text=True, timeout=60)
    if run.returncode:
        raise RuntimeError("nm failed: " + run.stderr[:800])
    names = set()
    for line in run.stdout.splitlines():
        cols = line.strip().split()
        if len(cols) >= 2 and cols[-2] in ("U", "w"):
            names.add(cols[-1])
    return names

def scan_sources(world, undefined, max_files=25000):
    world = Path(world).resolve()
    candidates = []
    for prefix, pattern in (("data", "*.s"), ("data", "*.inc"),
                            ("src", "*.s"), ("asm", "*.s"),
                            ("sound", "*.s")):
        base = world / prefix
        if base.is_dir():
            candidates += base.rglob(pattern)
    paths = sorted({p.resolve() for p in candidates
                    if p.is_file() and p.resolve().is_relative_to(world)})
    if len(paths) > max_files:
        raise RuntimeError("source inventory unexpectedly large")
    owners = {}
    for source in paths:
        try:
            text = source.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for symbol in set(LABEL.findall(text)):
            if symbol in undefined:
                owners.setdefault(symbol, []).append(source.relative_to(world).as_posix())
    return {
        "source_files_inspected": len(paths),
        "unresolved_symbols": len(undefined),
        "symbols_with_literal_asm_source_labels": len(owners),
        "symbols_without_literal_asm_source_labels": len(undefined - owners.keys()),
        "sample_candidate_owners": {
            symbol: owners[symbol][:4] for symbol in sorted(owners)[:120]},
        "sample_without_owners": sorted(undefined - owners.keys())[:100],
        "source_owner_lookup_is_heuristic": True,
        "generated_asset_definitions_not_invented": True,
        "native_link_complete": False,
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--world", required=True)
    p.add_argument("--object", required=True,
                   help="actual 32-bit relocatable compiled World/M8 C object")
    p.add_argument("--report", default="native-unresolved-source-audit.json")
    args = p.parse_args()
    data = scan_sources(args.world, undefined_symbols(args.object))
    Path(args.report).write_text(json.dumps(data, indent=2) + "\n",
                                 encoding="utf-8")
    print(json.dumps({key: val for key, val in data.items()
                      if not isinstance(val, (list, dict))}, indent=2))
    print("Candidate owners are evidence to prioritize native assembly, NOT a link.")

if __name__ == "__main__":
    main()
