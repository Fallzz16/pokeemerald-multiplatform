#!/usr/bin/env python3
"""Fail-closed ROM-bound mGBA gameplay evidence for the PT-BR M8 cartridge.

Unlike the standard 51 World suites, these cases cover the integrated M8
regions, persisted hero identities, real Save/reboot/Continue and carried
Pokemon. They do NOT certify visual avatar selection, all story events,
battle balance or a release-ready game.

No GBA ROM or player save is modified or distributed by this tool.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from audit_gba_arm_link import inspect_rom
from qa_acceptance import load_suite_proof

SUITES = (
    ("CatchTutorial", 15),
    ("GrandWorldHubParty", 94),
    ("GrandWorldSixRoutes", 167),
    ("GrandWorldHeroSave", 37),
    ("GrandWorldSaveBrendan", 38),
    ("GrandWorldSaveMay", 38),
    ("GrandWorldSaveRed", 38),
    ("GrandWorldSaveLeaf", 38),
    ("GrandWorldSaveEthan", 38),
    ("GrandWorldSaveLyra", 38),
    ("SSAquaKantoCrossing", 94),
    ("GrandWorldCrossRegionSave", 176),
    ("GrandWorldOamBudget", 2),
)


def verify_stamps(world, rom_md5):
    """Reject missing, failed, incomplete, stale or wrong-ROM mGBA verdicts."""
    if len({name for name, _ in SUITES}) != len(SUITES):
        raise ValueError("duplicate required M8 gameplay suite")
    proofs = []
    for suite, checks in SUITES:
        proof = load_suite_proof(world, suite, rom_md5, checks, required=True)
        if proof is None:  # Keep strict if upstream verifier changes behavior.
            raise ValueError("required mGBA suite not verified: " + suite)
        proofs.append(proof)
    return proofs


def audit(rom, world):
    # This reuses the existing GBA header/checksum/size gate.
    inspect_rom(rom)
    sha = hashlib.sha256()
    md5 = hashlib.md5()
    with rom.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
            md5.update(block)
    proofs = verify_stamps(world, md5.hexdigest().upper())
    return {
        "schema": 1,
        "target": "real_ptbr_gba_mgba_m8",
        "rom_sha256": sha.hexdigest(),
        "rom_md5": md5.hexdigest().upper(),
        "required_suites": len(SUITES),
        "verified_suites": len(proofs),
        "verified_checks": sum(p["passed"] for p in proofs),
        "all_required_checks_passed": True,
        "evidence": proofs,
        "hero_picker_ui_verified": False,
        "all_regions_and_story_homologated": False,
        "save_format_modified": False,
        "release_approved": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("world", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.rom, args.world)
    except (ValueError, OSError, UnicodeError) as exc:
        print("PT-BR M8 REAL GAMEPLAY FAIL CLOSED: " + str(exc), file=sys.stderr)
        return 1
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("PT-BR M8 emulator checks: %d/%d suites; %d checks; exact ROM SHA256 %s" % (
        result["verified_suites"], result["required_suites"],
        result["verified_checks"], result["rom_sha256"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
