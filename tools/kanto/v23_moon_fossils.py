"""Kanto V0.23 — Mt. Moon Miguel and one-time original fossil choice.

The script awards exactly one of Dome/Helix fossils only after Miguel is
defeated. All four new flags are saved SYSTEM_FLAGS 0x90C–0x90F, not daily.
Native Emerald collector/scientist portraits are temporary substitutes for
FireRed Super Nerd. Source Pokémon teams, actors and fossil locations are
matched to pinned FireRed input before modifying the generated tree.
"""
import re
from pathlib import Path

MIGUEL_ID = 904
MIGUEL_FLAG = 0x90C
FOSSILS_TAKEN_FLAG = 0x90D
DOME_CHOSEN_FLAG = 0x90E
HELIX_CHOSEN_FLAG = 0x90F
ORIGINAL_TRAINER = "TRAINER_SUPER_NERD_MIGUEL"
ORIGINAL_PARTY = "sParty_SuperNerdMiguel"
MIGUEL_FIELD_GRAPHIC = "OBJ_EVENT_GFX_SCIENTIST_1"
FOSSIL_GRAPHIC = "OBJ_EVENT_GFX_FOSSIL"

FLAG_NAMES = (
    ("FLAG_KANTO_V23_MIGUEL_DEFEATED", MIGUEL_FLAG),
    ("FLAG_KANTO_V23_FOSSILS_TAKEN", FOSSILS_TAKEN_FLAG),
    ("FLAG_KANTO_V23_DOME_CHOSEN", DOME_CHOSEN_FLAG),
    ("FLAG_KANTO_V23_HELIX_CHOSEN", HELIX_CHOSEN_FLAG),
)


def read(p):
    return p.read_text(encoding="utf-8")


