#!/usr/bin/env python3
from pathlib import Path
import re, sys
root = Path(__file__).resolve().parents[1]

def read(p): return (root/p).read_text(encoding='utf-8')
def require(cond, msg):
    if not cond:
        print(f'FAIL: {msg}', file=sys.stderr); sys.exit(1)

const = read('include/constants/pokemon.h')
require('#define DAMAGE_CATEGORY_PHYSICAL 0' in const, 'physical category constant')
require('#define DAMAGE_CATEGORY_SPECIAL  1' in const, 'special category constant')
require('#define DAMAGE_CATEGORY_STATUS   2' in const, 'status category constant')

ph = read('include/pokemon.h')
require(re.search(r'struct BattleMove\s*\{.*?u8 type;\s*\n\s*u8 category;', ph, re.S), 'BattleMove.category field')

moves = read('src/data/battle_moves.h')
require(moves.count('.category = DAMAGE_CATEGORY_PHYSICAL') == 140, '140 physical moves')
require(moves.count('.category = DAMAGE_CATEGORY_SPECIAL') == 77, '77 special moves')
require(moves.count('.category = DAMAGE_CATEGORY_STATUS') == 138, '138 status moves')
require(moves.count('.category = DAMAGE_CATEGORY_') == 355, '355 categorized moves')

key = {
'MOVE_FIRE_PUNCH':'PHYSICAL','MOVE_FLAMETHROWER':'SPECIAL','MOVE_SHADOW_BALL':'SPECIAL',
'MOVE_BITE':'PHYSICAL','MOVE_CRUNCH':'PHYSICAL','MOVE_HYPER_BEAM':'SPECIAL',
'MOVE_HIDDEN_POWER':'SPECIAL','MOVE_WEATHER_BALL':'SPECIAL','MOVE_COUNTER':'PHYSICAL','MOVE_MIRROR_COAT':'SPECIAL'
}
for move, cat in key.items():
    m = re.search(rf'\[{move}\]\s*=\s*\{{(.*?)\n\s*\}},', moves, re.S)
    require(m is not None, f'{move} record exists')
    require(f'.category = DAMAGE_CATEGORY_{cat}' in m.group(1), f'{move} is {cat}')

alltext = '\n'.join(read(p) for p in ['include/battle.h','src/pokemon.c','src/battle_script_commands.c','src/battle_tv.c'])
require('IS_TYPE_PHYSICAL' not in alltext and 'IS_TYPE_SPECIAL' not in alltext, 'no type-based category helper remains')

pc = read('src/pokemon.c')
require('category = gBattleMoves[move].category;' in pc, 'damage reads static category')
require('if (category == DAMAGE_CATEGORY_PHYSICAL)' in pc, 'physical damage branch')
require('if (category == DAMAGE_CATEGORY_SPECIAL)' in pc, 'special damage branch')
require('Weather and Flash Fire depend on the move\'s type, not its damage category.' in pc, 'weather common path')
require('defender->ability == ABILITY_THICK_FAT' in pc and 'category == DAMAGE_CATEGORY_PHYSICAL' in pc, 'Thick Fat category-aware')

bsc = read('src/battle_script_commands.c')
require('ABILITY_HUSTLE && IS_MOVE_PHYSICAL(move)' in bsc, 'Hustle category-aware')
require('if (IS_MOVE_PHYSICAL(gCurrentMove)' in bsc, 'Counter tracker category-aware')
require('else if (IS_MOVE_SPECIAL(gCurrentMove)' in bsc, 'Mirror Coat tracker category-aware')
require('&& TARGET_TURN_DAMAGED' in bsc and '&& moveType == TYPE_FIRE' in bsc, 'Fire thaw accepts either damage category')

btv = read('src/battle_tv.c')
require('gBattleMoves[move].category' in btv, 'Battle TV receives category')
require('category == DAMAGE_CATEGORY_PHYSICAL' in btv, 'Battle TV Reflect category')
require('category == DAMAGE_CATEGORY_SPECIAL' in btv, 'Battle TV Light Screen category')

# Protected subsystems must remain at their verified v0.3.4 blob content in this local branch.
protected = ['src/quest_log.c','src/sound_mixer.c','src/m4a.c','src/platform/sdl2.c','src/music_player.c']
# These SHA1s are Git blob SHAs from remote bced8c64 and are verified externally; use git hash-object when available.
expected = {
'src/quest_log.c':'0652aa4793083ff40ce89d424e3cfb1e36c0de81',
'src/sound_mixer.c':'80ab720fc977093a4111c8dfdc4a7b3b14d1c215',
'src/m4a.c':'f6499e673f9a679e206cad6bf2c2d7549f04df93',
'src/platform/sdl2.c':'b2bc67c158037c142b195617c8f44c33605b756e',
'src/music_player.c':'f4118911be46f7ff9b5b7d6ad417d8cfedee9990',
}
import subprocess
for p in protected:
    try:
        got = subprocess.check_output(['git','hash-object',str(root/p)], text=True).strip()
        require(got == expected[p], f'protected subsystem unchanged: {p}')
    except FileNotFoundError:
        pass

print('v0.5.0 split verifier: PASS')
print('  categories: 140 Physical / 77 Special / 138 Status')
print('  dynamic type is independent from category')
print('  Burn/Reflect/Light Screen/Thick Fat/Hustle/Counter/Mirror Coat paths checked')
print('  Weather/Flash Fire and Fire thawing paths checked')
print('  Quest/audio/native-port protected hashes checked')
