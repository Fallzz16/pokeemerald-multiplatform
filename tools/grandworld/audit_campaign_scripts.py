#!/usr/bin/env python3
"""Audit 24 gym badge awards and 3 League completion seams on pinned World.

Static source-structure evidence only: NOT 24 played victories, cutscene
homologation, or a claim that any of the 105 runtime acceptance cases passed.
"""
from pathlib import Path
import json
import re
import sys

GYMS = {
    "kanto": [
        "PewterCity_Gym_Frlg", "CeruleanCity_Gym_Frlg",
        "VermilionCity_Gym_Frlg", "CeladonCity_Gym_Frlg",
        "FuchsiaCity_Gym_Frlg", "SaffronCity_Gym_Frlg",
        "CinnabarIsland_Gym_Frlg", "ViridianCity_Gym_Frlg",
    ],
    "johto": [
        "VioletCity_Gym", "AzaleaTown_Gym", "GoldenrodCity_Gym",
        "EcruteakCity_Gym", "CianwoodGym", "OlivineCity_Gym",
        "MahoganyTown_Gym", "BlackthornCity_Gym",
    ],
    "hoenn": [
        "RustboroCity_Gym", "DewfordTown_Gym", "MauvilleCity_Gym",
        "LavaridgeTown_Gym_1F", "PetalburgCity_Gym",
        "FortreeCity_Gym", "MossdeepCity_Gym",
        "SootopolisCity_Gym_1F",
    ],
}

LEAGUE_PATHS = {
    "kanto": (
        "data/maps/PokemonLeague_ChampionsRoom_Frlg/scripts.inc",
        "data/maps/PokemonLeague_HallOfFame_Frlg/scripts.inc",
        "data/scripts/hall_of_fame_frlg.inc",
        "FLAG_KANTO_CHAMPION",
        "MAP_POKEMON_LEAGUE_HALL_OF_FAME",
    ),
    "johto": (
        "data/maps/JohtoPokemonLeague_ChampionsRoom/scripts.inc",
        "data/maps/JohtoPokemonLeague_HallOfFame/scripts.inc",
        "data/maps/JohtoPokemonLeague_HallOfFame/scripts.inc",
        "FLAG_JOHTO_CHAMPION",
        "MAP_JOHTO_POKEMON_LEAGUE_HALL_OF_FAME",
    ),
    "hoenn": (
        "data/maps/EverGrandeCity_ChampionsRoom/scripts.inc",
        "data/maps/EverGrandeCity_HallOfFame/scripts.inc",
        "data/scripts/hall_of_fame.inc",
        "FLAG_HOENN_CHAMPION",
        "MAP_EVER_GRANDE_CITY_HALL_OF_FAME",
    ),
}


def badge_path(region, index):
    # Clair's Rising Badge is legitimately awarded AFTER the Gym in the
    # Dragon's Den Shrine. Checking Blackthorn gym for the setflag would be a
    # false failure; treating its Gym visit alone as badge earned is worse.
    if region == "johto" and index == 8:
        return "data/maps/DragonsDen_Shrine/scripts.inc"
    return "data/maps/" + GYMS[region][index - 1] + "/scripts.inc"


def flag_name(region, index):
    return {
        "kanto": f"FLAG_KANTO_BADGE_{index}",
        "johto": f"FLAG_JOHTO_BADGE_{index}",
        "hoenn": f"FLAG_BADGE{index:02d}_GET",
    }[region]


def audit(world: Path):
    includes = (world / "data/event_scripts.s").read_text(encoding="utf-8")
    badges = []
    for region, gym_names in GYMS.items():
        if len(gym_names) != 8:
            raise ValueError(region + ": expected 8 canonical gyms")
        for index, gym in enumerate(gym_names, 1):
            gym_source = "data/maps/" + gym + "/scripts.inc"
            award_path = badge_path(region, index)
            for path in (gym_source, award_path):
                # The code being audited must be linked in game event scripts.
                if f'.include "{path}"' not in includes:
                    raise ValueError(f"unlinked map script: {path}")
            script = (world / award_path).read_text(encoding="utf-8")
            flag = flag_name(region, index)
            awards = re.findall(r"(?m)^\s*setflag\s+" + re.escape(flag) + r"\s*$", script)
            if len(awards) != 1:
                raise ValueError(f"{region} badge {index}: {flag} setflag found {len(awards)} times")
            badges.append({
                "region": region, "badge": index, "gym_script": gym_source,
                "badge_award_script": award_path, "flag": flag,
                "source_verified": True, "gameplay_verified": False,
            })
    leagues = []
    for region, (room_path, hall_path, champion_path, flag, warp) in LEAGUE_PATHS.items():
        for path in (room_path, hall_path, champion_path):
            if not (world / path).is_file():
                raise ValueError(f"missing {region} championship source: {path}")
            # All mapped Hall-of-Fame and champion-room scripts are linked by
            # event_scripts; other direct script includes are linked elsewhere.
            if path.startswith("data/maps/") and f'.include "{path}"' not in includes:
                raise ValueError(f"unlinked league source: {path}")
        room = (world / room_path).read_text(encoding="utf-8")
        hall = (world / hall_path).read_text(encoding="utf-8")
        champion = (world / champion_path).read_text(encoding="utf-8")
        if warp not in room:
            raise ValueError(f"{region}: champion room lacks Hall of Fame transition")
        if "HALL_OF_FAME_RECORD" not in hall:
            raise ValueError(f"{region}: Hall of Fame record event absent")
        if len(re.findall(r"(?m)^\s*setflag\s+" + re.escape(flag) + r"\s*$", champion)) != 1:
            # Johto deliberately has initial-clear and rematch branches that
            # both set this same champion flag in different script blocks.
            if region != "johto" or len(re.findall(
                r"(?m)^\s*setflag\s+" + re.escape(flag) + r"\s*$", champion
            )) != 2:
                raise ValueError(f"{region}: champion completion flag must be set explicitly")
        leagues.append({
            "region": region, "champion_room": room_path,
            "hall_of_fame": hall_path, "champion_flag": flag,
            "source_verified": True, "gameplay_verified": False,
        })
    if len(badges) != 24 or len(leagues) != 3:
        raise ValueError("source count drift")
    return {
        "kind": "static source audit; not gameplay QA",
        "badges": badges, "leagues": leagues,
        "badge_awards_found": len(badges), "league_paths_found": len(leagues),
        "release_approved": False,
    }


if __name__ == "__main__":
    try:
        if len(sys.argv) not in (2, 3):
            raise ValueError("usage: audit_campaign_scripts.py /isolated/world [output.json]")
        report = audit(Path(sys.argv[1]))
        if len(sys.argv) == 3:
            Path(sys.argv[2]).write_text(json.dumps(report, indent=2) + "\n")
        print(f"Static source paths: {report['badge_awards_found']}/24 badge awards, "
              f"{report['league_paths_found']}/3 Leagues; gameplay unverified")
    except (ValueError, OSError, UnicodeError) as exc:
        sys.exit("FAIL CLOSED: " + str(exc))
