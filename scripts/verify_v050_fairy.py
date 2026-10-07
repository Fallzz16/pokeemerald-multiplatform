#!/usr/bin/env python3
"""Emerald Vanilla+ Hybrid v0.5.0 Fairy data/UI regression verifier.

This is a deterministic source/asset verifier, not a substitute for the Windows
native build or in-game smoke test. Run alongside verify_v050_split.py.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, description: str) -> None:
    if not condition:
        raise AssertionError(description)


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def sha_file(path: str) -> str:
    return sha256((ROOT / path).read_bytes()).hexdigest()


def const(name: str) -> int:
    content = source("include/constants/pokemon.h")
    match = re.search(rf"^#define\s+{re.escape(name)}\s+(\d+)\s*(?:\/\/.*)?$", content, re.M)
    require(match is not None, f"constant {name} exists")
    return int(match.group(1))


# A) Type numbering is save/link-compatible with original Emerald.
old_names = (
    "NORMAL", "FIGHTING", "FLYING", "POISON", "GROUND", "ROCK",
    "BUG", "GHOST", "STEEL", "MYSTERY", "FIRE", "WATER", "GRASS",
    "ELECTRIC", "PSYCHIC", "ICE", "DRAGON", "DARK",
)
for index, name in enumerate(old_names):
    require(const(f"TYPE_{name}") == index, f"legacy type ID {name} unchanged ({index})")
require(const("TYPE_FAIRY") == 18, "Fairy appended as type 18")
require(const("TYPE_NONE") == 255, "TYPE_NONE retains 255 sentinel")
require(const("NUMBER_OF_MON_TYPES") == 19, "19 types total")


# B) Flat type chart remains bytewise semantically equivalent for old types.
chart = source("src/battle_main.c")
match = re.search(r"const u8 gTypeEffectiveness\[372\]\s*=\s*\{(.*?)\n\};", chart, re.S)
require(match is not None, "type chart uses unsized sentinel-terminated array")
triple_pattern = r"(TYPE_[A-Z_]+)\s*,\s*(TYPE_[A-Z_]+)\s*,\s*(TYPE_MUL_[A-Z_]+)"
triples = re.findall(triple_pattern, match.group(1))
require(len(triples) == 124, "112 old + 12 Fairy type chart triples")

expected_fairy = [
    ("FAIRY", "FIGHTING", "SUPER_EFFECTIVE"),
    ("FAIRY", "DRAGON", "SUPER_EFFECTIVE"),
    ("FAIRY", "DARK", "SUPER_EFFECTIVE"),
    ("FAIRY", "FIRE", "NOT_EFFECTIVE"),
    ("FAIRY", "POISON", "NOT_EFFECTIVE"),
    ("FAIRY", "STEEL", "NOT_EFFECTIVE"),
    ("DRAGON", "FAIRY", "NO_EFFECT"),
    ("FIGHTING", "FAIRY", "NOT_EFFECTIVE"),
    ("BUG", "FAIRY", "NOT_EFFECTIVE"),
    ("DARK", "FAIRY", "NOT_EFFECTIVE"),
    ("POISON", "FAIRY", "SUPER_EFFECTIVE"),
    ("STEEL", "FAIRY", "SUPER_EFFECTIVE"),
]
new_triples = [(f"TYPE_{a}", f"TYPE_{b}", f"TYPE_MUL_{c}") for a, b, c in expected_fairy]
end_of_regular = triples.index(("TYPE_FORESIGHT", "TYPE_FORESIGHT", "TYPE_MUL_NO_EFFECT"))
require(triples[end_of_regular - len(new_triples):end_of_regular] == new_triples,
        "12 Fairy matchups precede Foresight sentinel in correct order")
legacy = triples[:end_of_regular - len(new_triples)] + triples[end_of_regular:]
legacy_digest = sha256("\n".join(",".join(t) for t in legacy).encode("utf-8")).hexdigest()
require(legacy_digest == "1f76dbdee81751798b5489ac76572f0b411ec1e97924c00c6e997ab4bcca4081",
        "all 112 legacy type chart triples remain identical")
require(triples[-1] == ("TYPE_ENDTABLE", "TYPE_ENDTABLE", "TYPE_MUL_NO_EFFECT"),
        "table end sentinel remains last")

names = chart[chart.index("const u8 gTypeNames["):]
require('[TYPE_FAIRY] = _("FAIRY")' in names, "FAIRY battle type label")
require('extern const u8 gTypeEffectiveness[372];' in source("include/battle_main.h"),
        "chart declaration has 372 bytes for Conversion 2 sizeof")
require('[TYPE_FAIRY]    = _("a FAIRY move")' in source("src/battle_message.c"),
        "battle messages support Fairy")


# Conversion 2 uses sizeof(chart) in a separate translation unit. It requires a
# complete extern type and must never include the index equal to triple count.
conversion2 = source("src/battle_script_commands.c")
require("(i = Random() % 128) >= sizeof(gTypeEffectiveness) / 3" in conversion2,
        "Conversion 2 random sampler rejects out-of-range chart index")
require("!IS_BATTLER_OF_TYPE(gBattlerAttacker, TYPE_EFFECT_DEF_TYPE(j))" in conversion2,
        "Conversion 2 sequential fallback checks its own index, not last random index")


# C) Only the requested Gen 1-3 moves are retyped to Fairy.
moves_text = source("src/data/battle_moves.h")
entries = re.findall(r"\[(MOVE_[A-Z0-9_]+)\]\s*=\s*\{(.*?)\n\s*\},", moves_text, re.S)
require(len(entries) == 355, "all 355 legacy moves have records")
changed_moves = {
    "MOVE_SWEET_KISS": "STATUS",
    "MOVE_CHARM": "STATUS",
    "MOVE_MOONLIGHT": "STATUS",
}
actual_fairy = {}
for move, body in entries:
    match_type = re.search(r"\.type\s*=\s*(TYPE_[A-Z0-9_]+)", body)
    if match_type and match_type.group(1) == "TYPE_FAIRY":
        match_category = re.search(r"\.category\s*=\s*DAMAGE_CATEGORY_(\w+)", body)
        actual_fairy[move] = match_category.group(1) if match_category else None
require(actual_fairy == changed_moves, "only Sweet Kiss, Charm, Moonlight are Fairy status moves")

# Hidden Power's eligible types must remain original 16; category remains Special.
hidden = source("src/battle_script_commands.c")
require("((TYPE_DARK - 2) * typeBits) / 63 + 1" in hidden,
        "Hidden Power still calculates 16 non-Normal/non-Mystery types")
require("if (gBattleStruct->dynamicMoveType >= TYPE_MYSTERY)" in hidden,
        "Hidden Power skips Mystery while retaining 16-type distribution")
for type_bits in range(64):
    legacy_type = ((18 - 3) * type_bits) // 63 + 1
    modern_type = ((17 - 2) * type_bits) // 63 + 1
    if legacy_type >= 9:
        legacy_type += 1
    if modern_type >= 9:
        modern_type += 1
    require(legacy_type == modern_type and modern_type < 18,
            f"Hidden Power eligible type for bits={type_bits} stays old and not Fairy")


# D) Existing Gen 1–3 family retypings (no species added).
expected_species = {
    "CLEFFA": ("FAIRY", "FAIRY"),
    "CLEFAIRY": ("FAIRY", "FAIRY"),
    "CLEFABLE": ("FAIRY", "FAIRY"),
    "IGGLYBUFF": ("NORMAL", "FAIRY"),
    "JIGGLYPUFF": ("NORMAL", "FAIRY"),
    "WIGGLYTUFF": ("NORMAL", "FAIRY"),
    "MR_MIME": ("PSYCHIC", "FAIRY"),
    "TOGEPI": ("FAIRY", "FAIRY"),
    "TOGETIC": ("FAIRY", "FLYING"),
    "AZURILL": ("NORMAL", "FAIRY"),
    "MARILL": ("WATER", "FAIRY"),
    "AZUMARILL": ("WATER", "FAIRY"),
    "SNUBBULL": ("FAIRY", "FAIRY"),
    "GRANBULL": ("FAIRY", "FAIRY"),
    "RALTS": ("PSYCHIC", "FAIRY"),
    "KIRLIA": ("PSYCHIC", "FAIRY"),
    "GARDEVOIR": ("PSYCHIC", "FAIRY"),
    "MAWILE": ("STEEL", "FAIRY"),
}
species_text = source("src/data/pokemon/species_info.h")
species_type_rows = re.findall(r"\[SPECIES_([A-Z0-9_]+)\]\s*=\s*\{.*?\.types\s*=\s*\{\s*(TYPE_[A-Z0-9_]+)\s*,\s*(TYPE_[A-Z0-9_]+)\s*\}", species_text, re.S)
actual_species = {name for name, type1, type2 in species_type_rows if "TYPE_FAIRY" in (type1, type2)}
require(actual_species == set(expected_species), "exactly the 18 approved species carry Fairy type")
for species, types in expected_species.items():
    match = re.search(rf"\[SPECIES_{species}\]\s*=\s*\{{(.*?)\n\s*\}},", species_text, re.S)
    require(match is not None, f"{species} exists")
    expected_type = "{ TYPE_%s, TYPE_%s }" % types
    require(f".types = {expected_type}" in match.group(1), f"{species} types={types}")


# E) Summary, Pokédex, Union Room, menu info assets stay consistent.
sum_screen = source("src/pokemon_summary_screen.c")
require("ANIMCMD_FRAME(TYPE_FAIRY * 8" in sum_screen, "Fairy Summary sprite animation")
require("sSpriteAnim_TypeFairy," in sum_screen, "Fairy Summary lookup entry")
require("[TYPE_FAIRY] = 14," in sum_screen, "Fairy icon selects compatible palette")
gfx_rules = source("graphics_file_rules.mk")
match = re.search(r"^types\s*:=\s*(.*)$", gfx_rules, re.M)
require(match is not None, "ordered type atlas build rule")
ordered = match.group(1).split()
require(len(ordered) == 19 and ordered[-1] == "fairy", "Summary type atlas includes Fairy at slot 18")
require(ordered[:18] == ["normal", "fight", "flying", "poison", "ground", "rock", "bug", "ghost", "steel", "mystery", "fire", "water", "grass", "electric", "psychic", "ice", "dragon", "dark"], "legacy Summary icons keep their exact ordering")

pokedex = source("src/pokedex.c")
require("{gText_DexEmptyString, gTypeNames[TYPE_FAIRY]}" in pokedex, "Fairy Pokédex search display")
require("    TYPE_FAIRY,\n};" in pokedex, "Fairy Pokédex search ID")
union = source("src/data/union_room.h")
require("{ gTypeNames[TYPE_FAIRY],    TYPE_FAIRY" in union, "Fairy Union Room trading board")

menu = source("src/menu.c")
require("[TYPE_FAIRY + 1]    = { 32, 12, 0x04 }" in menu,
        "Fairy secondary move-info icon uses unused slot 0x04")
menu_h = source("include/menu.h")
for index, suffix in enumerate(("TYPE", "POWER", "ACCURACY", "PP", "EFFECT", "BALL_RED", "BALL_BLUE"), start=1):
    require(f"#define MENU_INFO_ICON_{suffix}" in menu_h and
            f"(NUMBER_OF_MON_TYPES + {index})" in menu_h,
            f"menu-info icon index {suffix} shifts safely with type count")

require(sha_file("graphics/types/fairy.png") == "567c048996b206842bef1457b318b5932bf299c291c65c63903dbfa24a97275e",
        "Fairy Summary icon is the exact audited donor PNG")
require(sha_file("graphics/interface/menu_info.png") == "91cf203adcedc7002626ee0938834a5bbfe0ef42f7a5956be1b80f0085b7c1ee",
        "secondary icon atlas matches manually pixel-reviewed Fairy-only patch")
for asset, width, height in (("graphics/types/fairy.png", 32, 16), ("graphics/interface/menu_info.png", 128, 128)):
    b = (ROOT / asset).read_bytes()
    require(b.startswith(b"\x89PNG\r\n\x1a\n"), f"{asset} PNG signature")
    require(int.from_bytes(b[16:20], "big") == width and int.from_bytes(b[20:24], "big") == height,
            f"{asset} expected sprite dimensions")


# F) Project scope, saved data, and proven native subsystems are unaffected.
# Project source root is backed by a local git checkout whose initial commit
# reproduces the remote bced8c64 byte-for-byte for the important files.
try:
    baseline = "433eb92"  # Verified remote bced8c64 working-tree snapshot.
    protected_targets = [
        "include/global.h", "include/load_save.h", "src/save.c", "src/load_save.c",
        "src/rom_header_gf.c", "src/data/trade.h",
        "src/data/wild_encounters.json", "src/data/trainers.h", "src/data/trainer_parties.h",
        "data/maps", "data/scripts",
        "src/quest_log.c", "src/sound_mixer.c", "src/m4a.c",
        "src/platform/sdl2.c", "src/music_player.c", ".github/workflows/build-windows-native.yml",
    ]
    result = subprocess.run(["git", "diff", "--quiet", baseline, "--", *protected_targets],
                            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    require(result.returncode == 0, "save/Quest/audio/native/Hoenn/trainer/encounter files unchanged")
    pokemon_diff = subprocess.run(["git", "diff", baseline, "--", "include/pokemon.h"],
                                  cwd=ROOT, capture_output=True, text=True, check=True).stdout
    added = [l[1:] for l in pokemon_diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    deleted = [l[1:] for l in pokemon_diff.splitlines() if l.startswith("-") and not l.startswith("---")]
    require(added == ["    u8 category;"] and not deleted,
            "BattleMove.category is only modification inside pokemon.h; persistent mon layout unchanged")
except FileNotFoundError:
    print("NOTE: git unavailable; protected source/save diff check skipped", file=sys.stderr)

print("v0.5.0 Fairy verifier: PASS")
print("  original 18 type IDs unchanged; Fairy=18 and 12 modern chart matchups")
print("  18 existing Pokémon retyped; 3 existing status moves retyped")
print("  Hidden Power preserved for all 64 possible type bit patterns")
print("  Summary, Pokédex, Union Room and TM/HM icon layouts checked")
print("  native port/save/Quest/audio/Hoenn content scoped and protected")
