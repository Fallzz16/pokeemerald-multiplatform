#!/usr/bin/env python3
"""Read-only mGBA diagnostic counters injected into the disposable pinned World checkout.

Only use after normal M8 integration, OWE palette patch and the test-only C
symbol export. Never apply to stable M8, PR #102, or a shipping ROM.
"""
import argparse
import json
from pathlib import Path

DECL_OLD = "EWRAM_DATA u8 sOWESpawnCountdown = 0;"
DECL_NEW = """EWRAM_DATA u8 sOWESpawnCountdown = 0;
// Experimental QA only. Counters are read by Lua, never written by it.
// [0] frames, [1] field/DexNav lock, [2] no land header, [3] feature/area off,
// [4] countdown ticks, [5] moving player, [6] no free generated slot,
// [7] incompatible water state, [8] rejected candidate spawn tile,
// [9] invalid/filtered wild species, [10] insufficient graphics resources,
// [11] spawned real overworld object.
EWRAM_DATA u16 gM9OWEProbe[12];
"""

EARLY_OLD = """    bool32 shouldSpawnWaterMons;
    if (ArePlayerFieldControlsLocked() || FlagGet(DN_FLAG_SEARCHING))
        return;
    shouldSpawnWaterMons = ShouldSpawnWaterOWE();
    if (!CheckCurrentWildMonHeaderForOWE(shouldSpawnWaterMons))
        return;
"""
EARLY_NEW = """    bool32 shouldSpawnWaterMons;
    gM9OWEProbe[0]++;
    if (ArePlayerFieldControlsLocked() || FlagGet(DN_FLAG_SEARCHING))
    {
        gM9OWEProbe[1]++;
        return;
    }
    shouldSpawnWaterMons = ShouldSpawnWaterOWE();
    if (!CheckCurrentWildMonHeaderForOWE(shouldSpawnWaterMons))
    {
        gM9OWEProbe[2]++;
        return;
    }
"""

DISABLE_OLD = """     || InTrainerHillChallenge())
    {
        if (sOWESpawnCountdown != OWE_NO_ENCOUNTER_SET)"""
DISABLE_NEW = """     || InTrainerHillChallenge())
    {
        gM9OWEProbe[3]++;
        if (sOWESpawnCountdown != OWE_NO_ENCOUNTER_SET)"""

TICK_OLD = """    if (sOWESpawnCountdown)
    {
        sOWESpawnCountdown--;
        return;
    }"""
TICK_NEW = """    if (sOWESpawnCountdown)
    {
        gM9OWEProbe[4]++;
        sOWESpawnCountdown--;
        return;
    }"""

MOVING_OLD = """    if (player->currentCoords.x != player->previousCoords.x || player->currentCoords.y != player->previousCoords.y)
        return;"""
MOVING_NEW = """    if (player->currentCoords.x != player->previousCoords.x || player->currentCoords.y != player->previousCoords.y)
    {
        gM9OWEProbe[5]++;
        return;
    }"""

TILE_OLD = """    if (spawnSlot == OWE_INVALID_SPAWN_SLOT
     || (shouldSpawnWaterMons && AreLegendariesInSootopolisPreventingEncounters())
     || !TrySelectTileForOWE(&x, &y))
    {
        SetMinimumOWESpawnTimer();
        return;
    }"""
TILE_NEW = """    if (spawnSlot == OWE_INVALID_SPAWN_SLOT)
    {
        gM9OWEProbe[6]++;
        SetMinimumOWESpawnTimer();
        return;
    }
    if (shouldSpawnWaterMons && AreLegendariesInSootopolisPreventingEncounters())
    {
        gM9OWEProbe[7]++;
        SetMinimumOWESpawnTimer();
        return;
    }
    if (!TrySelectTileForOWE(&x, &y))
    {
        gM9OWEProbe[8]++;
        SetMinimumOWESpawnTimer();
        return;
    }"""

GRAPHICS_OLD = """    if (infoOWE.speciesId == SPECIES_NONE
     || (WE_OWE_SPECIAL_ONLY && infoOWE.category >= OWE_CATEGORY_WILD)
     || !IsWildLevelAllowedByRepel(infoOWE.level)
     || !IsAbilityAllowingEncounter(infoOWE.level)
     || !CheckCanLoadOWE(infoOWE.speciesId, infoOWE.isFemale, infoOWE.isShiny, x, y))
    {
        SetMinimumOWESpawnTimer();
        return;
    }"""
GRAPHICS_NEW = """    if (infoOWE.speciesId == SPECIES_NONE
     || (WE_OWE_SPECIAL_ONLY && infoOWE.category >= OWE_CATEGORY_WILD)
     || !IsWildLevelAllowedByRepel(infoOWE.level)
     || !IsAbilityAllowingEncounter(infoOWE.level))
    {
        gM9OWEProbe[9]++;
        SetMinimumOWESpawnTimer();
        return;
    }
    if (!CheckCanLoadOWE(infoOWE.speciesId, infoOWE.isFemale, infoOWE.isShiny, x, y))
    {
        gM9OWEProbe[10]++;
        SetMinimumOWESpawnTimer();
        return;
    }"""

SUCCESS_OLD = """    ObjectEventTurn(owe, gStandardDirections[Random() & 3]);
    SetNewOWESpawnCountdown();"""
SUCCESS_NEW = """    ObjectEventTurn(owe, gStandardDirections[Random() & 3]);
    gM9OWEProbe[11]++;
    SetNewOWESpawnCountdown();"""

REPLACEMENTS = (
    (DECL_OLD, DECL_NEW),
    (EARLY_OLD, EARLY_NEW),
    (DISABLE_OLD, DISABLE_NEW),
    (TICK_OLD, TICK_NEW),
    (MOVING_OLD, MOVING_NEW),
    (TILE_OLD, TILE_NEW),
    (GRAPHICS_OLD, GRAPHICS_NEW),
    (SUCCESS_OLD, SUCCESS_NEW),
)


def transform(source):
    # All anchors must match before a single file is written.
    for label, (before, after) in enumerate(REPLACEMENTS):
        if source.count(before) != 1:
            raise ValueError(f"pinned World OWE trace anchor {label} not unique")
        if after in source and after != before:
            raise ValueError(f"OWE trace anchor {label} already applied")
    for before, after in REPLACEMENTS:
        source = source.replace(before, after, 1)
    return source


def run(world, apply=False):
    world = Path(world)
    if not (world / "Makefile").is_file():
        raise ValueError("expected full pinned World checkout")
    config = (world / "include/config/wild_encounter.h").read_text(encoding="utf-8")
    if "#define WE_OW_ENCOUNTERS                        TRUE" not in config:
        raise ValueError("OWE configuration disabled")
    path = world / "src/wild_encounter_ow.c"
    old = path.read_text(encoding="utf-8")
    new = transform(old)
    if apply:
        path.write_text(new, encoding="utf-8")
    return {"mode": "applied" if apply else "preflight", "counter_fields": 12,
            "actual_gameplay_approved": False, "ROM_distributed": False}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("world", type=Path)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    result = run(args.world, args.apply)
    payload = json.dumps(result, indent=2) + "\n"
    if args.report:
        args.report.write_text(payload, encoding="utf-8")
    print(payload, end="")
