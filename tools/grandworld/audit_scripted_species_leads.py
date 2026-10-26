#!/usr/bin/env python3
"""Source-only evidence of potential direct scripted acquisition in Grand World.

These 13 residual species come from the successful original/evolution audit
(#40316082335). This scanner does not rerun that audit, touch ROM/save files,
or claim the mapped event is reachable in-game.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

UNRESOLVED_FROM_EVOLUTION_AUDIT_40316082335 = (
    "SPECIES_CLAMPERL", "SPECIES_FINNEON", "SPECIES_HORSEA",
    "SPECIES_LAPRAS", "SPECIES_LUVDISC", "SPECIES_MANTINE",
    "SPECIES_NOSEPASS", "SPECIES_OCTILLERY", "SPECIES_RELICANTH",
    "SPECIES_REMORAID", "SPECIES_SEADRA", "SPECIES_SHELLDER",
    "SPECIES_SHELLOS",
)
COMMAND = re.compile(r"^\s*(givemon|giveegg|setwildbattle)\s+(SPECIES_[A-Z0-9_]+)\b")
METHODS = {
    "givemon": "scripted_gift_declaration",
    "giveegg": "scripted_egg_declaration",
    "setwildbattle": "scripted_battle_setup_declaration",
}


def inspect(root, min_files=200):
    root=Path(root)
    if not root.is_dir():
        raise ValueError(f"missing World scripts directory: {root}")
    files=sorted(root.rglob("scripts.inc"))
    if len(files)<min_files:
        raise ValueError(f"too few World map scripts: {len(files)}")
    out={s:[] for s in UNRESOLVED_FROM_EVOLUTION_AUDIT_40316082335}
    digests={}
    for path in files:
        data=path.read_bytes()
        for lineno,line in enumerate(data.decode("utf-8",errors="replace").splitlines(),start=1):
            m=COMMAND.match(line)
            if not m:continue
            opcode,species=m.groups()
            if species not in out:continue
            item={"op":opcode,"kind":METHODS[opcode],
                  "relative_script":str(path.relative_to(root)),
                  "line":lineno}
            out[species].append(item)
            digests[str(path.relative_to(root))]=hashlib.sha256(data).hexdigest()
    names=[s for s in out if out[s]]
    report={
        "schema_version":1,
        "source_evolution_audit_run":"https://github.com/Fallzz16/pokeemerald-multiplatform/actions/runs/40316082335",
        "source":"pinned PKMN-World data/maps/**/scripts.inc",
        "map_script_files_scanned":len(files),
        "original_residual_no_grass_or_evolution_path":len(out),
        "source_declared_gift_or_battle_species":len(names),
        "no_direct_map_script_command_identified":len(out)-len(names),
        "species":[{"species":k,
                    "has_direct_script_declaration":bool(v),
                    "declarations":v,
                    "event_accessibility_verified":False,
                    "event_gameplay_completion_verified":False} for k,v in out.items()],
        "matched_script_sha256":digests,
        "conditional_compilation_resolved":False,
        "dynamic_script_calls_and_trade_tables_analyzed":False,
        "species_obtainability_certified":False,
        "rom_or_save_modified":False,
        "release_approved":False,
    }
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("map_scripts_dir",type=Path)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        report=inspect(args.map_scripts_dir)
        args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(f"{report['map_script_files_scanned']} pinned World scripts scanned; "
              f"{report['source_declared_gift_or_battle_species']} of 13 have explicit scripted-source leads, "
              f"{report['no_direct_map_script_command_identified']} have none in this limited scan. "
              "No event reachable in gameplay certified.")
    except (OSError,ValueError,TypeError,KeyError) as err:
        sys.exit("FAIL CLOSED script species audit: "+str(err))


if __name__=="__main__":
    main()
