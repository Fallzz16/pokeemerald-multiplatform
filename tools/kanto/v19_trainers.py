"""Materialize four original FireRed Route 3 battles after Kanto V0.18.

This module must run only against the pinned FireRed input and a disposable
generated build tree. All allocations are append-only and save-compatible.
"""
import re
from pathlib import Path

ROSTER = (("Robin", "LASS"), ("Sally", "LASS"),
          ("Janice", "LASS"), ("Calvin", "YOUNGSTER"))


def materialize_route3(source: Path, emerald: Path, used_rows: list[dict],
                       load_json, emit_json) -> dict:
    opp_path = emerald / "include/constants/opponents.h"
    flag_path = emerald / "include/constants/flags.h"
    party_path = emerald / "src/data/trainer_parties.h"
    trainer_path = emerald / "src/data/trainers.h"
    opponents = opp_path.read_text(encoding="utf-8")
    flags = flag_path.read_text(encoding="utf-8")
    if ("#define TRAINERS_COUNT                      873" not in opponents
            or "#define MAX_TRAINERS_COUNT                  864" not in opponents):
        raise RuntimeError("V0.18 trainer registry/save layout changed unexpectedly")
    used = [row["flag_value"] for row in used_rows]
    if len(used) != 185 or len(used) != len(set(used)):
        raise RuntimeError("Expected 185 distinct pre-existing Kanto flags")
    pool = sorted({
        int(v, 16) for v in re.findall(
            r"(?m)^#define FLAG_UNUSED_0x([0-9A-Fa-f]{3})\s+", flags)
        if 0x264 <= int(v, 16) < 0x500
    })
    free = [v for v in pool if v not in set(used)]
    if len(free) < len(ROSTER):
        raise RuntimeError("No unique saved flags remain for Route 3")

    original = load_json(source, "data/maps/Route3/map.json")
    dest = load_json(emerald, "data/maps/Kanto_Route3/map.json")
    original_trainers = (source / "src/data/trainers.h").read_text(encoding="utf-8")
    original_parties = (source / "src/data/trainer_parties.h").read_text(encoding="utf-8")
    species = set(re.findall(
        r"\bSPECIES_[A-Z0-9_]+\b",
        (emerald / "include/constants/species.h").read_text(encoding="utf-8")))
    scripts_path = emerald / "data/maps/Kanto_Route3/scripts.inc"
    scripts = scripts_path.read_text(encoding="utf-8")
    current_trainers = trainer_path.read_text(encoding="utf-8")
    current_parties = party_path.read_text(encoding="utf-8")
    defs, parties, trainers, flag_defs, report = [], [], [], [], []
    for i, (name, category) in enumerate(ROSTER):
        source_id = f"TRAINER_{category}_{name.upper()}"
        prefix = "Lass" if category == "LASS" else "Youngster"
        source_party = f"sParty_{prefix}{name}"
        if not re.search(r"\[" + re.escape(source_id) + r"\]\s*=\s*\{",
                         original_trainers):
            raise RuntimeError(f"Missing FireRed original trainer {source_id}")
        match = re.search(
            r"static const struct TrainerMonNoItemDefaultMoves\s+"
            + re.escape(source_party) + r"\[\]\s*=\s*\{([\s\S]*?)\n\};",
            original_parties)
        if not match:
            raise RuntimeError(f"Missing original party {source_party}")
        body = match.group(1)
        members = re.findall(r"\bSPECIES_[A-Z0-9_]+\b", body)
        if (not members or not re.search(r"\.lvl\s*=\s*\d+", body)
                or any(mon not in species for mon in members)):
            raise RuntimeError(f"Invalid original party {source_party}")
        actors = [
            o for o in original["object_events"]
            if o.get("script") == f"Route3_EventScript_{name}"
            and o.get("trainer_type") == "TRAINER_TYPE_NORMAL"
            and o.get("graphics_id") == f"OBJ_EVENT_GFX_{category}"
        ]
        if len(actors) != 1:
            raise RuntimeError(f"Missing or ambiguous original actor: {name}")
        obj = actors[0]
        if any(o["x"] == obj["x"] and o["y"] == obj["y"]
               for o in dest["object_events"]):
            raise RuntimeError(f"Route 3 object collision at {name}")
        macro = f"TRAINER_KANTO_V19_{category}_{name.upper()}"
        party = f"sParty_KantoV19{prefix}{name}"
        flag = f"FLAG_KANTO_V19_TRAINER_{name.upper()}"
        label = f"Kanto_Route3_EventScript_V19{name}"
        dest["object_events"].append({
            key: obj[key] for key in (
                "graphics_id", "x", "y", "elevation", "movement_type",
                "movement_range_x", "movement_range_y", "trainer_type",
                "trainer_sight_or_berry_tree_id")
        } | {"script": label, "flag": "0"})
        intro = f"Kanto_Route3_Text_V19{name}Intro"
        defeat = f"Kanto_Route3_Text_V19{name}Defeat"
        after = f"Kanto_Route3_Text_V19{name}After"
        scripts += f"""
{label}::
    trainerbattle_single {macro}, {intro}, {defeat}
    msgbox {after}, MSGBOX_AUTOCLOSE
    end

{intro}:
    .string "Let's have a POKeMON battle!$"

{defeat}:
    .string "You're really good!$"

{after}:
    .string "I'll train some more.$"
"""
        defs.append(f"#define {macro:<44} {873 + i}\n")
        flag_defs.append(f"#define {flag:<44} FLAG_UNUSED_0x{free[i]:03X}\n")
        parties.append(
            f"static const struct TrainerMonNoItemDefaultMoves {party}[] = {{"
            + body + "\n};\n")
        encounter = ("F_TRAINER_FEMALE | TRAINER_ENCOUNTER_MUSIC_FEMALE"
                     if category == "LASS" else "TRAINER_ENCOUNTER_MUSIC_MALE")
        trainers.append(f"""    [{macro}] =
    {{
        .trainerClass = TRAINER_CLASS_{category},
        .encounterMusic_gender = {encounter},
        .trainerPic = TRAINER_PIC_{category},
        .trainerName = _("{name.upper()}"),
        .items = {{}},
        .doubleBattle = FALSE,
        .aiFlags = AI_SCRIPT_CHECK_BAD_MOVE,
        .party = NO_ITEM_DEFAULT_MOVES({party}),
    }},
""")
        report.append({
            "name": name, "category": category, "map": "Kanto_Route3",
            "trainer_id": 873 + i, "symbol": macro, "party": party,
            "flag": flag, "flag_value": free[i], "event": label,
            "position": [obj["x"], obj["y"]], "source_trainer": source_id,
        })

    footer = "#endif // GUARD_CONSTANTS_FLAGS_H"
    if flags.count(footer) != 1 or not current_trainers.rstrip().endswith("};"):
        raise RuntimeError("Unexpected flags.h or trainers.h file format")
    emit_json(emerald / "data/maps/Kanto_Route3/map.json", dest)
    scripts_path.write_text(scripts, encoding="utf-8")
    opp_path.write_text(opponents.replace(
        "#define TRAINERS_COUNT                      873",
        "".join(defs) + "#define TRAINERS_COUNT                      877"),
        encoding="utf-8")
    party_path.write_text(
        current_parties.rstrip() + "\n\n" + "\n".join(parties), encoding="utf-8")
    p = current_trainers.rfind("};")
    trainer_path.write_text(
        current_trainers[:p] + "\n" + "\n".join(trainers) + current_trainers[p:],
        encoding="utf-8")
    flag_path.write_text(flags.replace(
        footer, "// V0.19 trainer victory flags\n" + "".join(flag_defs)
        + "\n" + footer), encoding="utf-8")
    return {"count": len(report), "trainers": report}
