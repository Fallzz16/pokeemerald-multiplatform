"""Kanto V0.20: faithfully import source-backed common trainers from FireRed.

This only runs on a disposable materialization tree after V0.19.
Trainer IDs and victory flags are append-only. The selected new flags are
saved SYSTEM flags strictly before DAILY_FLAGS_START, not temporary/daily.
"""
import re
from pathlib import Path

# Order is part of the save compatibility contract; never reorder/insert.
ROSTER = (
    ("Route3", "Ben", "YOUNGSTER"),
    ("Route4", "Crissy", "LASS"),
    ("MtMoon_1F", "Iris", "LASS"),
    ("MtMoon_1F", "Miriam", "LASS"),
    ("MtMoon_1F", "Josh", "YOUNGSTER"),
    ("MtMoon_1F", "Marcos", "HIKER"),
    ("Route24", "Ethan", "CAMPER"),
    ("Route24", "Reli", "LASS"),
    ("Route24", "Timmy", "YOUNGSTER"),
    ("Route24", "Ali", "LASS"),
    ("Route24", "Cale", "BUG_CATCHER"),
    ("Route24", "Shane", "CAMPER"),
    ("Route25", "Franklin", "HIKER"),
    ("Route25", "Joey", "YOUNGSTER"),
    ("Route25", "Wayne", "HIKER"),
    ("Route25", "Dan", "YOUNGSTER"),
    ("Route25", "Kelsey", "PICNICKER"),
    ("Route25", "Nob", "HIKER"),
    ("Route25", "Flint", "CAMPER"),
    ("Route25", "Chad", "YOUNGSTER"),
    ("Route25", "Haley", "LASS"),
    ("CeruleanCity_Gym", "Diana", "PICNICKER"),
)

BASE_ID = 877
FLAG_START = 0x8F0
FLAG_STOP = FLAG_START + len(ROSTER)
EXPECTED_PREVIOUS_FLAGS = 189
EXPECTED_SOURCE_SHA = "ce6406d8c2eaf46d543c8a2606de0c3cb1951982"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _field(source_record: str, key: str) -> str:
    found = re.search(r"\." + re.escape(key) + r"\s*=\s*([^,\n]+)",
                      source_record)
    if not found:
        raise RuntimeError(f"Missing source trainer field: {key}")
    return found.group(1).strip()


