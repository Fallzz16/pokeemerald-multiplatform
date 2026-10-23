"""Kanto V0.21: first real Nugget Bridge Rocket story encounter.

Imports the original Route 24 NPC position and FireRed battle party, while
using Emerald-compatible temporary Rocket battle artwork. Victory and Nugget
claim have independent, persistent, append-only flags. No save ABI change.
"""
import re
from pathlib import Path

ROCKET_SOURCE_TRAINER = "TRAINER_TEAM_ROCKET_GRUNT_6"
ROCKET_SOURCE_PARTY = "sParty_TeamRocketGrunt6"
ROCKET_ID = 899
ROCKET_WIN_FLAG = "FLAG_KANTO_V21_BRIDGE_ROCKET_DEFEATED"
ROCKET_ITEM_FLAG = "FLAG_KANTO_V21_BRIDGE_NUGGET_CLAIMED"
ROCKET_FLAG_VALUE = 0x906
ITEM_FLAG_VALUE = 0x907


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def import_nugget_rocket(source: Path, emerald: Path, used_rows: list[dict],
                         load_json, emit_json) -> dict:
    opp_path = emerald / "include/constants/opponents.h"
    flag_path = emerald / "include/constants/flags.h"
    trainer_path = emerald / "src/data/trainers.h"
    parties_path = emerald / "src/data/trainer_parties.h"
    battle_path = emerald / "src/battle_setup.c"
    opponents, flags = _read(opp_path), _read(flag_path)
    trainers, parties, battle = (_read(trainer_path), _read(parties_path),
                                 _read(battle_path))
    if opponents.count("#define TRAINERS_COUNT                      899") != 1:
        raise RuntimeError("Expected Kanto V0.20 trainer table not found")
    if opponents.count("#define MAX_TRAINERS_COUNT                  864") != 1:
        raise RuntimeError("Save-ABI trainer flag count cannot be changed")

    previous = [r["flag_value"] for r in used_rows]
    if len(previous) != 211 or len(set(previous)) != 211:
        raise RuntimeError("V0.20 must allocate exactly 211 unique Kanto flags")
    for value in (ROCKET_FLAG_VALUE, ITEM_FLAG_VALUE):
        if value in previous or value >= 0x920:
            raise RuntimeError("Nugget Bridge would reuse or daily-reset a flag")
        symbol = f"FLAG_UNUSED_0x{value:03X}"
        offset = value - 0x860
        expected = rf"(?m)^#define {symbol}\s+\(SYSTEM_FLAGS \+ 0x{offset:X}\)\s+// Unused Flag\s*$"
        if len(re.findall(expected, flags)) != 1:
            raise RuntimeError(f"Persistent unused flag was changed: {symbol}")
        aliases = re.findall(
            rf"(?m)^#define \w+\s+\(SYSTEM_FLAGS \+ 0x{offset:X}\)(?:\s|$)",
            flags,
        )
        if len(aliases) != 1:
            raise RuntimeError(f"Unexpected alias at saved flag {symbol}")

    if (_read(emerald / "src/event_data.c").count(
            "gSaveBlock1Ptr->flags[DAILY_FLAGS_START / 8]") != 1):
        raise RuntimeError("Persistent/non-daily boundary changed")
    original_tr = _read(source / "src/data/trainers.h")
    original_pt = _read(source / "src/data/trainer_parties.h")
    entry = re.search(
        r"\[" + ROCKET_SOURCE_TRAINER + r"\]\s*=\s*\{([\s\S]*?)\n\s*\},",
        original_tr)
    party = re.search(
        r"static const struct TrainerMonNoItemDefaultMoves\s+"
        + ROCKET_SOURCE_PARTY + r"\[\]\s*=\s*\{([\s\S]*?)\n\};",
        original_pt)
    if not entry or not party or (
            "NO_ITEM_DEFAULT_MOVES(" + ROCKET_SOURCE_PARTY + ")" not in entry.group(1)):
        raise RuntimeError("FireRed Nugget Bridge Grunt data is unsupported")
    body = party.group(1)
    valid_species = set(re.findall(
        r"\bSPECIES_[A-Z0-9_]+\b",
        _read(emerald / "include/constants/species.h")))
    members = re.findall(r"\bSPECIES_[A-Z0-9_]+\b", body)
    if (not members or len(re.findall(r"\.lvl\s*=", body)) != len(members)
            or any(mon not in valid_species for mon in members)):
        raise RuntimeError("Invalid FireRed Rocket team or species")
    items = _read(emerald / "include/constants/items.h")
    if "ITEM_NUGGET" not in items:
        raise RuntimeError("Nugget not available in Emerald")
    classes = _read(emerald / "include/constants/trainers.h")
    if ("TRAINER_CLASS_TEAM_AQUA" not in classes
            or "TRAINER_PIC_AQUA_GRUNT_M" not in classes):
        raise RuntimeError("No compatible placeholder Rocket artwork")

    area = "Route24"
    src = load_json(source, f"data/maps/{area}/map.json")
    dst = load_json(emerald, f"data/maps/Kanto_{area}/map.json")
    original = [o for o in src["object_events"]
                if o.get("script") == "Route24_EventScript_Rocket"
                and o.get("graphics_id") == "OBJ_EVENT_GFX_MAN"
                and o.get("trainer_type") == "TRAINER_TYPE_NONE"]
    if len(original) != 1:
        raise RuntimeError("Original Nugget Bridge Rocket actor missing")
    obj = original[0]
    if any(o["x"] == obj["x"] and o["y"] == obj["y"]
           for o in dst["object_events"]):
        raise RuntimeError("Nugget Bridge actor overlaps existing Route 24 event")
    event = "Kanto_Route24_EventScript_V21NuggetBridgeRocket"
    dst["object_events"].append({
        key: obj[key] for key in (
            "graphics_id", "x", "y", "elevation", "movement_type",
            "movement_range_x", "movement_range_y", "trainer_type",
            "trainer_sight_or_berry_tree_id")
    } | {"script": event, "flag": "0"})
    source_script = emerald / "data/maps/Kanto_Route24/scripts.inc"
    scripts = _read(source_script)
    scripts += f"""
{event}::
    trainerbattle_single TRAINER_KANTO_V21_BRIDGE_ROCKET, Kanto_Route24_Text_V21RocketIntro, Kanto_Route24_Text_V21RocketDefeat
    goto_if_set {ROCKET_ITEM_FLAG}, Kanto_Route24_EventScript_V21RocketAfter
    giveitem ITEM_NUGGET
    goto_if_eq VAR_RESULT, FALSE, Kanto_Route24_EventScript_V21RocketFullBag
    setflag {ROCKET_ITEM_FLAG}
    msgbox Kanto_Route24_Text_V21RocketNugget, MSGBOX_AUTOCLOSE
    end

Kanto_Route24_EventScript_V21RocketFullBag::
    msgbox Kanto_Route24_Text_V21RocketNoRoom, MSGBOX_AUTOCLOSE
    end

Kanto_Route24_EventScript_V21RocketAfter::
    msgbox Kanto_Route24_Text_V21RocketAfter, MSGBOX_AUTOCLOSE
    end

Kanto_Route24_Text_V21RocketIntro:
    .string "Our team wants your POKeMON!$"

Kanto_Route24_Text_V21RocketDefeat:
    .string "You defeated me!$"

Kanto_Route24_Text_V21RocketNugget:
    .string "You earned a NUGGET!$"

Kanto_Route24_Text_V21RocketNoRoom:
    .string "Make room for your prize!$"

Kanto_Route24_Text_V21RocketAfter:
    .string "Your team is impressive.$"
"""
    if (battle.count("    default:\n        return TRAINER_FLAGS_START + trainerId;") != 1
            or not trainers.rstrip().endswith("};")):
        raise RuntimeError("Battle setup/trainer table format changed")
    footer = "#endif // GUARD_CONSTANTS_FLAGS_H"
    if flags.count(footer) != 1:
        raise RuntimeError("Flags include guard modified")
    emit_json(emerald / "data/maps/Kanto_Route24/map.json", dst)
    source_script.write_text(scripts, encoding="utf-8")
    opp_path.write_text(
        opponents.replace(
            "#define TRAINERS_COUNT                      899",
            "#define TRAINER_KANTO_V21_BRIDGE_ROCKET             899\n"
            "#define TRAINERS_COUNT                      900"),
        encoding="utf-8")
    parties_path.write_text(parties.rstrip() + "\n\n"
                            "static const struct TrainerMonNoItemDefaultMoves "
                            "sParty_KantoV21BridgeRocket[] = {"
                            + body + "\n};\n", encoding="utf-8")
    idx = trainers.rfind("};")
    trainer_path.write_text(trainers[:idx] + """
    [TRAINER_KANTO_V21_BRIDGE_ROCKET] =
    {
        .trainerClass = TRAINER_CLASS_TEAM_AQUA,
        .encounterMusic_gender = TRAINER_ENCOUNTER_MUSIC_MALE,
        .trainerPic = TRAINER_PIC_AQUA_GRUNT_M,
        .trainerName = _("ROCKET"),
        .items = {},
        .doubleBattle = FALSE,
        .aiFlags = AI_SCRIPT_CHECK_BAD_MOVE,
        .party = NO_ITEM_DEFAULT_MOVES(sParty_KantoV21BridgeRocket),
    },
""" + trainers[idx:], encoding="utf-8")
    flag_path.write_text(
        flags.replace(
            footer,
            "// V0.21 permanent Nugget Bridge story and victory flags\n"
            f"#define {ROCKET_WIN_FLAG:<48} FLAG_UNUSED_0x906\n"
            f"#define {ROCKET_ITEM_FLAG:<48} FLAG_UNUSED_0x907\n\n"
            + footer),
        encoding="utf-8")
    battle_path.write_text(
        battle.replace(
            "    default:\n        return TRAINER_FLAGS_START + trainerId;",
            f"    case TRAINER_KANTO_V21_BRIDGE_ROCKET:\n"
            f"        return {ROCKET_WIN_FLAG};\n"
            "    default:\n        return TRAINER_FLAGS_START + trainerId;"),
        encoding="utf-8")
    return {
        "count": 1, "trainer_id": ROCKET_ID,
        "source_trainer": ROCKET_SOURCE_TRAINER,
        "source_party": ROCKET_SOURCE_PARTY,
        "position": [obj["x"], obj["y"]],
        "event": event,
        "trainer_flag": ROCKET_WIN_FLAG,
        "trainer_flag_value": ROCKET_FLAG_VALUE,
        "reward_flag": ROCKET_ITEM_FLAG,
        "reward_flag_value": ITEM_FLAG_VALUE,
        "reward_item": "ITEM_NUGGET",
        "battle_sprite_temporary": True,
    }
