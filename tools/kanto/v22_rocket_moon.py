"""V0.22: four source-authentic Team Rocket trainers in Mt. Moon B2F.

Run only after V0.21 materialization. The original FireRed Rocket actor
graphic and battle portrait do not exist in the current Emerald Hybrid:
both are mapped to verified Emerald Aqua placeholders until art is ported.
Stable trainer IDs 900..903; victory flags 0x908..0x90B, save ABI unchanged.
"""
import re
from pathlib import Path

ROSTER = (
    ("Grunt1", "TRAINER_TEAM_ROCKET_GRUNT", "sParty_TeamRocketGrunt"),
    ("Grunt2", "TRAINER_TEAM_ROCKET_GRUNT_2", "sParty_TeamRocketGrunt2"),
    ("Grunt3", "TRAINER_TEAM_ROCKET_GRUNT_3", "sParty_TeamRocketGrunt3"),
    ("Grunt4", "TRAINER_TEAM_ROCKET_GRUNT_4", "sParty_TeamRocketGrunt4"),
)
FIRST_TRAINER_ID = 900
FIRST_FLAG = 0x908
FIELD_GRAPHIC = "OBJ_EVENT_GFX_AQUA_MEMBER_M"


def read(path):
    return path.read_text(encoding="utf-8")


def import_rocket_moon(source: Path, emerald: Path, previous_rows: list[dict],
                       load_json, emit_json) -> dict:
    flag_path = emerald / "include/constants/flags.h"
    opponent_path = emerald / "include/constants/opponents.h"
    party_path = emerald / "src/data/trainer_parties.h"
    trainer_path = emerald / "src/data/trainers.h"
    battle_path = emerald / "src/battle_setup.c"
    flags = read(flag_path)
    opponents = read(opponent_path)
    parties = read(party_path)
    trainers = read(trainer_path)
    battles = read(battle_path)
    old_values = [r["flag_value"] for r in previous_rows]
    if len(old_values) != 213 or len(set(old_values)) != 213:
        raise RuntimeError("V0.21 expected 213 unique saved Kanto flags")
    if opponents.count("#define TRAINERS_COUNT                      900") != 1:
        raise RuntimeError("V0.21 trainer table must have 900 entries")
    if opponents.count("#define MAX_TRAINERS_COUNT                  864") != 1:
        raise RuntimeError("V0.22 must not expand the trainer save bitmap")
    if battles.count("    default:\n        return TRAINER_FLAGS_START + trainerId;") != 1:
        raise RuntimeError("Unexpected Kanto trainer defeated flag mapping")

    # Verify these bits are saved, unused, and not part of daily resets.
    for i in range(len(ROSTER)):
        flag_value = FIRST_FLAG + i
        symbol = f"FLAG_UNUSED_0x{flag_value:03X}"
        expected = rf"(?m)^#define {symbol}\s+\(SYSTEM_FLAGS \+ 0x{flag_value - 0x860:X}\)\s+// Unused Flag\s*$"
        if len(re.findall(expected, flags)) != 1:
            raise RuntimeError("Unsafe V0.22 flag: " + symbol)
        if flag_value in old_values or flag_value >= 0x920:
            raise RuntimeError("Non-unique or non-persistent V0.22 flag")
        aliases = re.findall(
            rf"(?m)^#define \w+\s+\(SYSTEM_FLAGS \+ 0x{flag_value-0x860:X}\)(?:\s|$)", flags
        )
        if len(aliases) != 1:
            raise RuntimeError("Conflicting saved flag alias: " + symbol)
    if "gSaveBlock1Ptr->flags[DAILY_FLAGS_START / 8]" not in read(
            emerald / "src/event_data.c"):
        raise RuntimeError("Daily flag reset contract changed")

    event_header = read(emerald / "include/constants/event_objects.h")
    trainer_header = read(emerald / "include/constants/trainers.h")
    for symbol in (FIELD_GRAPHIC,):
        if symbol not in event_header:
            raise RuntimeError("Temporary Emerald field graphic missing: " + symbol)
    for symbol in ("TRAINER_CLASS_TEAM_AQUA", "TRAINER_PIC_AQUA_GRUNT_M"):
        if symbol not in trainer_header:
            raise RuntimeError("Temporary Emerald Rocket battle class missing: " + symbol)

    src_map = load_json(source, "data/maps/MtMoon_B2F/map.json")
    dest_map = load_json(emerald, "data/maps/Kanto_MtMoon_B2F/map.json")
    source_trainers = read(source / "src/data/trainers.h")
    source_parties = read(source / "src/data/trainer_parties.h")
    species = set(re.findall(
        r"\bSPECIES_[A-Z0-9_]+\b",
        read(emerald / "include/constants/species.h"),
    ))
    script_file = emerald / "data/maps/Kanto_MtMoon_B2F/scripts.inc"
    scripts = read(script_file)
    opp_defs, new_parties, new_trainers, new_flags, flag_cases, records = [], [], [], [], [], []

    for index, (name, source_id, source_party) in enumerate(ROSTER):
        actor_label = "MtMoon_B2F_EventScript_" + name
        matches = [
            obj for obj in src_map["object_events"]
            if obj.get("script") == actor_label
            and obj.get("graphics_id") == "OBJ_EVENT_GFX_ROCKET_M"
            and obj.get("trainer_type") == "TRAINER_TYPE_NORMAL"
        ]
        if len(matches) != 1:
            raise RuntimeError("Source Rocket event not unique: " + name)
        original = matches[0]
        if any(o["x"] == original["x"] and o["y"] == original["y"]
               for o in dest_map["object_events"]):
            raise RuntimeError("Mt. Moon actor position occupied: " + name)
        match = re.search(
            r"\[" + re.escape(source_id) + r"\]\s*=\s*\{([\s\S]*?)\n\s*\},",
            source_trainers,
        )
        if not match or not re.search(
                r"\.party\s*=\s*NO_ITEM_DEFAULT_MOVES\("
                + re.escape(source_party) + r"\)", match.group(1)):
            raise RuntimeError("Unsupported source Rocket battle: " + source_id)
        part = re.search(
            r"static const struct TrainerMonNoItemDefaultMoves\s+"
            + re.escape(source_party) + r"\[\]\s*=\s*\{([\s\S]*?)\n\};",
            source_parties,
        )
        if not part:
            raise RuntimeError("Missing Rocket party " + source_party)
        body = part.group(1)
        members = re.findall(r"\bSPECIES_[A-Z0-9_]+\b", body)
        if not members or not re.search(r"\.lvl\s*=\s*\d+", body):
            raise RuntimeError("Empty/unsupported Rocket party " + source_party)
        if any(p not in species for p in members):
            raise RuntimeError("Emerald does not support original Rocket species")

        symbol = f"TRAINER_KANTO_V22_ROCKET_{name.upper()}"
        flag = f"FLAG_KANTO_V22_ROCKET_{name.upper()}_DEFEATED"
        party = f"sParty_KantoV22Rocket{name}"
        script = f"Kanto_MtMoon_B2F_EventScript_V22Rocket{name}"
        intro = f"Kanto_MtMoon_B2F_Text_V22{name}Intro"
        defeat = f"Kanto_MtMoon_B2F_Text_V22{name}Defeat"
        after = f"Kanto_MtMoon_B2F_Text_V22{name}After"
        mapped = {
            key: original[key] for key in (
                "x", "y", "elevation", "movement_type", "movement_range_x",
                "movement_range_y", "trainer_type", "trainer_sight_or_berry_tree_id")
        }
        mapped.update({"graphics_id": FIELD_GRAPHIC, "script": script, "flag": "0"})
        dest_map["object_events"].append(mapped)
        scripts += f"""
{script}::
    trainerbattle_single {symbol}, {intro}, {defeat}
    msgbox {after}, MSGBOX_AUTOCLOSE
    end

{intro}:
    .string "Get out of TEAM ROCKET's way!$"

{defeat}:
    .string "We were defeated!$"

{after}:
    .string "We'll be back!$"
"""
        opp_defs.append(f"#define {symbol:<45} {FIRST_TRAINER_ID + index}\n")
        new_flags.append(f"#define {flag:<45} FLAG_UNUSED_0x{FIRST_FLAG + index:03X}\n")
        flag_cases.append(f"    case {symbol}:\n        return {flag};\n")
        new_parties.append(
            f"static const struct TrainerMonNoItemDefaultMoves {party}[] = {{"
            + body + "\n};\n")
        new_trainers.append(f"""    [{symbol}] =
    {{
        .trainerClass = TRAINER_CLASS_TEAM_AQUA,
        .encounterMusic_gender = TRAINER_ENCOUNTER_MUSIC_MALE,
        .trainerPic = TRAINER_PIC_AQUA_GRUNT_M,
        .trainerName = _("ROCKET"),
        .items = {{}},
        .doubleBattle = FALSE,
        .aiFlags = AI_SCRIPT_CHECK_BAD_MOVE,
        .party = NO_ITEM_DEFAULT_MOVES({party}),
    }},
""")
        records.append({
            "name": name, "source_trainer": source_id, "source_party": source_party,
            "trainer_id": FIRST_TRAINER_ID + index, "symbol": symbol,
            "party": party, "flag": flag, "flag_value": FIRST_FLAG + index,
            "position": [original["x"], original["y"]], "script": script,
            "source_graphics_id": original["graphics_id"],
            "field_graphics_id": FIELD_GRAPHIC, "art_temporary": True,
        })

    footer = "#endif // GUARD_CONSTANTS_FLAGS_H"
    if flags.count(footer) != 1 or not trainers.rstrip().endswith("};"):
        raise RuntimeError("Unexpected constant/trainer table end")
    emit_json(emerald / "data/maps/Kanto_MtMoon_B2F/map.json", dest_map)
    script_file.write_text(scripts, encoding="utf-8")
    opponent_path.write_text(
        opponents.replace(
            "#define TRAINERS_COUNT                      900",
            "".join(opp_defs) + "#define TRAINERS_COUNT                      904"),
        encoding="utf-8")
    flag_path.write_text(flags.replace(
        footer, "// V0.22 Rocket Mt. Moon victories - permanent SYSTEM_FLAGS\n"
        + "".join(new_flags) + "\n" + footer), encoding="utf-8")
    party_path.write_text(
        parties.rstrip() + "\n\n" + "\n".join(new_parties), encoding="utf-8")
    at = trainers.rfind("};")
    trainer_path.write_text(
        trainers[:at] + "\n" + "\n".join(new_trainers) + trainers[at:],
        encoding="utf-8")
    battle_path.write_text(
        battles.replace(
            "    default:\n        return TRAINER_FLAGS_START + trainerId;",
            "".join(flag_cases)
            + "    default:\n        return TRAINER_FLAGS_START + trainerId;"),
        encoding="utf-8")
    return {"count": len(records), "trainers": records,
            "remaining_permanent_system_flags": 0x920 - (FIRST_FLAG + len(records))}
