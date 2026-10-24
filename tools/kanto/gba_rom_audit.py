#!/usr/bin/env python3
"""Inspect built GBA header and cartridge bounds (NOT runtime gameplay QA)."""
import argparse
import hashlib
import json
from pathlib import Path

MAX_GBA_ROM = 32 * 1024 * 1024
# SHA-1 of the standard Nintendo GBA boot-logo field (156 bytes at 0x004).
# Derived from the pinned, checksum-verified Emerald header; no logo bytes here.
OFFICIAL_BOOT_LOGO_SHA1 = "17daa0fec02fc33c0f6abb549a8b80b6613b48ee"


class GbaRomValidationError(ValueError):
    pass


def verify_rom(data, expected_logo_sha1=OFFICIAL_BOOT_LOGO_SHA1):
    if not 0xC0 <= len(data) <= MAX_GBA_ROM:
        raise GbaRomValidationError("ROM length outside GBA bounds")
    if len(data) % 4:
        raise GbaRomValidationError("ROM must contain complete ARM words")
    if (int.from_bytes(data[0:4], "little") >> 24) != 0xEA:
        raise GbaRomValidationError("Missing ARM branch at cartridge entry")
    logo = hashlib.sha1(data[4:0xA0]).hexdigest()
    if expected_logo_sha1 is not None and logo != expected_logo_sha1:
        raise GbaRomValidationError("Unexpected GBA boot-logo checksum")
    if data[0xA0:0xAC] != b"POKEMON EMER":
        raise GbaRomValidationError("Unexpected ROM title")
    if data[0xAC:0xB0] != b"BPEE":
        raise GbaRomValidationError("Unexpected Emerald game code")
    if data[0xB0:0xB2] != b"01":
        raise GbaRomValidationError("Unexpected manufacturer code")
    if data[0xB2] != 0x96:
        raise GbaRomValidationError("Invalid GBA fixed header field")
    checksum = (-(sum(data[0xA0:0xBD]) + 0x19)) & 0xFF
    if checksum != data[0xBD]:
        raise GbaRomValidationError("Invalid header complement checksum")
    return {
        "mode": "GBA_HEADER_STATIC_AUDIT_NOT_EMULATOR_QA",
        "rom_size_bytes": len(data),
        "max_rom_bytes": MAX_GBA_ROM,
        "title": "POKEMON EMER",
        "game_code": "BPEE",
        "maker": "01",
        "logo_sha1": logo,
        "header_complement": checksum,
        "sha256": hashlib.sha256(data).hexdigest(),
        "boot_verified": False,
        "gameplay_verified": False,
        "save_reload_verified": False,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rom", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    result = verify_rom(Path(args.rom).read_bytes())
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Validated GBA cartridge header: {result['rom_size_bytes']} bytes, "
          f"SHA256 {result['sha256']}")


if __name__ == "__main__":
    main()
