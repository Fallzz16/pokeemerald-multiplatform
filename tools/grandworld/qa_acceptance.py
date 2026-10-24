#!/usr/bin/env python3
"""Grand World M8: strict evidence for up to three of 105 release criteria.
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

def report(world):
    rom=(world/"pokemonworld.gba").read_bytes()
    if len(rom)!=33554432 or rom[0xB2]!=0x96 or rom[0xAC:0xB0]!=b'BPEE':
        raise ValueError("invalid World ROM header or size")
    if (sum(rom[0xA0:0xBD])+rom[0xBD]+0x19)&255:
        raise ValueError("World ROM header checksum mismatch")
    sha=hashlib.sha256(rom).hexdigest()
    md5=hashlib.md5(rom).hexdigest().upper()
    proof=json.loads((world.parent/"m8-integrated-gen4-evidence.json").read_text())
    if proof.get("sha")!=sha or proof.get("rom_size")!=len(rom):
        raise ValueError("memory evidence references different ROM")
    limits={"ROM":33554432,"EWRAM":262144,"IWRAM":32768}
    mem=proof.get("memory",{})
    if set(mem)!=set(limits) or any(type(mem[k]) is not int or mem[k]<1 or mem[k]>v for k,v in limits.items()):
        raise ValueError("invalid hardware memory provenance")
    seen={"performance.memory":{"source":"ARM linker / SHA256","memory_bytes":mem}}
    for suite,case in [("SmokeBoot","boot.new_game"),("WorldTitle","boot.cold_start")]:
        stamp=world/"_pwtest"/(suite+".PASS")
        fail=world/"_pwtest"/(suite+".FAIL")
        if not stamp.is_file() or fail.exists():
            raise ValueError("required mGBA suite absent or failed: "+suite)
        txt=stamp.read_text()
        match=re.fullmatch(r"PASS (\d+)/(\d+) rom=([A-F0-9]{32}) at=[^\r\n]+ suite="+suite+r"\s*",txt)
        if not match or match[1]!=match[2] or int(match[1])==0 or match[3]!=md5:
            raise ValueError("stale or malformed mGBA test result: "+suite)
        seen[case]={"source":"headless mGBA Lua","suite":suite,"passed":int(match[1]),"rom_md5":md5}
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
