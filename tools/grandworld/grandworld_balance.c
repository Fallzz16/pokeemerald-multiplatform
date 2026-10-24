/* Grand World M4: on-the-fly NPC trainer level scaling in Pokémon World.
 * Preserves original species, moves, items, natures and trainer party templates.
 * No SaveBlock changes. Do not apply to the player's scripted rental party.
 */
#include "global.h"
#include "grandworld_balance.h"
#include "event_data.h"
#include "regions.h"
#include "pokemon.h"
#include "constants/pokemon.h"

#if ALL_REGIONS
u8 GrandWorld_AdjustTrainerLevel(u8 baseLevel)
{
    enum Region active = GetActiveRegion();
    unsigned otherBadges = 0;
    unsigned partyTotal = 0, partyCount = 0, partyMax = 0;
    unsigned progressFloor, teamFloor, target, ceiling;
    unsigned region, i;
    bool8 challenge = gSaveBlock2Ptr->optionsHardMode;

    if (baseLevel < 1 || baseLevel >= 65)
        return baseLevel;
    if (active < REGION_KANTO || active > REGION_HOENN)
        return baseLevel;

    for (region = REGION_KANTO; region <= REGION_HOENN; ++region)
        for (i = 0; i < 8; ++i)
            if (region != (unsigned)active && HasBadge((enum Region)region, i))
                ++otherBadges;

    for (i = 0; i < PARTY_SIZE; ++i)
    {
        struct Pokemon *mon = &gParties[B_TRAINER_PLAYER][i];
        unsigned species = GetMonData(mon, MON_DATA_SPECIES);
        unsigned level;
        if (species == SPECIES_NONE || species == SPECIES_EGG)
            continue;
        level = GetMonData(mon, MON_DATA_LEVEL);
        if (level == 0 || level > 100)
            continue;
        partyTotal += level;
        if (level > partyMax)
            partyMax = level;
        ++partyCount;
    }
    if (partyCount == 0)
        return baseLevel;

    progressFloor = baseLevel;
    if (otherBadges != 0)
    {
        unsigned floor = 7 + otherBadges * 2;
        if (floor > progressFloor)
            progressFloor = floor;
    }
    teamFloor = partyTotal / partyCount;
    teamFloor = teamFloor > (challenge ? 5u : 8u)
        ? teamFloor - (challenge ? 5u : 8u) : 1;
    if (partyMax > teamFloor + 18 && teamFloor < progressFloor)
        teamFloor = progressFloor;
    target = progressFloor > teamFloor ? progressFloor : teamFloor;
    if (target < baseLevel)
        target = baseLevel;
    ceiling = baseLevel + (otherBadges ? 35u : 8u);
    if (ceiling > 100)
        ceiling = 100;
    if (target > ceiling)
        target = ceiling;
    if (challenge && target < ceiling && otherBadges)
        target += 1;
    return (u8)target;
}
#else
u8 GrandWorld_AdjustTrainerLevel(u8 baseLevel)
{
    return baseLevel;
}
#endif
