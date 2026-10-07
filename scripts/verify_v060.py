#!/usr/bin/env python3
"""v0.6.0 QoL targeted source/integration guard; native build QA remains required."""
from pathlib import Path
import re
from hashlib import sha1

ROOT=Path(__file__).resolve().parents[1]
def src(p): return (ROOT/p).read_text(encoding="utf-8")
def ok(test,what):
    if not test: raise AssertionError(what)

def contains(path,*checks):
    s=src(path)
    for c in checks: ok(c in s,f"{path}: missing {c}")
    return s

party=contains("src/party_menu.c",'void ItemUseCB_TMHM','static void Task_LearnedMove')
tm=party[party.index('static void Task_LearnedMove(u8 taskId)'):party.index('static void Task_DoLearnedMoveFanfareAfterText')]
ok('RemoveBagItem' not in tm,"TMs must not be consumed on success")
contains('src/field_player_avatar.c','FlagGet(FLAG_SYS_B_DASH)','IsRunningDisallowed(')
run=contains('src/bike.c','bool32 IsRunningDisallowed(u8 metatile)')
ok('!gMapHeader.allowRunning ||' not in run[run.index('bool32 IsRunningDisallowed('):], "indoor running restriction removed without bypassing metatile")
item=contains('src/data/items.h','[ITEM_LINK_CABLE]','ItemUseOutOfBattle_EvolutionStone','sLinkCableDesc')
ok(re.search(r'\[ITEM_LINK_CABLE\][\s\S]{0,300}\.price = 2500',item),"Link Cable sold")
contains('data/maps/PetalburgCity_Mart/scripts.inc','PetalburgCity_Mart_Pokemart_Expanded:', '.short ITEM_LINK_CABLE')
contains('src/data/pokemon/item_effects.h','gItemEffect_LinkCable','[ITEM_LINK_CABLE - ITEM_POTION]')
contains('src/data/item_icon_table.h','[ITEM_LINK_CABLE]')
evo=contains('src/pokemon.c','evolutionItem == ITEM_LINK_CABLE','method == EVO_TRADE_ITEM && requirement == heldItem')
check_block=evo[evo.index('case EVO_MODE_ITEM_USE:'):evo.index('return targetSpecies;',evo.index('case EVO_MODE_ITEM_USE:'))]
ok('SetMonData' not in check_block,'previewing evolution must not consume held items')
ok(re.search(r'^#define ITEM_LINK_CABLE 99',src('include/constants/items.h'),re.M), 'Link Cable uses only previously unused item 99')
repel=contains('data/scripts/repel.inc','Text_RepelAskAgain','MSGBOX_YESNO','removeitem ITEM_MAX_REPEL, 1','removeitem ITEM_SUPER_REPEL, 1','removeitem ITEM_REPEL, 1','setvar VAR_REPEL_STEP_COUNT, 250','setvar VAR_REPEL_STEP_COUNT, 200','setvar VAR_REPEL_STEP_COUNT, 100')
for item_name in ('ITEM_MAX_REPEL','ITEM_SUPER_REPEL','ITEM_REPEL'):
    ok(f'checkitem {item_name}' in repel, f'repel reuse checks inventory: {item_name}')
opts=contains('src/option_menu.c','sOptionMenuPage ^= 1','tExpShare','tBattleSpeed','L_BUTTON | R_BUTTON','DrawExtraOptionChoices')
contains('src/battle_message.c','optionsBattleSpeed == 1','optionsBattleSpeed == 2')
ex=contains('src/battle_script_commands.c','gSaveBlock2Ptr->optionsExpShare','Modern mode: participants keep their full share','!gSaveBlock2Ptr->optionsExpShare && holdEffect == HOLD_EFFECT_EXP_SHARE','MON_DATA_IS_EGG')
contains('src/pokemon_summary_screen.c','static void PrintNatureStatLabels(void)','gNatureStatTable[sMonSummaryScreen->summary.nature]','PrintNatureStatLabels();')
contains('src/pokedex.c','typeLine','if (owned && natNum != SPECIES_NONE)','gTypeNames[gSpeciesInfo[natNum].types[0]]','gTypeNames[gSpeciesInfo[natNum].types[1]]')
# Save bitfield fits original unused bits; no struct changes outside the 16-bit option field.
header=src('include/global.h')
opts_block=header[header.index('/*0x14*/ u16 optionsTextSpeed'):header.index('/*0x18*/ struct Pokedex pokedex;')]
widths=[int(x) for x in re.findall(r'\bu16\s+\w+:(\d+)',opts_block)]
ok(widths==[3,5,1,1,1,1,1,2], f'SaveBlock options bit widths changed: {widths}')
ok(sum(widths)==15 and '/*0x18*/ struct Pokedex' in header, 'SaveBlock2 structure byte offsets unchanged')
# Explicitly reviewed protected changes have exact, fixed content hashes.
allow=src('scripts/v060_modified_protected_manifest.tsv').splitlines()
for row in allow:
    if not row or row.startswith('#'):continue
    sha,rel=row.split('\t')
    data=(ROOT/rel).read_bytes(); actual=sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    ok(actual==sha,f'protected v0.6 file changed after QA signoff: {rel}')
print('v0.6.0 targeted QA: PASS')
print('  TM, indoor running, Link Cable, all 3 Repels')
print('  optional shared experience + classic fallback, battle text modes')
print('  Nature colors, owned-Pokemon Dex typings, 15-bit save options')