def import_trainers(source: Path, emerald: Path, previous: list[dict],
                    load_json, emit_json) -> dict:
    """Append 22 trainers without changing MAX_TRAINERS_COUNT/SaveBlock."""
    opp_path = emerald / "include/constants/opponents.h"
    flags_path = emerald / "include/constants/flags.h"
    trainer_path = emerald / "src/data/trainers.h"
    parties_path = emerald / "src/data/trainer_parties.h"
    battle_path = emerald / "src/battle_setup.c"

    opp = _read(opp_path)
    flags = _read(flags_path)
    trainer_text = _read(trainer_path)
    party_text = _read(parties_path)
    battle = _read(battle_path)
    source_trainers = _read(source / "src/data/trainers.h")
    source_parties = _read(source / "src/data/trainer_parties.h")
    classes = _read(emerald / "include/constants/trainers.h")
    graphics = _read(emerald / "include/constants/event_objects.h")
    valid_species = set(re.findall(
        r"\bSPECIES_[A-Z0-9_]+\b",
        _read(emerald / "include/constants/species.h"),
    ))
    old_flags = [r["flag_value"] for r in previous]
    if len(old_flags) != EXPECTED_PREVIOUS_FLAGS or len(set(old_flags)) != len(old_flags):
        raise RuntimeError("V0.19 flags must contain 189 unique allocations")
    if (opp.count("#define TRAINERS_COUNT                      877") != 1
            or opp.count("#define MAX_TRAINERS_COUNT                  864") != 1):
        raise RuntimeError("Expected exact V0.19 trainer limits")
    if "#define TRAINER_FLAGS_START" not in flags or (
            "#define DAILY_FLAGS_START" not in flags or
            "FLAG_UNUSED_0x91F + (8 - FLAG_UNUSED_0x91F % 8)" not in flags):
        raise RuntimeError("Save-backed system/daily flag boundary changed")
    if _read(emerald / "src/event_data.c").count(
            "gSaveBlock1Ptr->flags[DAILY_FLAGS_START / 8]") != 1:
        raise RuntimeError("Daily flags reset semantics changed")
    if FLAG_STOP > 0x920:
        raise RuntimeError("New victory flags would overlap daily-reset flags")

    # The 0x8F0+ band was UNUSED in the pre-V0.20 source and belongs to
    # SYSTEM_FLAGS=0x860, a saved area; DAILY starts exactly at 0x920.
    # Check both the symbol and its exact offset so changing a header
    # cannot silently move victory bits into an unsafe flag range.
    for n in range(FLAG_START, FLAG_STOP):
        symbol = f"FLAG_UNUSED_0x{n:03X}"
        offset = n - 0x860
        expected = re.compile(
            rf"(?m)^#define {symbol}\s+\(SYSTEM_FLAGS \+ 0x{offset:X}\)\s+// Unused Flag\s*$"
        )
        if len(expected.findall(flags)) != 1:
            raise RuntimeError(f"Flag {symbol} no longer uniquely UNUSED")
        aliases = re.findall(
            rf"(?m)^#define \w+\s+\(SYSTEM_FLAGS \+ 0x{offset:X}\)(?:\s|$)",
            flags,
        )
        if len(aliases) != 1:
            raise RuntimeError(f"Duplicate system-flag value: 0x{n:03X}")
        if n in old_flags:
            raise RuntimeError(f"Collision with pre-V0.20 Kanto: 0x{n:03X}")

    if len({(where, name) for where, name, _ in ROSTER}) != len(ROSTER):
        raise RuntimeError("Duplicate original trainer")
    if not trainer_text.rstrip().endswith("};"):
        raise RuntimeError("Unexpected trainer table footer")
    if battle.count("    default:\n        return TRAINER_FLAGS_START + trainerId;") != 1:
        raise RuntimeError("Unexpected battle flag switch format")

    maps = {}
    source_maps = {}
    scripts = {}
    map_paths = {}
    added_flags, added_macros, party_defs, trainer_defs, flag_cases, rows = [], [], [], [], [], []

    for i, (area, name, category) in enumerate(ROSTER):
        if area not in maps:
            map_paths[area] = emerald / "data/maps" / f"Kanto_{area}"
            maps[area] = load_json(emerald, f"data/maps/Kanto_{area}/map.json")
            source_maps[area] = load_json(source, f"data/maps/{area}/map.json")
            scripts[area] = _read(map_paths[area] / "scripts.inc")

        old_macro = f"TRAINER_{category}_{name.upper()}"
        old_label = f"{area}_EventScript_{name}"
        record = re.search(
            r"\[" + re.escape(old_macro) + r"\]\s*=\s*\{([\s\S]*?)\n\s*\},",
            source_trainers,
        )
        if not record:
            raise RuntimeError(f"FireRed trainer not found: {old_macro}")
        body = record.group(1)
        if _field(body, "trainerClass") != f"TRAINER_CLASS_{category}":
            raise RuntimeError(f"Unexpected FireRed trainer class: {name}")
        pic = _field(body, "trainerPic")
        if pic != f"TRAINER_PIC_{category}" or pic not in classes:
            raise RuntimeError(f"Unsupported trainer portrait: {name}")
        if f"TRAINER_CLASS_{category}" not in classes:
            raise RuntimeError(f"Missing Emerald trainer class: {category}")
        music = _field(body, "encounterMusic_gender")
        tokens = re.findall(r"[A-Z][A-Z0-9_]+", music)
        if not tokens or any(token not in trainer_text for token in tokens):
            raise RuntimeError(f"Unsupported encounter music/gender: {name}")
        if _field(body, "doubleBattle") != "FALSE":
            raise RuntimeError(f"Double battle not supported in this batch: {name}")
        if _field(body, "aiFlags") != "AI_SCRIPT_CHECK_BAD_MOVE":
            raise RuntimeError(f"Unexpected AI definition for {name}")
        if not re.search(r"\.items\s*=\s*\{\s*\}", body):
            raise RuntimeError(f"Source trainer items unsupported: {name}")

        source_party = re.search(
            r"\.party\s*=\s*NO_ITEM_DEFAULT_MOVES\((\w+)\)", body)
        if not source_party:
            raise RuntimeError(f"Unsupported original party type: {name}")
        old_party = source_party.group(1)
        party = re.search(
            r"static const struct TrainerMonNoItemDefaultMoves\s+"
            + re.escape(old_party) + r"\[\]\s*=\s*\{([\s\S]*?)\n\};",
            source_parties,
        )
        if not party:
            raise RuntimeError(f"FireRed party missing: {old_party}")
        party_body = party.group(1)
        species = re.findall(r"\bSPECIES_[A-Z0-9_]+\b", party_body)
        if (not species or not re.search(r"\.lvl\s*=\s*\d+", party_body)
                or any(item not in valid_species for item in species)):
            raise RuntimeError(f"Invalid original species/levels: {name}")

        original = [
            obj for obj in source_maps[area]["object_events"]
            if obj.get("script") == old_label
            and obj.get("trainer_type") == "TRAINER_TYPE_NORMAL"
            and obj.get("graphics_id") == f"OBJ_EVENT_GFX_{category}"
        ]
        if len(original) != 1:
            raise RuntimeError(f"FireRed actor missing/ambiguous: {area}:{name}")
        obj = original[0]
        if obj["graphics_id"] not in graphics:
            raise RuntimeError(f"Emerald graphics missing: {obj['graphics_id']}")
        if any(v["x"] == obj["x"] and v["y"] == obj["y"]
               for v in maps[area]["object_events"]):
            raise RuntimeError(f"NPC overlap in {area}: {name}")

        new_macro = f"TRAINER_KANTO_V20_{category}_{name.upper()}"
        new_party = f"sParty_KantoV20{category.title().replace('_', '')}{name}"
        flag = f"FLAG_KANTO_V20_TRAINER_{name.upper()}"
        script = f"Kanto_{area}_EventScript_V20{name}"
        flag_n = FLAG_START + i
        maps[area]["object_events"].append({
            key: obj[key] for key in (
                "graphics_id", "x", "y", "elevation", "movement_type",
                "movement_range_x", "movement_range_y", "trainer_type",
                "trainer_sight_or_berry_tree_id")
        } | {"script": script, "flag": "0"})
        intro = f"Kanto_{area}_Text_V20{name}Intro"
        defeat = f"Kanto_{area}_Text_V20{name}Defeat"
        after = f"Kanto_{area}_Text_V20{name}After"
        scripts[area] += f"""
{script}::
    trainerbattle_single {new_macro}, {intro}, {defeat}
    msgbox {after}, MSGBOX_AUTOCLOSE
    end

{intro}:
    .string "Let's see your POKeMON!$"

{defeat}:
    .string "Good battle!$"

{after}:
    .string "I'll keep training!$"
"""
        added_macros.append(f"#define {new_macro:<48} {BASE_ID + i}\n")
        added_flags.append(
            f"#define {flag:<48} FLAG_UNUSED_0x{flag_n:03X}\n")
        flag_cases.append(f"    case {new_macro}:\n        return {flag};\n")
        party_defs.append(
            f"static const struct TrainerMonNoItemDefaultMoves {new_party}[] = {{"
            + party_body + "\n};\n")
        trainer_defs.append(f"""    [{new_macro}] =
    {{
        .trainerClass = TRAINER_CLASS_{category},
        .encounterMusic_gender = {music},
        .trainerPic = {pic},
        .trainerName = _("{name.upper()}"),
        .items = {{}},
        .doubleBattle = FALSE,
        .aiFlags = AI_SCRIPT_CHECK_BAD_MOVE,
        .party = NO_ITEM_DEFAULT_MOVES({new_party}),
    }},
""")
        rows.append({
            "name": name, "map": f"Kanto_{area}", "category": category,
            "trainer_id": BASE_ID + i, "symbol": new_macro,
            "source_trainer": old_macro, "source_party": old_party,
            "party": new_party, "flag": flag, "flag_value": flag_n,
            "event": script, "position": [obj["x"], obj["y"]],
            "source_graphics_id": obj["graphics_id"],
        })

    # No source mutation until every trainer, collision and flag was checked.
    for area in maps:
        emit_json(map_paths[area] / "map.json", maps[area])
        (map_paths[area] / "scripts.inc").write_text(
            scripts[area], encoding="utf-8")
    opp_path.write_text(opp.replace(
        "#define TRAINERS_COUNT                      877",
        "".join(added_macros) + f"#define TRAINERS_COUNT                      {BASE_ID + len(ROSTER)}"),
        encoding="utf-8")
    footer = "#endif // GUARD_CONSTANTS_FLAGS_H"
    if flags.count(footer) != 1:
        raise RuntimeError("flags.h include guard changed")
    flags_path.write_text(
        flags.replace(footer, "// V0.20 - saved, non-daily victories\n"
                      + "".join(added_flags) + "\n" + footer),
        encoding="utf-8")
    parties_path.write_text(
        party_text.rstrip() + "\n\n" + "\n".join(party_defs),
        encoding="utf-8")
    index = trainer_text.rfind("};")
    trainer_path.write_text(
        trainer_text[:index] + "\n" + "\n".join(trainer_defs)
        + trainer_text[index:], encoding="utf-8")
    battle_path.write_text(
        battle.replace("    default:\n        return TRAINER_FLAGS_START + trainerId;",
                       "".join(flag_cases)
                       + "    default:\n        return TRAINER_FLAGS_START + trainerId;"),
        encoding="utf-8")
    return {"count": len(rows), "trainers": rows,
            "flag_start": FLAG_START, "flag_stop": FLAG_STOP,
            "flags_remaining_in_lane": 0x920 - FLAG_STOP}
