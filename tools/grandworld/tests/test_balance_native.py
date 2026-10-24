"""Compile and exercise the *actual* GrandWorld NPC difficulty C code on host.

This tests the pure level-scaling function with stubbed GBA state; it does not
claim battle-engine, trainer-party, or cartridge gameplay certification.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GLOBAL = r"""
#ifndef GRANDWORLD_TEST_GLOBAL
#define GRANDWORLD_TEST_GLOBAL
typedef unsigned char u8;
typedef unsigned char bool8;
#define PARTY_SIZE 6
#define B_TRAINER_PLAYER 0
enum Region { REGION_NONE, REGION_KANTO, REGION_JOHTO, REGION_HOENN };
struct Pokemon { unsigned species, level; };
struct SaveBlock2 { bool8 optionsHardMode; };
extern struct Pokemon gParties[1][PARTY_SIZE];
extern struct SaveBlock2 *gSaveBlock2Ptr;
enum { MON_DATA_SPECIES=1, MON_DATA_LEVEL=2 };
enum { SPECIES_NONE=0, SPECIES_EGG=1 };
enum Region GetActiveRegion(void);
int HasBadge(enum Region region, unsigned badge);
unsigned GetMonData(struct Pokemon *mon, int what);
#endif
"""
DRIVER = r"""
#include "global.h"
#include "grandworld_balance.h"
struct Pokemon gParties[1][PARTY_SIZE];
static struct SaveBlock2 opts;
struct SaveBlock2 *gSaveBlock2Ptr = &opts;
static enum Region currentRegion;
static unsigned badges[4][8];
enum Region GetActiveRegion(void) { return currentRegion; }
int HasBadge(enum Region region, unsigned i) { return badges[region][i] != 0; }
unsigned GetMonData(struct Pokemon *mon, int what)
{
    return what == MON_DATA_SPECIES ? mon->species : mon->level;
}
static int check(const char *name, unsigned actual, unsigned expected)
{
    if (actual != expected) { printf("%s: actual=%u expected=%u\n", name, actual, expected); return 1; }
    return 0;
}
#include <stdio.h>
#include <string.h>
int main(void)
{
    int failed = 0;
    currentRegion = REGION_KANTO;
    failed += check("no playable party", GrandWorld_AdjustTrainerLevel(10), 10);
    gParties[0][0].species = SPECIES_EGG;
    gParties[0][0].level = 100;
    failed += check("egg excluded", GrandWorld_AdjustTrainerLevel(10), 10);
    gParties[0][0].species = 25;
    gParties[0][0].level = 50;
    failed += check("new game per-region ceiling", GrandWorld_AdjustTrainerLevel(5), 13);
    gParties[0][0].level = 20;
    for (int i=0;i<4;++i) badges[REGION_JOHTO][i] = 1;
    failed += check("four foreign badges floor", GrandWorld_AdjustTrainerLevel(10), 15);
    opts.optionsHardMode = 1;
    failed += check("challenge mode one-level bonus", GrandWorld_AdjustTrainerLevel(10), 16);
    opts.optionsHardMode = 0;
    gParties[0][0].level = 100;
    for (int i=0;i<8;++i) { badges[REGION_JOHTO][i]=1; badges[REGION_HOENN][i]=1; }
    failed += check("foreign badge ceiling", GrandWorld_AdjustTrainerLevel(10), 45);
    failed += check("scripted level 65 preserved", GrandWorld_AdjustTrainerLevel(65), 65);
    failed += check("invalid level zero preserved", GrandWorld_AdjustTrainerLevel(0), 0);
    currentRegion = REGION_NONE;
    failed += check("invalid region unchanged", GrandWorld_AdjustTrainerLevel(10), 10);
    return failed ? 1 : 0;
}
"""


class BalanceNativeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("cc"), "native C compiler unavailable")
    def test_actual_balance_c_with_game_like_state(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)
            (p / "global.h").write_text(GLOBAL)
            for name in ("event_data.h", "regions.h", "pokemon.h"):
                (p / name).write_text('#include "global.h"\n')
            (p / "constants").mkdir()
            (p / "constants/pokemon.h").write_text('#include "global.h"\n')
            (p / "driver.c").write_text(DRIVER)
            binary = p / "balance_test"
            cmd = ["cc", "-std=c99", "-DALL_REGIONS=1", "-Wall", "-Wextra",
                   "-Werror", "-I", str(p), "-I", str(ROOT),
                   str(ROOT / "grandworld_balance.c"), str(p / "driver.c"),
                   "-o", str(binary)]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            subprocess.run([str(binary)], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
