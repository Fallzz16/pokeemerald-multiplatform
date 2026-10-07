#!/usr/bin/env python3
"""Compile and run the REAL CalculateBaseDamage function with tiny mocked battle state.

Designed to catch regressions in Gen4 damage categories independently of the
Windows x86 runtime. It is a host-only arithmetic unit test, not an end-to-end
battle or game launch test. Requires a host C compiler (gcc).
"""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / 'src/pokemon.c').read_text(encoding='utf-8')
start = text.index('#define APPLY_STAT_MOD')
end = text.index('\nu8 CountAliveMonsInBattle', start)
body = text[start:end]

# The source-provided table is adapted selectively: we only inject the types,
# categories and powers used in this experiment, never reimplement damage logic.
moves_src = (ROOT / 'src/data/battle_moves.h').read_text(encoding='utf-8')
wanted = [
    'MOVE_FIRE_PUNCH','MOVE_FLAMETHROWER','MOVE_SHADOW_BALL','MOVE_BITE',
    'MOVE_CRUNCH','MOVE_HYPER_BEAM','MOVE_HIDDEN_POWER','MOVE_WEATHER_BALL',
    'MOVE_WATERFALL', 'MOVE_ROCK_SLIDE',
]
info=[]
for move in wanted:
    match = re.search(rf'\[{move}\]\s*=\s*\{{(.*?)\n\s*\}},', moves_src, re.S)
    assert match, f'Move {move} missing'
    block = match.group(1)
    fields={}
    for field in ('power','type','category','target','effect'):
        m=re.search(rf'\.{field}\s*=\s*([A-Z0-9_]+)',block)
        if m: fields[field]=m.group(1)
    assert all(x in fields for x in ('power','type','category'))
    power = fields['power'] if fields['power'].isdigit() else '50'
    info.append(f'    [{move}] = {{ .power={power}, .type={fields["type"]}, .category={fields["category"]}, .target=0, .effect=0 }},')

