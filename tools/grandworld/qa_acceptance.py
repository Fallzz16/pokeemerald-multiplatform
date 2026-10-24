#!/usr/bin/env python3
"""Grand World M8: ROM-bound evidence for individually proven release criteria.
No auto-promotion of 24 gyms, three Leagues or save migrations from a ROM build.
Do not distribute original game ROM. Intended for isolated CI checkouts.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

def manifest():
    core=(
        "boot.cold_start boot.new_game boot.continue boot.hard_reset boot.soft_reset boot.no_debug_menu "
        "audio.bgm audio.sfx audio.transitions graphics.tiles graphics.palettes "
        "performance.battle performance.overworld performance.memory "
        "save.two_slots save.interrupted save.world_checksum save.full_boxes save.backup save.cross_region save.migration "
        "difficulty.casual difficulty.classic difficulty.challenge difficulty.box_swap difficulty.champion "
        "dex.capture_and_reload dex.form_evolution dex.disabled_refs dex.storage dex.rom_budget "
        "post.frontier_gate post.world_gate post.reward_once post.legendaries post.red_mt_silver "
        "post.battle_frontier post.world_bracket post.frontier_return"
    ).split()
    region=(
        "new_game avatar story_order no_softlock rival team_persistence "
        "gym01 gym02 gym03 gym04 gym05 gym06 gym07 gym08 "
        "elite01 elite02 elite03 elite04 champion champion_rematch"
    ).split()
    cases=core+[r+"."+suffix for r in ("kanto","johto","hoenn") for suffix in region]
    cases+=["travel."+a+"_to_"+b for a in ("kanto","johto","hoenn") for b in ("kanto","johto","hoenn") if a!=b]
    if len(cases)!=105 or len(set(cases))!=105:
        raise ValueError(f"release manifest drift: {len(cases)}")
    return cases

def load_memory_proof(path, rom_sha256, rom_size):
    """Validate ROM-bound linker evidence, rejecting legacy or malformed records."""
    try:
        proof = json.loads(path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid memory evidence file") from exc
    if not isinstance(proof, dict):
        raise ValueError("invalid memory evidence format")
    if proof.get("sha") != rom_sha256 or type(proof.get("rom_size")) is not int or proof["rom_size"] != rom_size:
        raise ValueError("memory evidence references different ROM")
    limits = {"ROM": 33554432, "EWRAM": 262144, "IWRAM": 32768}
    mem = proof.get("memory")
    if not isinstance(mem, dict) or set(mem) != set(limits) or any(
        type(mem[k]) is not int or mem[k] < 1 or mem[k] > limit for k, limit in limits.items()
    ):
        raise ValueError("invalid hardware memory provenance")
    return mem

def load_suite_proof(world, suite, rom_md5, expected_checks, required=False):
    """Only a complete, ROM-matched headless mGBA PASS certifies a criterion.

    Failed or absent advisory suites stay pending; conflicting or malformed
    results fail closed. An exact check count prevents early-exit false PASSes.
    """
    stamp = world / "_pwtest" / (suite + ".PASS")
    fail = world / "_pwtest" / (suite + ".FAIL")
    if fail.exists():
        if stamp.exists():
            raise ValueError("conflicting mGBA verdict: " + suite)
        if required:
            raise ValueError("required mGBA suite failed: " + suite)
        return None
    if not stamp.is_file():
        if required:
            raise ValueError("required mGBA suite absent: " + suite)
        return None
    try:
        content = stamp.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError("unreadable mGBA verdict: " + suite) from exc
    match = re.fullmatch(
        r"PASS (\d+)/(\d+) rom=([A-F0-9]{32}) at=[^\r\n]+ suite="
        + re.escape(suite) + r"\s*", content
    )
    if not match or match[1] != match[2] or int(match[1]) != expected_checks or match[3] != rom_md5:
        raise ValueError("stale or incomplete mGBA verdict: " + suite)
    return {"source": "headless mGBA Lua", "suite": suite,
            "passed": expected_checks, "rom_md5": rom_md5}


def register_six_route_proofs(seen, proof):
    """Map a complete 167-check same-ROM itinerary to its six directed gates."""
    if proof is None:
        return
    routes = (
        ("hoenn", "kanto"), ("kanto", "johto"), ("johto", "hoenn"),
        ("hoenn", "johto"), ("johto", "kanto"), ("kanto", "hoenn"),
    )
    for origin, dest in routes:
        case = f"travel.{origin}_to_{dest}"
        if case not in manifest():
            raise ValueError("six-route evidence no longer maps to acceptance manifest")
        seen[case] = {
            **proof, "proven_real_gate": f"{origin}_to_{dest}",
            "scope": "physical hub travel and unchanged party, not save/reload",
        }



def load_suite_group_proof(world, rom_md5, case, suite_counts, scope):
    """Promote only if ALL specified, exact-count, same-ROM gameplay suites passed.

    Each suite must have a PASS stamp without a conflicting FAIL. Absent optional
    suites keep the criterion pending; malformed/stale stamps fail closed.
    """
    if case not in manifest():
        raise ValueError("unknown release acceptance criterion: " + case)
    if not suite_counts or len(suite_counts) != len(set(suite_counts)):
        raise ValueError("invalid independent acceptance suite group")
    proofs = []
    for suite, expected_checks in suite_counts:
        proof = load_suite_proof(world, suite, rom_md5, expected_checks)
        if proof is None:
            return None
        proofs.append(proof)
    return {"source": "multiple headless mGBA Lua suites", "scope": scope,
            "rom_md5": rom_md5, "suites": proofs}


def report(world):
    rom=(world/"pokemonworld.gba").read_bytes()
    if hashlib.sha1(rom[0x04:0xA0]).hexdigest() != '17daa0fec02fc33c0f6abb549a8b80b6613b48ee':
        raise ValueError('complete GBA boot logo hash does not match actual cartridge header')
    if len(rom)!=33554432 or rom[0xB2]!=0x96 or rom[0xAC:0xB0]!=b'BPEE':
        raise ValueError("invalid World ROM header or size")
    if (sum(rom[0xA0:0xBD])+rom[0xBD]+0x19)&255:
        raise ValueError("World ROM header checksum mismatch")
    sha=hashlib.sha256(rom).hexdigest()
    md5=hashlib.md5(rom).hexdigest().upper()
    mem = load_memory_proof(world.parent/"m8-integrated-gen4-evidence.json", sha, len(rom))
    seen={"performance.memory":{"source":"ARM linker / SHA256","memory_bytes":mem}}
    # Mandatory fresh-ROM proofs.
    for suite, case, count in [
        ("SmokeBoot", "boot.new_game", 10),
        ("WorldTitle", "boot.cold_start", 37),
    ]:
        seen[case] = load_suite_proof(world, suite, md5, count, required=True)

    # Only complete emulated gameplay qualifies; no static-test or compile promotions.
    for suite, case, count in [
        ("GrandWorldHeroSave", "boot.continue", 37),
        ("GrandWorldHubParty", "hoenn.team_persistence", 94),
    ]:
        proof = load_suite_proof(world, suite, md5, count)
        if proof is not None:
            seen[case] = proof

    # This single isolated Lua suite makes all SIX *real* directed crossings
    # through the hub attendants. Each crossing checks in-game confirmation,
    # physical destination, stored active region and byte-identical party.
    # Only the full 167/167 verdict against this exact cartridge certifies them.
    six = load_suite_proof(world, "GrandWorldSixRoutes", md5, 167)
    register_six_route_proofs(seen, six)

    # The S.S. Aqua transfer independently proves the Johto-to-Kanto case.
    # If both travel proofs exist, keep BOTH instead of increasing the count.
    ship = load_suite_proof(world, "SSAquaKantoCrossing", md5, 94)
    if ship is not None:
        case = "travel.johto_to_kanto"
        if case in seen:
            seen[case]["additional_ship_proof"] = ship
        else:
            seen[case] = ship
    # All three tracked and intentionally different historical fixture cases
    # must be accepted. v7dirty exercises trainer-flag zeroing, v3 exercises
    # the incompatible-layout refusal, and v7renumber exercises safe old warps.
    # This is migration compatibility, NOT every personal save or slot backup.
    grouped = [
        ("save.migration",
         [("VerifyV7Migrate", 14), ("MigrateFixtures", 7),
          ("VerifyMapRenumber", 4)],
         "tracked v3 refusal, dirty v7 migration, two renumbered-map warps"),
        ("audio.bgm",
         [("JohtoMusicPass", 18), ("Route41SurfBgm", 11)],
         "tested Johto overworld, takeover, cycling and surfing music states"),
        ("graphics.palettes",
         [("WorldTitle", 37), ("DayNightTint", 32)],
         "title RGB555 resources and outdoor/day-night/cave palette transitions"),
    ]
    for case, checks, scope in grouped:
        proof = load_suite_group_proof(world, md5, case, checks, scope)
        if proof is not None:
            seen[case] = proof
    ids=manifest()
    out={"rom_sha256":sha,"rom_md5":md5,"world_base":"15d3888b0d81322a04d3c71b0bce18948761ee44",
         "verified":len(seen),"pending":len(ids)-len(seen),"total":len(ids),
         "cases":{key:{"status":"verified","evidence":seen[key]} if key in seen else {"status":"pending"} for key in ids},
         "release_approved":False}
    return out

if __name__=="__main__":
    try:
        if len(sys.argv)!=3:
            raise ValueError("usage: qa_acceptance.py /isolated/world /path/report.json")
        result=report(Path(sys.argv[1]))
        Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+"\n")
        print(f"verified {result['verified']}/{result['total']}; release_approved=False")
    except (ValueError,KeyError,OSError,UnicodeError) as exc:
        sys.exit(f"FAIL CLOSED: {exc}")
