#!/usr/bin/env python3
"""Audit real, hash-matched mGBA Save/Continue and three-region QA on PT-BR ROM.

This does not play a game or fabricate suite verdicts. Only fresh PASS stamps
from the existing real mGBA Lua runs can satisfy the strict World proof parser.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from qa_acceptance import load_suite_proof

ROM_SIZE = 32 * 1024 * 1024

# These are existing Lua suites, generated from the pinned World game test
# harness. A new suite or changed assertion count must be reviewed explicitly.
REQUIRED_SUITES = (
    ("GrandWorldHubParty", 94),
    ("GrandWorldSixRoutes", 167),
    ("GrandWorldHeroSave", 37),
    ("GrandWorldSaveBrendan", 38),
    ("GrandWorldSaveMay", 38),
    ("GrandWorldSaveRed", 38),
    ("GrandWorldSaveLeaf", 38),
    ("GrandWorldSaveEthan", 38),
    ("GrandWorldSaveLyra", 38),
    ("GrandWorldCrossRegionSave", 176),
)


def audit(world):
    world = Path(world)
    rom = (world / "pokemonworld.gba").read_bytes()
    if len(rom) != ROM_SIZE or rom[0xAC:0xB0] != b"BPEE" or rom[0xB2] != 0x96:
        raise ValueError("not the complete 32 MiB World GBA cartridge")
    if (sum(rom[0xA0:0xBD]) + rom[0xBD] + 0x19) % 256:
        raise ValueError("invalid GBA header complement checksum")

    sha256 = hashlib.sha256(rom).hexdigest()
    md5 = hashlib.md5(rom).hexdigest().upper()
    suites = []
    for name, expected in REQUIRED_SUITES:
        # required=True rejects missing PASS, conflicting FAIL, wrong check
        # totals, corrupt stamps, and stamps from a different compiled ROM.
        proof = load_suite_proof(world, name, md5, expected, required=True)
        suites.append(proof)

    return {
        "schema": 1,
        "target": "PTBR_GBA_ARM_not_PC",
        "rom_sha256": sha256,
        "rom_md5": md5,
        "suite_count": len(suites),
        "expected_assertion_passes": sum(n for _, n in REQUIRED_SUITES),
        "real_mgba_suite_proofs": suites,
        "scope": "staged hero identities and gender, genuine saves/reboots/Continue, carried party, six real hub gate directions",
        "intro_hero_picker_ui_certified": False,
        "all_campaign_events_certified": False,
        "existing_player_save_compatibility_certified": False,
        "manual_gameplay_certified": False,
        "release_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("world", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        proof = audit(args.world)
    except (OSError, ValueError, UnicodeError) as exc:
        sys.exit("PT-BR REAL mGBA PROGRESSION GATE FAILED: " + str(exc))
    args.output.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    print("PT-BR mGBA progression: %d suites, %d/%d assertions, ROM SHA256 %s" %
          (proof["suite_count"], proof["expected_assertion_passes"],
           proof["expected_assertion_passes"], proof["rom_sha256"]))


if __name__ == "__main__":
    main()