header=r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define ARRAY_COUNT(a) (sizeof(a)/sizeof(a[0]))
#include "constants/moves.h"
#include "constants/pokemon.h"
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int32_t s32;
#define SIDE_STATUS_REFLECT 1
#define SIDE_STATUS_LIGHTSCREEN 2
#define STATUS1_BURN 1
#define BATTLE_TYPE_DOUBLE (1<<1)
#define BATTLE_TYPE_FRONTIER (1<<2)
#define ITEM_ENIGMA_BERRY 10
#define FLAG_BADGE01_GET 1
#define FLAG_BADGE05_GET 2
#define FLAG_BADGE07_GET 3
#define ABILITY_HUGE_POWER 2
#define ABILITY_PURE_POWER 3
#define ABILITY_THICK_FAT 4
#define ABILITY_HUSTLE 5
#define ABILITY_PLUS 6
#define ABILITY_MINUS 7
#define ABILITY_GUTS 8
#define ABILITY_MARVEL_SCALE 9
#define ABILITY_OVERGROW 10
#define ABILITY_BLAZE 11
#define ABILITY_TORRENT 12
#define ABILITY_SWARM 13
#define HOLD_EFFECT_CHOICE_BAND 30
#define HOLD_EFFECT_SOUL_DEW 31
#define HOLD_EFFECT_DEEP_SEA_TOOTH 32
#define HOLD_EFFECT_DEEP_SEA_SCALE 33
#define HOLD_EFFECT_LIGHT_BALL 34
#define HOLD_EFFECT_METAL_POWDER 35
#define HOLD_EFFECT_THICK_CLUB 36
#define SPECIES_LATIAS 200
#define SPECIES_LATIOS 201
#define SPECIES_CLAMPERL 202
#define SPECIES_PIKACHU 203
#define SPECIES_DITTO 204
#define SPECIES_CUBONE 205
#define SPECIES_MAROWAK 206
#define ABILITYEFFECT_FIELD_SPORT 10
#define ABILITYEFFECT_MUD_SPORT 11
#define ABILITYEFFECT_WATER_SPORT 12
#define B_WEATHER_RAIN_TEMPORARY (1<<0)
#define B_WEATHER_RAIN (1<<0)
#define B_WEATHER_SANDSTORM (1<<1)
#define B_WEATHER_HAIL (1<<2)
#define B_WEATHER_SUN (1<<3)
#define WEATHER_HAS_EFFECT2 1
#define RESOURCE_FLAG_FLASH_FIRE 1
#define EFFECT_EXPLOSION 1
#define MOVE_TARGET_BOTH 2
#define DYNAMIC_TYPE_MASK 0x3F
#define ABILITY_ON_FIELD2(x) 0
#define APPLY_STAT_MOD_ORIGINAL 1
struct BattlePokemon {
    u16 attack, defense, spAttack, spDefense;
    u16 hp, maxHP, item, species;
    u8 ability, level;
    u32 status1;
    u8 statStages[8];
};
struct BattleMove {
    u8 effect, power, type, category, target;
};
struct Berry { u8 holdEffect, holdEffectParam; };
struct BattleResourceFlags { u32 flags[4]; };
struct BattleResources { struct BattleResourceFlags *flags; };
const struct BattleMove gBattleMoves[355] = {
'''
footer =r'''
};
const u8 gStatStageRatios[13][2] = {
   {1,1},{1,1},{1,1},{1,1},{1,1},{1,1},{1,1},{1,1},
   {1,1},{1,1},{1,1},{1,1},{1,1},
};
const u8 sHoldEffectToType[1][2] = {{42,TYPE_FIRE}};
struct Berry gEnigmaBerries[4] = {{0}};
struct BattleResourceFlags flags_ = {{0}};
struct BattleResources resources_ = { &flags_ };
struct BattleResources *gBattleResources = &resources_;
u32 gBattleTypeFlags = 0, gBattleWeather = 0;
u16 gCurrentMove = MOVE_NONE, gBattleMovePower = 0;
u8 gCritMultiplier = 1;
u8 GetItemHoldEffect(u16 item) { return item == 2 ? 42 : 0; }
u8 GetItemHoldEffectParam(u16 item) { return item == 2 ? 20 : 0; }
int ShouldGetStatBadgeBoost(int flag, int battler) { (void)flag; (void)battler; return 0; }
int AbilityBattleEffects(int a,int b,int c,int d,int e) { (void)a;(void)b;(void)c;(void)d;(void)e; return 0; }
u8 CountAliveMonsInBattle(int kind) { (void)kind; return 1; }
'''
main=r'''
#define CHECK_EQ(got,want,title) do { if ((got)!=(want)) { fprintf(stderr,"FAIL %s: got %d want %d\n",title,got,want); return 1; } checks++; } while(0)
#define CHECK_TRUE(x,title) do { if (!(x)) {fprintf(stderr,"FAIL %s\n",title);return 1;}checks++; } while(0)
static void init_mons(struct BattlePokemon *a, struct BattlePokemon *d) {
    memset(a,0,sizeof(*a));memset(d,0,sizeof(*d));
    a->level=50;a->hp=100;a->maxHP=100;
    a->attack=160; a->spAttack=60;a->defense=100;a->spDefense=100;
    d->attack=100;d->spAttack=100;d->defense=100;d->spDefense=110;
    for(int i=0;i<8;i++){a->statStages[i]=6;d->statStages[i]=6;}
    gBattleWeather=0;gBattleTypeFlags=0;flags_.flags[0]=0;
}
static s32 calc(struct BattlePokemon*a,struct BattlePokemon*d,int move,int side,int override) {
    gCurrentMove=move;
    return CalculateBaseDamage(a,d,move,side,move==MOVE_HIDDEN_POWER ? 60 : 0,override,0,1);
}
int main(void) {
    int checks=0;
    struct BattlePokemon a,d;init_mons(&a,&d);
    int firep=calc(&a,&d,MOVE_FIRE_PUNCH,0,0);
    int flam=calc(&a,&d,MOVE_FLAMETHROWER,0,0);
    CHECK_TRUE(firep>flam,"Fire Punch uses strong physical Attack, Flamethrower weak SpAtk");
    int darkp=calc(&a,&d,MOVE_BITE,0,0);
    int darkp2=calc(&a,&d,MOVE_CRUNCH,0,0);
    int ghostsp=calc(&a,&d,MOVE_SHADOW_BALL,0,0);
    CHECK_TRUE(darkp>0 && darkp2>0 && ghostsp>0,"Gen3 Dark/Ghost switches stat route");
    CHECK_TRUE(calc(&a,&d,MOVE_HYPER_BEAM,0,0)>0,"Hyper Beam Special yields damage");
    CHECK_TRUE(calc(&a,&d,MOVE_HIDDEN_POWER,0,TYPE_FIRE)>0,"Hidden Power Fire uses Special");
    CHECK_TRUE(calc(&a,&d,MOVE_WEATHER_BALL,0,TYPE_ROCK)>0,"Weather Ball Rock uses Special");
    int bite_reference=calc(&a,&d,MOVE_BITE,0,0);
    int crunch_reference=calc(&a,&d,MOVE_CRUNCH,0,0);
    int shadow_reference=calc(&a,&d,MOVE_SHADOW_BALL,0,0);
    int hyper_reference=calc(&a,&d,MOVE_HYPER_BEAM,0,0);
    int hidden_reference=calc(&a,&d,MOVE_HIDDEN_POWER,0,TYPE_FIRE);
    int weather_reference=calc(&a,&d,MOVE_WEATHER_BALL,0,TYPE_ROCK);
    int waterfall_reference=calc(&a,&d,MOVE_WATERFALL,0,0);
    a.attack=20;a.spAttack=260;
    CHECK_TRUE(calc(&a,&d,MOVE_BITE,0,0)<bite_reference,"Bite truly uses Attack, not SpAtk");
    CHECK_TRUE(calc(&a,&d,MOVE_CRUNCH,0,0)<crunch_reference,"Crunch truly uses Attack, not SpAtk");
    CHECK_TRUE(calc(&a,&d,MOVE_SHADOW_BALL,0,0)>shadow_reference,"Shadow Ball truly uses SpAtk, not Attack");
    CHECK_TRUE(calc(&a,&d,MOVE_HYPER_BEAM,0,0)>hyper_reference,"Hyper Beam truly uses SpAtk, not Attack");
    CHECK_TRUE(calc(&a,&d,MOVE_HIDDEN_POWER,0,TYPE_FIRE)>hidden_reference,"Hidden Power Fire remains Special under dynamic type");
    CHECK_TRUE(calc(&a,&d,MOVE_WEATHER_BALL,0,TYPE_ROCK)>weather_reference,"Weather Ball Rock remains Special under dynamic type");
    a.attack=160;a.spAttack=60;

    a.item=2;
    CHECK_TRUE(calc(&a,&d,MOVE_FIRE_PUNCH,0,0)>firep,"Fire type held item boosts physical Fire Punch via Attack");
    CHECK_TRUE(calc(&a,&d,MOVE_FLAMETHROWER,0,0)>flam,"Fire type held item boosts special Flamethrower via SpAtk");
    a.item=0;

    a.status1=STATUS1_BURN;
    CHECK_EQ(calc(&a,&d,MOVE_FIRE_PUNCH,0,0),(firep-2)/2+2,"Burn halves Physical Fire Punch");
    CHECK_EQ(calc(&a,&d,MOVE_FLAMETHROWER,0,0),flam,"Burn leaves Special Flamethrower unchanged");
    a.status1=0;
    CHECK_EQ(calc(&a,&d,MOVE_FIRE_PUNCH,SIDE_STATUS_REFLECT,0),(firep-2)/2+2,"Reflect halves Physical Fire Punch");
    CHECK_EQ(calc(&a,&d,MOVE_FLAMETHROWER,SIDE_STATUS_REFLECT,0),flam,"Reflect leaves Flamethrower unchanged");
    CHECK_EQ(calc(&a,&d,MOVE_FLAMETHROWER,SIDE_STATUS_LIGHTSCREEN,0),(flam-2)/2+2,"Light Screen halves Special Flamethrower");
    CHECK_EQ(calc(&a,&d,MOVE_FIRE_PUNCH,SIDE_STATUS_LIGHTSCREEN,0),firep,"Light Screen leaves Physical Fire Punch unchanged");

    d.ability=ABILITY_THICK_FAT;
    CHECK_TRUE(calc(&a,&d,MOVE_FIRE_PUNCH,0,0)<firep,"Thick Fat reduces Physical Fire Punch");
    CHECK_TRUE(calc(&a,&d,MOVE_FLAMETHROWER,0,0)<flam,"Thick Fat reduces Special Flamethrower");
    d.ability=0;

    gBattleWeather=B_WEATHER_RAIN_TEMPORARY;
    CHECK_EQ(calc(&a,&d,MOVE_FIRE_PUNCH,0,0),(firep-2)/2+2,"Rain halves Physical Fire Punch");
    CHECK_TRUE(calc(&a,&d,MOVE_WATERFALL,0,0)>waterfall_reference,"Rain boosts Physical Waterfall");
    gBattleWeather=B_WEATHER_SUN;
    CHECK_TRUE(calc(&a,&d,MOVE_FIRE_PUNCH,0,0)>firep,"Sun boosts Physical Fire Punch");
    CHECK_TRUE(calc(&a,&d,MOVE_FLAMETHROWER,0,0)>flam,"Sun boosts Special Flamethrower");
    CHECK_TRUE(calc(&a,&d,MOVE_WATERFALL,0,0)<waterfall_reference,"Sun weakens Physical Waterfall");
    gBattleWeather=0;
    flags_.flags[0]=RESOURCE_FLAG_FLASH_FIRE;
    CHECK_TRUE(calc(&a,&d,MOVE_FIRE_PUNCH,0,0)>firep,"Flash Fire boosts Physical Fire Punch");
    CHECK_TRUE(calc(&a,&d,MOVE_FLAMETHROWER,0,0)>flam,"Flash Fire boosts Special Flamethrower");
    printf("v0.5.0 actual CalculateBaseDamage test: PASS (%d assertions)\n",checks);
    return 0;
}
'''
ccode = header + '\n'.join(info) + footer + body + main
with tempfile.TemporaryDirectory(prefix='emerald-v050-damage-') as d:
    cpath=Path(d)/'test.c'
    opath=Path(d)/'test'
    cpath.write_text(ccode,encoding='utf-8')
    proc=subprocess.run(['gcc','-std=gnu99','-O0','-iquote',str(ROOT/'include'),'-Wno-trigraphs','-Wall','-Wextra','-o',str(opath),str(cpath)],capture_output=True,text=True)
    if proc.returncode:
        print(proc.stderr[-6000:])
        raise SystemExit('Could not compile host damage test harness')
    proc=subprocess.run([str(opath)],capture_output=True,text=True)
    print(proc.stdout,end='')
    if proc.returncode:
        print(proc.stderr)
        raise SystemExit('Host damage test failed')
