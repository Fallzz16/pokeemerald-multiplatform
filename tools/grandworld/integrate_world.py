#!/usr/bin/env python3
"""M8 isolated source integration for pinned PKMN-World.

Runs against an isolated World checkout. Fail-closed exact source patterns, no
SaveBlock/ROM release edits, no multiplayer. Only passes if every seam is found.
"""
from pathlib import Path
import sys
import shutil

OLD_BOX = "    if (target != gCurrentRegion)\n        DepositPartyToPC();"
OLD_GATE = "\tcallnative RegionHub_ScrCanDepositParty\n\tgoto_if_eq VAR_RESULT, FALSE, RegionHub_EventScript_TravelNoRoom\n"
OLD_MSG = r'''	.string "Your current team will be sent to\n"
	.string "the PC BOXES when you switch\l"
	.string "regions, and any MAIL they hold\l"
	.string "moves to your PC mailbox.\p"'''
NEW_MSG = r'''	.string "Your team stays with you when\n"
	.string "you travel between regions.\p"'''
OLD_TOUR = r'''	.string "Your team is sent to the PC BOXES\n"
	.string "whenever you switch regions. The\l"
	.string "BOXES are shared, so nothing is\l"
	.string "ever lost.\p"'''
NEW_TOUR = r'''	.string "Your team stays by your side\n"
	.string "when you switch regions.\p"'''

def replace_exact(text, before, after, n, name):
    count=text.count(before)
    if count!=n:
        raise RuntimeError(f'{name} expected {n} matched {count}; refusing patch')
    return text.replace(before,after)

