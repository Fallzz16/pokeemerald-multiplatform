#!/usr/bin/env python3
"""Fail-closed audit of the authentic linked ARM/GBA ELF and cartridge ROM.

This is for the original World/M8 GBA pipeline, NOT the x86/SDL2 native
port. It never edits the ROM, player saves, or original World sources.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess

ROM_SIZE = 32 * 1024 * 1024
ROM_START = 0x08000000
ROM_END = ROM_START + ROM_SIZE
REQUIRED_BOOT_SYMBOLS = ("Start", "Init", "AgbMain")
NATIVE_ONLY_DIAGNOSTIC_SYMBOLS = (
    "VBlankIntrWait", "SoftReset", "BitUnPack", "Div", "TrackStop",
    "gNumMusicPlayers", "GameCubeMultiBoot_Main", "ply_fine",
)


class AuditError(ValueError):
    """Invalid or incomplete genuine GBA link evidence."""


def _sha256(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def parse_nm_posix(output):
    """Parse arm-none-eabi-nm -P for a single final ELF, rejecting junk."""
    symbols = []
    for lineno, line in enumerate(output.splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 2 or len(parts[1]) != 1:
            raise AuditError("unexpected nm POSIX output on line %d" % lineno)
        symbols.append((parts[0], parts[1], parts[2:] if len(parts) > 2 else []))
    return symbols


def inspect_elf_header(elf):
    with Path(elf).open("rb") as handle:
        header = handle.read(52)
    if len(header) < 52 or header[:4] != b"\x7fELF":
        raise AuditError("linked ELF missing or not ELF")
    if header[4] != 1 or header[5] != 1:
        raise AuditError("expected 32-bit LITTLE ENDIAN ARM ELF, not a PC executable")
    elf_type, machine = struct.unpack_from("<HH", header, 16)
    entry = struct.unpack_from("<I", header, 24)[0]
    if elf_type != 2 or machine != 40:
        raise AuditError("expected executable ARM ELF, not relocatable or x86")
    if not ROM_START <= (entry & ~1) < ROM_END:
        raise AuditError("ARM entry point not inside GBA cartridge ROM mapping")
    return entry


def inspect_rom(rom):
    rom = Path(rom)
    if rom.stat().st_size != ROM_SIZE:
        raise AuditError("GBA ROM must be exactly 32 MiB")
    with rom.open("rb") as handle:
        header = handle.read(0xC0)
    if header[0xAC:0xB0] != b"BPEE" or header[0xB2] != 0x96:
        raise AuditError("unexpected World GBA game code or fixed header byte")
    if (sum(header[0xA0:0xBD]) + header[0xBD] + 0x19) % 256:
        raise AuditError("invalid official GBA complement checksum")
    return header[0xA0:0xAC].rstrip(b"\x00").decode("ascii", errors="replace")


def analyze(elf, rom, defined_output, undefined_output):
    """Cross-check the ARM entry, real symbols, and actual GBA ROM header."""
    elf = Path(elf)
    rom = Path(rom)
    entry = inspect_elf_header(elf)
    title = inspect_rom(rom)
    defined = {}
    for name, kind, rest in parse_nm_posix(defined_output):
        if kind.upper() != "U":
            defined[name] = (kind, rest)
    unresolved = [name for name, kind, _ in parse_nm_posix(undefined_output)
                  if kind.upper() == "U"]
    weak = [name for name, kind, _ in parse_nm_posix(undefined_output)
            if kind in ("w", "v")]
    if unresolved:
        raise AuditError("unresolved STRONG ARM symbols: %s" % ", ".join(unresolved[:15]))
    missing = sorted(set(REQUIRED_BOOT_SYMBOLS) - defined.keys())
    if missing:
        raise AuditError("missing authentic GBA boot symbols: %s" % ", ".join(missing))
    start_address = defined["Start"][1]
    if not start_address:
        raise AuditError("GBA Start symbol has no ARM address")
    try:
        start = int(start_address[0], 16)
    except ValueError as exc:
        raise AuditError("invalid GBA Start symbol address") from exc
    if (start & ~1) != (entry & ~1):
        raise AuditError("GBA ELF entry point does not match Start label")
    return {
        "schema": 1,
        "target": "GBA_ARM7TDMI_not_x86",
        "verified": True,
        "machine": "ELF32 ARM little-endian executable",
        "elf_entry": "0x%08X" % entry,
        "rom_bytes": ROM_SIZE,
        "rom_title": title,
        "gba_game_code": "BPEE",
        "gba_header_checksum_valid": True,
        "required_boot_symbols_found": list(REQUIRED_BOOT_SYMBOLS),
        "defined_symbol_count": len(defined),
        "undefined_strong_symbol_count": 0,
        "optional_undefined_weak_symbols": sorted(set(weak))[:50],
        "previously_native_unresolved_symbols_found_in_gba": sorted(
            set(NATIVE_ONLY_DIAGNOSTIC_SYMBOLS) & defined.keys()),
        "elf_sha256": _sha256(elf),
        "rom_sha256": _sha256(rom),
        "original_rom_modified": False,
        "player_saves_accessed": False,
        "gba_boot_or_gameplay_verified_by_this_audit": False,
        "note": "This validates ARM link + GBA container, not emulator gameplay; x86 unresolved symbols are unrelated.",
    }


def collect(elf, rom, nm="arm-none-eabi-nm"):
    resolved = shutil.which(nm)
    if resolved is None:
        raise AuditError("real ARM nm toolchain missing: %s" % nm)
    outputs = []
    for flag in ("--defined-only", "--undefined-only"):
        try:
            run = subprocess.run([resolved, "--format=posix", flag, str(elf)],
                                 text=True, capture_output=True, timeout=90)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AuditError("ARM nm execution failed: %s" % exc) from exc
        if run.returncode:
            raise AuditError("ARM nm failed (%s): %s" % (flag, run.stderr[-700:]))
        outputs.append(run.stdout)
    return analyze(elf, rom, *outputs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", required=True)
    parser.add_argument("--rom", required=True)
    parser.add_argument("--output", default="gba-arm-link-audit.json")
    parser.add_argument("--nm", default="arm-none-eabi-nm")
    args = parser.parse_args()
    try:
        result = collect(args.elf, args.rom, args.nm)
    except (AuditError, OSError) as exc:
        result = {"schema": 1, "target": "GBA_ARM7TDMI_not_x86", "verified": False,
                  "error": str(exc), "original_rom_modified": False}
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
