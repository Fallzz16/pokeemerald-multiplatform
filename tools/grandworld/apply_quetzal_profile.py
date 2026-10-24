#!/usr/bin/env python3
"""M8 opt-in profile: grass-only wild encounters and budgeted adaptive shadows.

Designed for a pinned isolated PKMN-World checkout after the PR #70 optimizer.
No edits to SaveBlock, maps, encounter tables, trainer data, or releases.
Every source anchor is checked before any file is changed.
"""
import argparse
import json
from pathlib import Path

OWE_ON = "#define WE_OW_ENCOUNTERS                        TRUE"
OWE_OFF = "#define WE_OW_ENCOUNTERS                        FALSE"
RANDOM_ON = "#define WE_VANILLA_RANDOM           TRUE"
SHADOW_VANILLA = "#define OW_OBJECT_VANILLA_SHADOWS      TRUE"
SHADOW_ALL = "#define OW_OBJECT_VANILLA_SHADOWS      FALSE"

# One cleanup pass is allowed; later frames avoid expensive spawn-header checks.
UPDATE_OLD = """void UpdateOverworldWildEncounter(void)
{
    //Check if possible to spawn.

    bool32 shouldSpawnWaterMons = ShouldSpawnWaterOWE();"""
UPDATE_NEW = """void UpdateOverworldWildEncounter(void)
{
    // Grand World grass-only: let the original code clear any generated objects
    // once, then skip the rest of the unused overworld-spawn path every frame.
    if (!WE_OW_ENCOUNTERS && sOWESpawnCountdown == OWE_NO_ENCOUNTER_SET)
        return;

    //Check if possible to spawn.

    bool32 shouldSpawnWaterMons = ShouldSpawnWaterOWE();"""

SHADOW_START = """static bool32 TryCreateShadowFieldEffect(void)
{
    u8 objectEventId;
    const struct ObjectEventGraphicsInfo *graphicsInfo;
    u8 spriteId;
    s32 i;
    for (i = MAX_SPRITES - 1; i > -1; i--) // Search backwards, because of CreateSpriteAtEnd
    {
        // Return early if a shadow sprite already exists"""
SHADOW_START_NEW = """static bool32 TryCreateShadowFieldEffect(void)
{
    u8 objectEventId;
    const struct ObjectEventGraphicsInfo *graphicsInfo;
    u8 spriteId;
    s32 i;
    s32 usedSprites = 0;
    for (i = MAX_SPRITES - 1; i > -1; i--) // Search backwards, because of CreateSpriteAtEnd
    {
        // Count slots in the duplicate-shadow scan: no second sprite traversal.
        if (gSprites[i].inUse)
            usedSprites++;
        // Return early if a shadow sprite already exists"""

SHADOW_OBJECT = """    objectEventId = GetObjectEventIdByLocalIdAndMap(gFieldEffectArguments[0], gFieldEffectArguments[1], gFieldEffectArguments[2]);
    // The overworld-flight pair carries its own dedicated ground shadow; the"""
SHADOW_OBJECT_NEW = """    objectEventId = GetObjectEventIdByLocalIdAndMap(gFieldEffectArguments[0], gFieldEffectArguments[1], gFieldEffectArguments[2]);
    // Grand World: reserve engine sprite slots for essential field effects.
    // Player/follower shadows have priority. Existing shadows remain alive;
    // skip only new shadow allocation under pressure, avoiding OAM churn.
    // These numbers are hypotheses, NOT measured FPS or optimal thresholds.
    if (usedSprites >= MAX_SPRITES -
        ((gObjectEvents[objectEventId].isPlayer
          || gObjectEvents[objectEventId].localId == OBJ_EVENT_ID_FOLLOWER) ? 4 : 12))
        return FALSE;
    // The overworld-flight pair carries its own dedicated ground shadow; the"""


def exact(text, old, new, name):
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{name}: expected one exact source anchor; found {count}")
    return text.replace(old, new, 1)


def plan(root):
    root = Path(root)
    wild_cfg = root / "include/config/wild_encounter.h"
    ow_cfg = root / "include/config/overworld.h"
    wild_src = root / "src/wild_encounter_ow.c"
    effect_src = root / "src/field_effect_helpers.c"
    paths = [wild_cfg, ow_cfg, wild_src, effect_src]
    original = {p: p.read_text(encoding="utf-8") for p in paths}
    if original[wild_cfg].count(RANDOM_ON) != 1:
        raise ValueError("vanilla grass random encounters not enabled or config changed")
    if original[ow_cfg].count("#define OW_GFX_COMPRESS                FALSE") != 1:
        raise ValueError("graphics VRAM policy drifted; refusing experimental profile")
    if "if (ArePlayerFieldControlsLocked() || FlagGet(DN_FLAG_SEARCHING)" not in original[wild_src]:
        raise ValueError("unexpected overworld encounter source; refusing profile")
    # PR #70 must be applied first; this prevents accidental patch on another version.
    if "     || FlagGet(DN_FLAG_SEARCHING)\n     || (gMapHeader.mapLayoutId" in original[wild_src]:
        raise ValueError("PR #70 fast path is missing; apply baseline M8 patch first")
    changed = {
        wild_cfg: exact(original[wild_cfg], OWE_ON, OWE_OFF, "grass-only"),
        ow_cfg: exact(original[ow_cfg], SHADOW_VANILLA, SHADOW_ALL, "adaptive shadow config"),
        wild_src: exact(original[wild_src], UPDATE_OLD, UPDATE_NEW, "grass-only fast path"),
        effect_src: exact(
            exact(original[effect_src], SHADOW_START, SHADOW_START_NEW, "shadow budget count"),
            SHADOW_OBJECT, SHADOW_OBJECT_NEW, "shadow budget allocation gate"
        ),
    }
    return [(p, original[p], changed[p]) for p in paths]


def apply(root, write=False):
    edits = plan(root)  # Fail closed before writing any file.
    changed = []
    if write:
        try:
            for path, before, after in edits:
                path.write_text(after, encoding="utf-8")
                changed.append((path, before))
        except OSError:
            for path, before in reversed(changed):
                path.write_text(before, encoding="utf-8")
            raise
    return {
        "mode": "applied" if write else "preflight",
        "changes": [str(p.relative_to(root)) for p, _, _ in edits],
        "vanilla_random_grass": True,
        "generated_overworld_encounters": False,
        "adaptive_shadows": "opt-in; player/follower reserve 4 sprite slots; normal objects reserve 12",
        "shadow_budget_scan": "reuse existing duplicate-shadow scan",
        "gfx_compression_changed": False,
        "save_layout_changed": False,
        "runtime_fps_measured": False,
        "graphics_prefetch_changed": False,
        "follow_up": "Measure OAM/FPS and only then test cache and 32px prefetch for proven repeated loads.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = apply(args.world, args.apply)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