def integrate(world):
    c=world/'src/region_switch.c'
    s=world/'data/maps/RegionHub/scripts.inc'
    b=world/'src/battle_main.c'
    if any(not p.is_file() for p in (c,s,b,world/'Makefile')):
        raise RuntimeError('not a complete World checkout')
    if 'C_SRCS_IN := $(wildcard $(C_SUBDIR)/*.c' not in (world/'Makefile').read_text():
        raise RuntimeError('automatic source discovery not confirmed')
    source=c.read_text()
    scripts=s.read_text()
    battle=b.read_text()

    source=replace_exact(source,OLD_BOX,
        '    /* Grand World M2: party and held mail travel together. */',
        1,'region party boxing')
    capacity=r'''/* Grand World M2: keep a free slot for a new region's starter.
 * Does not move Pokemon or touch the save. */
void RegionHub_ScrCanCarryToNewRegion(struct ScriptContext *ctx)
{
    u32 target = REGION_KANTO + VarGet(VAR_0x8008);
    bool8 introDone;
    u32 i, filled = 0;
    (void)ctx;
    gSpecialVar_Result = FALSE;
    if (target < REGION_KANTO || target > REGION_HOENN)
        return;
    if (target == REGION_KANTO)
        introDone = gSaveBlock2Ptr->kantoIntroDone;
    else if (target == REGION_JOHTO)
        introDone = gSaveBlock2Ptr->johtoIntroDone;
    else
        introDone = gSaveBlock2Ptr->hoennIntroDone;
    if (introDone)
    {
        gSpecialVar_Result = TRUE;
        return;
    }
    for (i = 0; i < PARTY_SIZE; ++i)
        if (GetMonData(&gParties[B_TRAINER_PLAYER][i], MON_DATA_SPECIES) != SPECIES_NONE)
            ++filled;
    gSpecialVar_Result = filled < PARTY_SIZE;
}

'''
    source=replace_exact(source,
        'void RegionHub_ScrTargetIsCurrent(struct ScriptContext *ctx)',
        capacity+'void RegionHub_ScrTargetIsCurrent(struct ScriptContext *ctx)',
        1,'region native entry')
    scripts=replace_exact(scripts,OLD_GATE,'',3,'obsolete PC capacity gate')
    scripts=replace_exact(scripts,OLD_MSG,NEW_MSG,3,'regional travel text')
    scripts=replace_exact(scripts,OLD_TOUR,NEW_TOUR,1,'hub tour text')
    for target in (0,1,2):
        anchor=f'\tsetvar VAR_RESULT, {target}\n\tcallnative RegionHub_ScrEnterRegion'
        patched=('\tcallnative RegionHub_ScrCanCarryToNewRegion\n'
                 '\tgoto_if_eq VAR_RESULT, FALSE, RegionHub_EventScript_TravelNoRoom\n'
                 +anchor)
        scripts=replace_exact(scripts,anchor,patched,1,f'gate {target} travel')
    a=scripts.index('RegionHub_Text_TravelNoRoom:')
    d=scripts.index('\nRegionHub_Text_TravelKantoSame:',a)
    scripts=scripts[:a]+r'''RegionHub_Text_TravelNoRoom:
	.string "Please leave one free spot\n"
	.string "in your party before starting\l"
	.string "a new regional journey.\p"
	.string "Your other POKeMON remain\n"
	.string "with you during travel.$"
'''+scripts[d:]

    old='            CreateMon(&party[i], partyData[monIndex].species, partyData[monIndex].lvl, personalityValue, otId);'
    new=('            u8 battleLevel = partyData[monIndex].lvl;\n'
         '#if ALL_REGIONS\n'
         '            /* Skip scripted rental player parties. */\n'
         '            if (party != gParties[B_TRAINER_PLAYER])\n'
         '                battleLevel = GrandWorld_AdjustTrainerLevel(battleLevel);\n'
         '#endif\n'
         '            CreateMon(&party[i], partyData[monIndex].species, battleLevel, personalityValue, otId);')
    battle=replace_exact(battle,old,new,1,'trainer creation site')
    battle=replace_exact(battle,'#include "global.h"',
                         '#include "global.h"\n#include "grandworld_balance.h"',
                         1,'trainer source header')
    assets=Path(__file__).resolve().parent
    extras={
        world/'src/grandworld_balance.c':(assets/'grandworld_balance.c').read_bytes(),
        world/'include/grandworld_balance.h':(assets/'grandworld_balance.h').read_bytes()
    }
    for p in extras:
        if p.exists():
            raise RuntimeError(f'existing file collision: {p}')
    # Fail closed before any modification, then atomically install pre-rendered
    # files with rollback on disk error or interruption. A previous .gw-original
    # backup is never silently overwritten.
    import os
    import tempfile
    updated = {c: source.encode(), s: scripts.encode(), b: battle.encode()}
    updated.update(extras)
    original_paths = (c, s, b)
    backup_paths = {p: p.with_name(p.name + '.gw-original') for p in original_paths}
    for p in original_paths:
        if backup_paths[p].exists():
            raise RuntimeError(f'existing backup: {backup_paths[p]}')
    staged = {}
    try:
        for p, data in updated.items():
            fd, tmp = tempfile.mkstemp(prefix=p.name + '.gw-stage-', dir=p.parent)
            staged[p] = Path(tmp)
            with os.fdopen(fd, 'wb') as out:
                out.write(data)
        for p in original_paths:
            shutil.copy2(p, backup_paths[p])
        try:
            for p, stage in staged.items():
                os.replace(stage, p)
        except Exception:
            for p in original_paths:
                if backup_paths[p].exists():
                    shutil.copy2(backup_paths[p], p)
            for p in extras:
                if p.exists():
                    p.unlink()
            raise
    finally:
        for stage in staged.values():
            if stage.exists():
                stage.unlink()
    print('Patched 5 World files; party stays intact, intro capacity guarded, NPC levels scale.')
    print('Save format and multiplayer unaffected. Full GBA build, field and starter tests mandatory.')

if __name__=='__main__':
    try:
        if len(sys.argv)!=2:
            raise RuntimeError('usage: integrate_world.py /path/to/isolated/World')
        integrate(Path(sys.argv[1]).resolve())
    except Exception as e:
        sys.exit(f'FAIL-CLOSED: {e}')
