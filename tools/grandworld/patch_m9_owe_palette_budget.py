#!/usr/bin/env python3
"""M9 experimental, fail-closed OWE palette-budget correction for pinned PKMN-World.

Changes exactly two source functions in the temporary World checkout. Does not
alter maps, species, sprites, encounter rates, followers, or any save structure.
Without --apply, this is a strictly read-only preflight.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

HELPER_PATH = "src/event_object_movement.c"
OWE_PATH = "src/wild_encounter_ow.c"

HELPER_OLD = """u16 GetDynamicFollowerPaletteTag(enum Species species, bool32 shiny, bool32 female)
{
    u16 palTag = species + OBJ_EVENT_MON + (shiny ? OBJ_EVENT_MON_SHINY : 0);
#if OW_POKEMON_OBJECT_EVENTS == TRUE && OW_PKMN_OBJECTS_SHARE_PALETTES == FALSE && P_GENDER_DIFFERENCES == TRUE
    // Only claim the female tag if a female palette for *this* shininess actually exists, because
    // that is the sole condition under which the loader below puts female colours in the slot.
    if (female && GetSpeciesOverworldPalette(species, shiny, TRUE) != NULL)
        palTag += OBJ_EVENT_MON_FEMALE;
#endif
    return palTag;
}
"""

HELPER_NEW = """u16 GetDynamicFollowerPaletteTag(enum Species species, bool32 shiny, bool32 female)
{
#if OW_POKEMON_OBJECT_EVENTS == TRUE && OW_PKMN_OBJECTS_SHARE_PALETTES == FALSE
    // Mirror LoadDynamicFollowerPalette: if neither gender-specific nor shared
    // overworld palette exists, it uses the front sprite palette tagged species.
    const void *owPalette = GetSpeciesOverworldPalette(species, shiny, female);
    if (owPalette == NULL)
        owPalette = GetSpeciesOverworldPalette(species, shiny, FALSE);
    if (owPalette == NULL)
        return species;

    u16 palTag = species + OBJ_EVENT_MON + (shiny ? OBJ_EVENT_MON_SHINY : 0);
#if P_GENDER_DIFFERENCES == TRUE
    if (female && GetSpeciesOverworldPalette(species, shiny, TRUE) != NULL)
        palTag += OBJ_EVENT_MON_FEMALE;
#endif
    return palTag;
#else
    // Front-palette-only configurations use bare species as their cache tag.
    return species;
#endif
}
"""

NOTE_OLD = """    // One gap this does NOT close, inherited rather than introduced and out of scope for #78: the
    // helper only produces the standalone-palette tag. A species with no standalone overworld
    // palette at all sends the loader down its front-sprite branch, which caches under bare
    // `speciesId`, so the check below would miss a palette that is in fact resident and refuse the
    // spawn when exactly one slot is free. CheckValidOWESpecies does not require overworld data,
    // so whether any spawnable species is in that state was not settled here.
"""

NOTE_NEW = """    // The shared helper also covers the front-sprite palette fallback, which
    // LoadDynamicFollowerPalette caches under bare speciesId.
"""

PALETTE_OLD = """    // We need at least 2 pal slots open. One for the object and one for the spawn field effect.
    // Add this and tiles to seperate graphics check function
    if (numFreePalSlots == 1)
    {
        u32 metatileBehavior = MapGridGetMetatileBehaviorAt(x, y);
        struct SpritePalette palette = GetOWESpawnDespawnAnimFldEffPalette(GetOWESpawnDespawnAnimType(metatileBehavior));
        // If the mon's palette or field effect palette isn't already loaded, don't spawn.
        // Include check if female or shiny mon is loaded and use that tag if possible
        if (IndexOfSpritePaletteTag(tag) == 0xFF && IndexOfSpritePaletteTag(palette.tag) == 0xFF)
            return FALSE;
    }
    else if (numFreePalSlots == 0)
    {
        return FALSE;
    }

    return TRUE;
"""

PALETTE_NEW = """    // Each distinct missing palette consumes one OBJ palette slot. Existing
    // palettes are reusable even if no slots remain (e.g. a follower of the
    // same species on a crowded route). Never evict an NPC/follower palette.
    u32 metatileBehavior = MapGridGetMetatileBehaviorAt(x, y);
    struct SpritePalette palette = GetOWESpawnDespawnAnimFldEffPalette(GetOWESpawnDespawnAnimType(metatileBehavior));
    u32 slotsNeeded = 0;

    if (IndexOfSpritePaletteTag(tag) == 0xFF)
        slotsNeeded++;
    if (palette.tag != tag && IndexOfSpritePaletteTag(palette.tag) == 0xFF)
        slotsNeeded++;

    // If resources are insufficient, skip this spawn and retry at the existing
    // normal countdown; preserve encounter RNG, movement and battle code.
    return slotsNeeded <= numFreePalSlots;
"""


def _sha(data):
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _require_flag(text, name, expected, path):
    matches = re.findall(r"(?m)^[ \t]*#define[ \t]+" + re.escape(name)
                         + r"[ \t]+([A-Za-z_][A-Za-z_0-9]*)\b", text)
    if matches != [expected]:
        raise ValueError(f"{path}: expected exactly {name}={expected}; saw {matches}")


def prepare(world):
    if not (world / "Makefile").is_file():
        raise ValueError("expected complete World checkout (Makefile missing)")
    for path, flags in {
        "include/config/wild_encounter.h": {"WE_OW_ENCOUNTERS": "TRUE", "WE_VANILLA_RANDOM": "TRUE"},
        "include/config/overworld.h": {"OW_FOLLOWERS_ENABLED": "TRUE", "OW_GFX_COMPRESS": "FALSE"},
    }.items():
        data = (world / path).read_text(encoding="utf-8")
        for name, value in flags.items():
            _require_flag(data, name, value, path)

    originals = {}
    replacements = {}
    for path, chunks in {
        HELPER_PATH: ((HELPER_OLD, HELPER_NEW),),
        OWE_PATH: ((NOTE_OLD, NOTE_NEW), (PALETTE_OLD, PALETTE_NEW)),
    }.items():
        original = (world / path).read_text(encoding="utf-8")
        candidate = original
        for before, after in chunks:
            if candidate.count(before) != 1 or after in candidate:
                raise ValueError(f"{path}: pinned source anchor changed or patch already applied")
            candidate = candidate.replace(before, after, 1)
        originals[path] = original
        replacements[path] = candidate
    return originals, replacements


def run(world, apply=False):
    world = Path(world).resolve()
    originals, replacements = prepare(world)
    if apply:
        for path, content in replacements.items():
            (world / path).write_text(content, encoding="utf-8")
    return {
        "patch": "M9_OWE_PALETTE_BUDGET",
        "mode": "applied" if apply else "preflight",
        "files": {path: {
            "before_sha256": _sha(originals[path]),
            "after_sha256": _sha(replacements[path]),
        } for path in originals},
        "active_owe_cap_changed": False,
        "encounter_rates_changed": False,
        "gameplay_approved": False,
        "mgba_evidence": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = run(args.world, args.apply)
    except (OSError, ValueError, UnicodeError) as error:
        sys.exit("FAIL CLOSED: " + str(error))
    rendered = json.dumps(result, indent=2) + "\n"
    if args.report:
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