def import_moon_fossils(source: Path, emerald: Path,
                        previously_used: list[dict], load_json, emit_json) -> dict:
    opp_path = emerald / "include/constants/opponents.h"
    flag_path = emerald / "include/constants/flags.h"
    party_path = emerald / "src/data/trainer_parties.h"
    trainers_path = emerald / "src/data/trainers.h"
    battle_path = emerald / "src/battle_setup.c"
    opponents = read(opp_path)
    flags = read(flag_path)
    parties = read(party_path)
    trainers = read(trainers_path)
    battles = read(battle_path)
    used = [r["flag_value"] for r in previously_used]
    if len(used) != 217 or len(set(used)) != len(used):
        raise RuntimeError("V0.22 Kanto saved flag history must have 217 bits")
    if (opponents.count("#define TRAINERS_COUNT                      904") != 1
            or opponents.count("#define MAX_TRAINERS_COUNT                  864") != 1):
        raise RuntimeError("V0.22 trainer save ABI changed")
    if battles.count("    default:\n        return TRAINER_FLAGS_START + trainerId;") != 1:
        raise RuntimeError("Trainer save mapping cannot be safely extended")
    for name, value in FLAG_NAMES:
        if value in used or value >= 0x920:
            raise RuntimeError("Attempt to reuse a trainer or daily flag " + name)
        base = f"FLAG_UNUSED_0x{value:03X}"
        expected = (
            rf"(?m)^#define {base}\s+\(SYSTEM_FLAGS \+ 0x{value - 0x860:X}\)"
            rf"\s+// Unused Flag\s*$")
        if len(re.findall(expected, flags)) != 1:
            raise RuntimeError("Expected unused permanent flag changed " + base)
        aliases = re.findall(
            rf"(?m)^#define \w+\s+\(SYSTEM_FLAGS \+ 0x{value - 0x860:X}\)(?:\s|$)",
            flags)
        if len(aliases) != 1:
            raise RuntimeError("Duplicate permanent flag alias " + base)

    events = read(emerald / "include/constants/event_objects.h")
    classes = read(emerald / "include/constants/trainers.h")
    items = read(emerald / "include/constants/items.h")
    for sym in (MIGUEL_FIELD_GRAPHIC, FOSSIL_GRAPHIC):
        if sym not in events:
            raise RuntimeError("Missing valid Emerald field graphic " + sym)
    for sym in ("TRAINER_CLASS_COLLECTOR", "TRAINER_PIC_COLLECTOR"):
        if sym not in classes:
            raise RuntimeError("Missing safe trainer class/pic placeholder " + sym)
    for sym in ("ITEM_DOME_FOSSIL", "ITEM_HELIX_FOSSIL"):
        if sym not in items:
            raise RuntimeError("Required FireRed fossil missing from Emerald " + sym)

    original = load_json(source, "data/maps/MtMoon_B2F/map.json")
    target = load_json(emerald, "data/maps/Kanto_MtMoon_B2F/map.json")
    source_trainers = read(source / "src/data/trainers.h")
    source_parties = read(source / "src/data/trainer_parties.h")
    src_record = re.search(
        r"\[" + ORIGINAL_TRAINER + r"\]\s*=\s*\{([\s\S]*?)\n\s*\},",
        source_trainers)
    src_party = re.search(
        r"static const struct TrainerMonNoItemDefaultMoves\s+"
        + ORIGINAL_PARTY + r"\[\]\s*=\s*\{([\s\S]*?)\n\};",
        source_parties)
    if not src_record or not src_party or (
            "NO_ITEM_DEFAULT_MOVES(" + ORIGINAL_PARTY + ")" not in src_record.group(1)):
        raise RuntimeError("Miguel trainer and FireRed party changed")
    body = src_party.group(1)
    species = set(re.findall(
        r"\bSPECIES_[A-Z0-9_]+\b",
        read(emerald / "include/constants/species.h")))
    mons = re.findall(r"\bSPECIES_[A-Z0-9_]+\b", body)
    if not mons or any(mon not in species for mon in mons):
        raise RuntimeError("Miguel party contains invalid Emerald species")
    if len(mons) != len(re.findall(r"\.lvl\s*=\s*\d+", body)):
        raise RuntimeError("Miguel team has unrecognized levels")

    specs = (
        ("Miguel", "MtMoon_B2F_EventScript_Miguel", "OBJ_EVENT_GFX_SCIENTIST",
         MIGUEL_FIELD_GRAPHIC, "Kanto_MtMoon_B2F_EventScript_V23Miguel", "0"),
        ("Dome", "MtMoon_B2F_EventScript_DomeFossil", FOSSIL_GRAPHIC,
         FOSSIL_GRAPHIC, "Kanto_MtMoon_B2F_EventScript_V23Dome", FLAG_NAMES[1][0]),
        ("Helix", "MtMoon_B2F_EventScript_HelixFossil", FOSSIL_GRAPHIC,
         FOSSIL_GRAPHIC, "Kanto_MtMoon_B2F_EventScript_V23Helix", FLAG_NAMES[1][0]),
    )
    records = []
    for name, original_script, expected_graphic, graphic, script, flag in specs:
        source_actors = [
            o for o in original["object_events"]
            if o.get("script") == original_script
            and o.get("graphics_id") == expected_graphic
            and o.get("trainer_type") == "TRAINER_TYPE_NONE"
        ]
        if len(source_actors) != 1:
            raise RuntimeError("Missing original Miguel/fossil actor " + name)
        src = source_actors[0]
        if any(o["x"] == src["x"] and o["y"] == src["y"]
               for o in target["object_events"]):
            raise RuntimeError("Mt. Moon actor cell already taken by " + name)
        mapped = {
            key: src[key] for key in (
                "x", "y", "elevation", "movement_type",
                "movement_range_x", "movement_range_y", "trainer_type",
                "trainer_sight_or_berry_tree_id")
        }
        mapped.update({"graphics_id": graphic, "script": script, "flag": flag})
        target["object_events"].append(mapped)
        records.append({
            "name": name, "event": script, "source_script": original_script,
            "position": [src["x"], src["y"]], "source_graphics_id": expected_graphic,
            "field_graphics_id": graphic, "flag": flag,
        })

    script_path = emerald / "data/maps/Kanto_MtMoon_B2F/scripts.inc"
    scripts = read(script_path)
    # On a current map visit the *other* fossil may remain displayed until
    # a transition. It is never obtainable twice due to the completed flag.
    scripts += """
Kanto_MtMoon_B2F_EventScript_V23Miguel::
    trainerbattle_single TRAINER_KANTO_V23_MIGUEL, Kanto_MtMoon_B2F_Text_V23MiguelIntro, Kanto_MtMoon_B2F_Text_V23MiguelDefeat
    msgbox Kanto_MtMoon_B2F_Text_V23MiguelAfter, MSGBOX_AUTOCLOSE
    end

Kanto_MtMoon_B2F_EventScript_V23Dome::
    lock
    faceplayer
    goto_if_unset FLAG_KANTO_V23_MIGUEL_DEFEATED, Kanto_MtMoon_B2F_EventScript_V23NotReady
    goto_if_set FLAG_KANTO_V23_FOSSILS_TAKEN, Kanto_MtMoon_B2F_EventScript_V23Done
    msgbox Kanto_MtMoon_B2F_Text_V23DomeAsk, MSGBOX_YESNO
    goto_if_eq VAR_RESULT, NO, Kanto_MtMoon_B2F_EventScript_V23Exit
    giveitem ITEM_DOME_FOSSIL
    goto_if_eq VAR_RESULT, FALSE, Kanto_MtMoon_B2F_EventScript_V23BagFull
    setflag FLAG_KANTO_V23_DOME_CHOSEN
    setflag FLAG_KANTO_V23_FOSSILS_TAKEN
    removeobject VAR_LAST_TALKED
    goto Kanto_MtMoon_B2F_EventScript_V23Exit

Kanto_MtMoon_B2F_EventScript_V23Helix::
    lock
    faceplayer
    goto_if_unset FLAG_KANTO_V23_MIGUEL_DEFEATED, Kanto_MtMoon_B2F_EventScript_V23NotReady
    goto_if_set FLAG_KANTO_V23_FOSSILS_TAKEN, Kanto_MtMoon_B2F_EventScript_V23Done
    msgbox Kanto_MtMoon_B2F_Text_V23HelixAsk, MSGBOX_YESNO
    goto_if_eq VAR_RESULT, NO, Kanto_MtMoon_B2F_EventScript_V23Exit
    giveitem ITEM_HELIX_FOSSIL
    goto_if_eq VAR_RESULT, FALSE, Kanto_MtMoon_B2F_EventScript_V23BagFull
    setflag FLAG_KANTO_V23_HELIX_CHOSEN
    setflag FLAG_KANTO_V23_FOSSILS_TAKEN
    removeobject VAR_LAST_TALKED
    goto Kanto_MtMoon_B2F_EventScript_V23Exit

Kanto_MtMoon_B2F_EventScript_V23NotReady::
    msgbox Kanto_MtMoon_B2F_Text_V23NotReady, MSGBOX_DEFAULT
    goto Kanto_MtMoon_B2F_EventScript_V23Exit

Kanto_MtMoon_B2F_EventScript_V23Done::
    msgbox Kanto_MtMoon_B2F_Text_V23Done, MSGBOX_DEFAULT
    goto Kanto_MtMoon_B2F_EventScript_V23Exit

Kanto_MtMoon_B2F_EventScript_V23BagFull::
    msgbox Kanto_MtMoon_B2F_Text_V23BagFull, MSGBOX_DEFAULT

Kanto_MtMoon_B2F_EventScript_V23Exit::
    release
    end

Kanto_MtMoon_B2F_Text_V23MiguelIntro:
    .string "You can't take our FOSSILS!$"
Kanto_MtMoon_B2F_Text_V23MiguelDefeat:
    .string "You win this time!$"
Kanto_MtMoon_B2F_Text_V23MiguelAfter:
    .string "Choose one FOSSIL!$"
Kanto_MtMoon_B2F_Text_V23DomeAsk:
    .string "Take the DOME FOSSIL?$"
Kanto_MtMoon_B2F_Text_V23HelixAsk:
    .string "Take the HELIX FOSSIL?$"
Kanto_MtMoon_B2F_Text_V23NotReady:
    .string "A trainer is guarding these.$"
Kanto_MtMoon_B2F_Text_V23Done:
    .string "Only one FOSSIL may be taken.$"
Kanto_MtMoon_B2F_Text_V23BagFull:
    .string "There isn't room in your BAG.$"
"""
    guard = "#endif // GUARD_CONSTANTS_FLAGS_H"
    if flags.count(guard) != 1 or not trainers.rstrip().endswith("};"):
        raise RuntimeError("Unexpected flags/trainer data format")
    # Validate all invariants before emitting files.
    emit_json(emerald / "data/maps/Kanto_MtMoon_B2F/map.json", target)
    script_path.write_text(scripts, encoding="utf-8")
    opp_path.write_text(
        opponents.replace(
            "#define TRAINERS_COUNT                      904",
            "#define TRAINER_KANTO_V23_MIGUEL                     904\n"
            "#define TRAINERS_COUNT                      905"),
        encoding="utf-8")
    flag_defs = "".join(
        f"#define {name:<47} FLAG_UNUSED_0x{value:03X}\n"
        for name, value in FLAG_NAMES
    )
    flag_path.write_text(
        flags.replace(guard, "// V0.23 saved Miguel / Fossil choice flags\n"
                      + flag_defs + "\n" + guard),
        encoding="utf-8")
    party_path.write_text(
        parties.rstrip()
        + "\n\nstatic const struct TrainerMonNoItemDefaultMoves "
        + "sParty_KantoV23Miguel[] = {" + body + "\n};\n",
        encoding="utf-8")
    idx = trainers.rfind("};")
    trainer_path.write_text(
        trainers[:idx] + """
    [TRAINER_KANTO_V23_MIGUEL] =
    {
        .trainerClass = TRAINER_CLASS_COLLECTOR,
        .encounterMusic_gender = TRAINER_ENCOUNTER_MUSIC_MALE,
        .trainerPic = TRAINER_PIC_COLLECTOR,
        .trainerName = _("MIGUEL"),
        .items = {},
        .doubleBattle = FALSE,
        .aiFlags = AI_SCRIPT_CHECK_BAD_MOVE,
        .party = NO_ITEM_DEFAULT_MOVES(sParty_KantoV23Miguel),
    },
""" + trainers[idx:], encoding="utf-8")
    battle_path.write_text(
        battles.replace(
            "    default:\n        return TRAINER_FLAGS_START + trainerId;",
            "    case TRAINER_KANTO_V23_MIGUEL:\n"
            "        return FLAG_KANTO_V23_MIGUEL_DEFEATED;\n"
            "    default:\n        return TRAINER_FLAGS_START + trainerId;"),
        encoding="utf-8")
    return {
        "count": 1, "trainer_id": MIGUEL_ID, "trainer_flag_value": MIGUEL_FLAG,
        "fossils_taken_flag_value": FOSSILS_TAKEN_FLAG,
        "dome_chosen_flag_value": DOME_CHOSEN_FLAG,
        "helix_chosen_flag_value": HELIX_CHOSEN_FLAG,
        "flags": [{"name": n, "flag_value": v} for n, v in FLAG_NAMES],
        "actors": records, "source_trainer": ORIGINAL_TRAINER,
        "source_party": ORIGINAL_PARTY, "party": "sParty_KantoV23Miguel",
        "remaining_permanent_system_flags": 0x920 - (HELIX_CHOSEN_FLAG + 1),
        "fossil_choice_is_exclusive": True,
        "sprite_portrait_provisional": True,
    }
