#include "global.h"
#include "event_data.h"
#include "main.h"
#include "menu.h"
#include "quest_log.h"
#include "sound.h"
#include "string_util.h"
#include "text.h"
#include "window.h"
#include "constants/flags.h"
#include "constants/region_map_sections.h"
#include "constants/songs.h"
#include "constants/vars.h"

#define QUESTS_VISIBLE_COMPLETED 6

enum
{
    QUEST_TAB_CURRENT,
    QUEST_TAB_COMPLETED,
};

enum
{
    QUEST_RESCUE_BIRCH,
    QUEST_RIVAL_AND_POKEDEX,
    QUEST_PETALBURG_AND_WALLY,
    QUEST_STONE_BADGE,
    QUEST_RECOVER_DEVON_GOODS,
    QUEST_KNUCKLE_BADGE,
    QUEST_DELIVER_STEVEN_LETTER,
    QUEST_DELIVER_DEVON_GOODS,
    QUEST_DYNAMO_BADGE,
    QUEST_MT_CHIMNEY,
    QUEST_HEAT_BADGE,
    QUEST_BALANCE_BADGE,
    QUEST_WEATHER_INSTITUTE,
    QUEST_DEVON_SCOPE,
    QUEST_FEATHER_BADGE,
    QUEST_MT_PYRE,
    QUEST_MAGMA_HIDEOUT,
    QUEST_SLATEPORT_SUBMARINE,
    QUEST_AQUA_HIDEOUT,
    QUEST_MIND_BADGE,
    QUEST_SPACE_CENTER,
    QUEST_GET_DIVE,
    QUEST_SEAFLOOR_CAVERN,
    QUEST_CAVE_OF_ORIGIN,
    QUEST_AWAKEN_RAYQUAZA,
    QUEST_SOOTOPOLIS_CRISIS,
    QUEST_RAIN_BADGE,
    QUEST_VICTORY_ROAD,
    QUEST_POKEMON_LEAGUE,
    QUEST_COUNT
};

struct MainQuest
{
    const u8 *title;
    const u8 *objective;
    const u8 *location;
    u16 mapSecId;
};

static const struct WindowTemplate sQuestWindowTemplate =
{
    .bg = 0,
    .tilemapLeft = 1,
    .tilemapTop = 1,
    .width = 28,
    .height = 18,
    .paletteNum = 15,
    .baseBlock = 0x139
};

static const u8 sText_QuestLog[] = _("QUEST LOG");
static const u8 sText_TabCurrent[] = _("CURRENT");
static const u8 sText_TabCompleted[] = _("COMPLETED");
static const u8 sText_Objective[] = _("WHAT WAS I DOING?");
static const u8 sText_Location[] = _("NEXT LOCATION");
static const u8 sText_PreviousMilestone[] = _("LAST: ");
static const u8 sText_StoryProgress[] = _("STORY {STR_VAR_1}/{STR_VAR_2}");
static const u8 sText_NoPreviousMilestone[] = _("Your journey has just begun.");
static const u8 sText_StoryComplete[] = _("MAIN STORY COMPLETE!");
static const u8 sText_StoryCompleteDesc[] = _("You became the Pokémon League\nChampion of Hoenn.");
static const u8 sText_NoCompleted[] = _("No main-story milestones completed yet.");
static const u8 sText_Checkmark[] = _("- ");
static const u8 sText_TabCurrentSelected[] = _("> CURRENT");
static const u8 sText_TabCompletedSelected[] = _("> COMPLETED");
static const u8 sText_Showing[] = _("SHOWING {STR_VAR_1}-{STR_VAR_2} OF {STR_VAR_3}");

static const u8 sQuestTitle0[] = _("A PROFESSOR IN TROUBLE");
static const u8 sQuestObjective0[] = _("Find Prof. Birch on Route 101 and\nhelp him escape the wild Pokémon.");
static const u8 sQuestLocation0[] = _("ROUTE 101");
static const u8 sQuestTitle1[] = _("YOUR FIRST RIVAL BATTLE");
static const u8 sQuestObjective1[] = _("Meet your rival on Route 103, then\nreturn to Prof. Birch's lab.");
static const u8 sQuestLocation1[] = _("ROUTE 103 / LITTLEROOT");
static const u8 sQuestTitle2[] = _("A VISIT TO PETALBURG");
static const u8 sQuestObjective2[] = _("Meet your father at Petalburg Gym\nand help Wally catch a Pokémon.");
static const u8 sQuestLocation2[] = _("PETALBURG CITY");
static const u8 sQuestTitle3[] = _("THE STONE BADGE");
static const u8 sQuestObjective3[] = _("Travel through Petalburg Woods and\ndefeat Roxanne at Rustboro Gym.");
static const u8 sQuestLocation3[] = _("RUSTBORO CITY");
static const u8 sQuestTitle4[] = _("STOLEN DEVON GOODS");
static const u8 sQuestObjective4[] = _("Pursue Team Aqua onto Route 116,\nrecover the goods, and return them.");
static const u8 sQuestLocation4[] = _("ROUTE 116 / RUSTURF TUNNEL");
static const u8 sQuestTitle5[] = _("THE KNUCKLE BADGE");
static const u8 sQuestObjective5[] = _("Sail to Dewford and defeat Brawly\nat the Dewford Gym.");
static const u8 sQuestLocation5[] = _("DEWFORD TOWN");
static const u8 sQuestTitle6[] = _("LETTER FOR STEVEN");
static const u8 sQuestObjective6[] = _("Find Steven deep inside Granite Cave\nand deliver Mr. Stone's letter.");
static const u8 sQuestLocation6[] = _("GRANITE CAVE");
static const u8 sQuestTitle7[] = _("DELIVER THE DEVON GOODS");
static const u8 sQuestObjective7[] = _("Sail to Slateport and deliver the\nDevon Goods to Captain Stern.");
static const u8 sQuestLocation7[] = _("SLATEPORT CITY");
static const u8 sQuestTitle8[] = _("THE DYNAMO BADGE");
static const u8 sQuestObjective8[] = _("Continue north to Mauville City and\ndefeat Wattson at the Gym.");
static const u8 sQuestLocation8[] = _("MAUVILLE CITY");
static const u8 sQuestTitle9[] = _("TROUBLE AT MT. CHIMNEY");
static const u8 sQuestObjective9[] = _("Investigate Meteor Falls, then pursue\nthe teams to the top of Mt. Chimney.");
static const u8 sQuestLocation9[] = _("METEOR FALLS / MT. CHIMNEY");
static const u8 sQuestTitle10[] = _("THE HEAT BADGE");
static const u8 sQuestObjective10[] = _("Descend Jagged Pass to Lavaridge\nand defeat Flannery at the Gym.");
static const u8 sQuestLocation10[] = _("LAVARIDGE TOWN");
static const u8 sQuestTitle11[] = _("THE BALANCE BADGE");
static const u8 sQuestObjective11[] = _("Return to Petalburg and challenge\nyour father Norman for a Gym Badge.");
static const u8 sQuestLocation11[] = _("PETALBURG CITY");
static const u8 sQuestTitle12[] = _("STORM AT THE INSTITUTE");
static const u8 sQuestObjective12[] = _("Surf east and travel up Route 119.\nDrive Team Aqua from the institute.");
static const u8 sQuestLocation12[] = _("ROUTE 119");
static const u8 sQuestTitle13[] = _("THE INVISIBLE OBSTACLE");
static const u8 sQuestObjective13[] = _("Find Steven on Route 120 and obtain\nthe device needed to reveal Kecleon.");
static const u8 sQuestLocation13[] = _("ROUTE 120");
static const u8 sQuestTitle14[] = _("THE FEATHER BADGE");
static const u8 sQuestObjective14[] = _("Clear the path into Fortree Gym and\ndefeat Winona.");
static const u8 sQuestLocation14[] = _("FORTREE CITY");
static const u8 sQuestTitle15[] = _("THE ORBS OF MT. PYRE");
static const u8 sQuestObjective15[] = _("Follow Team Aqua to Mt. Pyre and\nlearn what they are planning.");
static const u8 sQuestLocation15[] = _("MT. PYRE");
static const u8 sQuestTitle16[] = _("TEAM MAGMA'S HIDEOUT");
static const u8 sQuestObjective16[] = _("Use the clue from Mt. Pyre to enter\nTeam Magma's hideout at Jagged Pass.");
static const u8 sQuestLocation16[] = _("JAGGED PASS / MAGMA HIDEOUT");
static const u8 sQuestTitle17[] = _("THE STOLEN SUBMARINE");
static const u8 sQuestObjective17[] = _("Return to Slateport Harbor and find\nout what Team Aqua is planning.");
static const u8 sQuestLocation17[] = _("SLATEPORT CITY");
static const u8 sQuestTitle18[] = _("TEAM AQUA'S HIDEOUT");
static const u8 sQuestObjective18[] = _("Search the hideout near Lilycove and\nstop Team Aqua from escaping.");
static const u8 sQuestLocation18[] = _("LILYCOVE CITY");
static const u8 sQuestTitle19[] = _("THE MIND BADGE");
static const u8 sQuestObjective19[] = _("Cross the sea to Mossdeep and defeat\nTate & Liza at the Gym.");
static const u8 sQuestLocation19[] = _("MOSSDEEP CITY");
static const u8 sQuestTitle20[] = _("ATTACK ON THE SPACE CENTER");
static const u8 sQuestObjective20[] = _("Team Magma has invaded Mossdeep's\nSpace Center. Help Steven stop them.");
static const u8 sQuestLocation20[] = _("MOSSDEEP CITY");
static const u8 sQuestTitle21[] = _("THE DEEP SEA");
static const u8 sQuestObjective21[] = _("Visit Steven at his Mossdeep home\nand obtain the HM for Dive.");
static const u8 sQuestLocation21[] = _("MOSSDEEP CITY");
static const u8 sQuestTitle22[] = _("BENEATH ROUTE 128");
static const u8 sQuestObjective22[] = _("Dive on Route 128, locate Seafloor\nCavern, and pursue Team Aqua.");
static const u8 sQuestLocation22[] = _("ROUTE 128 / SEAFLOOR CAVERN");
static const u8 sQuestTitle23[] = _("A CITY IN CRISIS");
static const u8 sQuestObjective23[] = _("Go to Sootopolis, meet Steven, and\nseek Wallace in the Cave of Origin.");
static const u8 sQuestLocation23[] = _("SOOTOPOLIS CITY");
static const u8 sQuestTitle24[] = _("SEEK THE SKY DRAGON");
static const u8 sQuestObjective24[] = _("Travel to Sky Pillar and awaken\nRayquaza before Hoenn is destroyed.");
static const u8 sQuestLocation24[] = _("SKY PILLAR");
static const u8 sQuestTitle25[] = _("RETURN TO SOOTOPOLIS");
static const u8 sQuestObjective25[] = _("Return to Sootopolis and witness the\nend of Groudon and Kyogre's clash.");
static const u8 sQuestLocation25[] = _("SOOTOPOLIS CITY");
static const u8 sQuestTitle26[] = _("THE RAIN BADGE");
static const u8 sQuestObjective26[] = _("Challenge Juan at the Sootopolis Gym\nand earn your eighth Badge.");
static const u8 sQuestLocation26[] = _("SOOTOPOLIS CITY");
static const u8 sQuestTitle27[] = _("VICTORY ROAD");
static const u8 sQuestObjective27[] = _("Travel to Ever Grande, cross Victory\nRoad, and overcome Wally.");
static const u8 sQuestLocation27[] = _("VICTORY ROAD");
static const u8 sQuestTitle28[] = _("THE POKéMON LEAGUE");
static const u8 sQuestObjective28[] = _("Challenge the Elite Four and Champion\nto become Hoenn's new Champion.");
static const u8 sQuestLocation28[] = _("EVER GRANDE CITY");

static const struct MainQuest sMainQuests[QUEST_COUNT] =
{
    [0] = {sQuestTitle0, sQuestObjective0, sQuestLocation0, MAPSEC_ROUTE_101},
    [1] = {sQuestTitle1, sQuestObjective1, sQuestLocation1, MAPSEC_ROUTE_103},
    [2] = {sQuestTitle2, sQuestObjective2, sQuestLocation2, MAPSEC_PETALBURG_CITY},
    [3] = {sQuestTitle3, sQuestObjective3, sQuestLocation3, MAPSEC_RUSTBORO_CITY},
    [4] = {sQuestTitle4, sQuestObjective4, sQuestLocation4, MAPSEC_ROUTE_116},
    [5] = {sQuestTitle5, sQuestObjective5, sQuestLocation5, MAPSEC_DEWFORD_TOWN},
    [6] = {sQuestTitle6, sQuestObjective6, sQuestLocation6, MAPSEC_GRANITE_CAVE},
    [7] = {sQuestTitle7, sQuestObjective7, sQuestLocation7, MAPSEC_SLATEPORT_CITY},
    [8] = {sQuestTitle8, sQuestObjective8, sQuestLocation8, MAPSEC_MAUVILLE_CITY},
    [9] = {sQuestTitle9, sQuestObjective9, sQuestLocation9, MAPSEC_METEOR_FALLS},
    [10] = {sQuestTitle10, sQuestObjective10, sQuestLocation10, MAPSEC_LAVARIDGE_TOWN},
    [11] = {sQuestTitle11, sQuestObjective11, sQuestLocation11, MAPSEC_PETALBURG_CITY},
    [12] = {sQuestTitle12, sQuestObjective12, sQuestLocation12, MAPSEC_ROUTE_119},
    [13] = {sQuestTitle13, sQuestObjective13, sQuestLocation13, MAPSEC_ROUTE_120},
    [14] = {sQuestTitle14, sQuestObjective14, sQuestLocation14, MAPSEC_FORTREE_CITY},
    [15] = {sQuestTitle15, sQuestObjective15, sQuestLocation15, MAPSEC_MT_PYRE},
    [16] = {sQuestTitle16, sQuestObjective16, sQuestLocation16, MAPSEC_MAGMA_HIDEOUT},
    [17] = {sQuestTitle17, sQuestObjective17, sQuestLocation17, MAPSEC_SLATEPORT_CITY},
    [18] = {sQuestTitle18, sQuestObjective18, sQuestLocation18, MAPSEC_AQUA_HIDEOUT},
    [19] = {sQuestTitle19, sQuestObjective19, sQuestLocation19, MAPSEC_MOSSDEEP_CITY},
    [20] = {sQuestTitle20, sQuestObjective20, sQuestLocation20, MAPSEC_MOSSDEEP_CITY},
    [21] = {sQuestTitle21, sQuestObjective21, sQuestLocation21, MAPSEC_MOSSDEEP_CITY},
    [22] = {sQuestTitle22, sQuestObjective22, sQuestLocation22, MAPSEC_SEAFLOOR_CAVERN},
    [23] = {sQuestTitle23, sQuestObjective23, sQuestLocation23, MAPSEC_SOOTOPOLIS_CITY},
    [24] = {sQuestTitle24, sQuestObjective24, sQuestLocation24, MAPSEC_SKY_PILLAR},
    [25] = {sQuestTitle25, sQuestObjective25, sQuestLocation25, MAPSEC_SOOTOPOLIS_CITY},
    [26] = {sQuestTitle26, sQuestObjective26, sQuestLocation26, MAPSEC_SOOTOPOLIS_CITY},
    [27] = {sQuestTitle27, sQuestObjective27, sQuestLocation27, MAPSEC_VICTORY_ROAD},
    [28] = {sQuestTitle28, sQuestObjective28, sQuestLocation28, MAPSEC_EVER_GRANDE_CITY},
};
static u8 sQuestWindowId = WINDOW_NONE;
static u8 sQuestTab = QUEST_TAB_CURRENT;
static u8 sCompletedScroll = 0;

static void PrintText(const u8 *text, u8 x, u8 y, u8 font);

static bool8 IsQuestComplete(u8 questId)
{
    switch (questId)
    {
    case QUEST_RESCUE_BIRCH:
        return FlagGet(FLAG_RESCUED_BIRCH);
    case QUEST_RIVAL_AND_POKEDEX:
        return FlagGet(FLAG_RECEIVED_POKEDEX_FROM_BIRCH);
    case QUEST_PETALBURG_AND_WALLY:
        return VarGet(VAR_PETALBURG_GYM_STATE) >= 2;
    case QUEST_STONE_BADGE:
        return FlagGet(FLAG_BADGE01_GET);
    case QUEST_RECOVER_DEVON_GOODS:
        return FlagGet(FLAG_RETURNED_DEVON_GOODS);
    case QUEST_KNUCKLE_BADGE:
        return FlagGet(FLAG_BADGE02_GET);
    case QUEST_DELIVER_STEVEN_LETTER:
        return FlagGet(FLAG_DELIVERED_STEVEN_LETTER);
    case QUEST_DELIVER_DEVON_GOODS:
        return FlagGet(FLAG_DELIVERED_DEVON_GOODS);
    case QUEST_DYNAMO_BADGE:
        return FlagGet(FLAG_BADGE03_GET);
    case QUEST_MT_CHIMNEY:
        return FlagGet(FLAG_DEFEATED_EVIL_TEAM_MT_CHIMNEY);
    case QUEST_HEAT_BADGE:
        return FlagGet(FLAG_BADGE04_GET);
    case QUEST_BALANCE_BADGE:
        return FlagGet(FLAG_BADGE05_GET);
    case QUEST_WEATHER_INSTITUTE:
        return VarGet(VAR_WEATHER_INSTITUTE_STATE) >= 1;
    case QUEST_DEVON_SCOPE:
        return FlagGet(FLAG_RECEIVED_DEVON_SCOPE);
    case QUEST_FEATHER_BADGE:
        return FlagGet(FLAG_BADGE06_GET);
    case QUEST_MT_PYRE:
        return VarGet(VAR_MT_PYRE_STATE) >= 1;
    case QUEST_MAGMA_HIDEOUT:
        return VarGet(VAR_SLATEPORT_HARBOR_STATE) >= 1;
    case QUEST_SLATEPORT_SUBMARINE:
        return VarGet(VAR_SLATEPORT_HARBOR_STATE) >= 2;
    case QUEST_AQUA_HIDEOUT:
        return FlagGet(FLAG_TEAM_AQUA_ESCAPED_IN_SUBMARINE);
    case QUEST_MIND_BADGE:
        return FlagGet(FLAG_BADGE07_GET);
    case QUEST_SPACE_CENTER:
        return VarGet(VAR_MOSSDEEP_SPACE_CENTER_STATE) >= 3;
    case QUEST_GET_DIVE:
        return FlagGet(FLAG_RECEIVED_HM_DIVE);
    case QUEST_SEAFLOOR_CAVERN:
        return FlagGet(FLAG_KYOGRE_ESCAPED_SEAFLOOR_CAVERN);
    case QUEST_CAVE_OF_ORIGIN:
        return FlagGet(FLAG_WALLACE_GOES_TO_SKY_PILLAR);
    case QUEST_AWAKEN_RAYQUAZA:
        return VarGet(VAR_SKY_PILLAR_STATE) >= 1;
    case QUEST_SOOTOPOLIS_CRISIS:
        return VarGet(VAR_SKY_PILLAR_STATE) >= 2;
    case QUEST_RAIN_BADGE:
        return FlagGet(FLAG_BADGE08_GET);
    case QUEST_VICTORY_ROAD:
        return FlagGet(FLAG_DEFEATED_WALLY_VICTORY_ROAD);
    case QUEST_POKEMON_LEAGUE:
        return FlagGet(FLAG_IS_CHAMPION);
    }

    return FALSE;
}

static u8 GetCurrentQuestId(void)
{
    u8 i;

    for (i = 0; i < QUEST_COUNT; i++)
    {
        if (!IsQuestComplete(i))
            return i;
    }

    return QUEST_COUNT;
}

static u8 CountCompletedQuests(void)
{
    u8 i;
    u8 count = 0;

    for (i = 0; i < QUEST_COUNT; i++)
    {
        if (IsQuestComplete(i))
            count++;
    }

    return count;
}

static void DrawStoryProgress(void)
{
    u8 progress = CountCompletedQuests();

    ConvertIntToDecimalStringN(gStringVar1, progress, STR_CONV_MODE_LEFT_ALIGN, 2);
    ConvertIntToDecimalStringN(gStringVar2, QUEST_COUNT, STR_CONV_MODE_LEFT_ALIGN, 2);
    StringExpandPlaceholders(gStringVar4, sText_StoryProgress);
    PrintText(gStringVar4, 134, 2, FONT_SMALL_NARROW);
}

static s8 GetPreviousMilestone(u8 currentQuest)
{
    s8 i;

    if (currentQuest == 0 || currentQuest > QUEST_COUNT)
        return -1;

    for (i = currentQuest - 1; i >= 0; i--)
    {
        if (IsQuestComplete(i))
            return i;
    }

    return -1;
}

static u8 GetCompletedQuestByListIndex(u8 listIndex)
{
    u8 i;
    u8 count = 0;

    for (i = 0; i < QUEST_COUNT; i++)
    {
        if (IsQuestComplete(i))
        {
            if (count == listIndex)
                return i;
            count++;
        }
    }

    return QUEST_COUNT;
}

static void PrintText(const u8 *text, u8 x, u8 y, u8 font)
{
    AddTextPrinterParameterized(sQuestWindowId, font, text, x, y, TEXT_SKIP_DRAW, NULL);
}

static void DrawTabs(void)
{
    if (sQuestTab == QUEST_TAB_CURRENT)
    {
        PrintText(sText_TabCurrentSelected, 8, 18, FONT_NARROW);
        PrintText(sText_TabCompleted, 94, 18, FONT_NARROW);
    }
    else
    {
        PrintText(sText_TabCurrent, 8, 18, FONT_NARROW);
        PrintText(sText_TabCompletedSelected, 82, 18, FONT_NARROW);
    }
}

static void DrawCurrentQuest(void)
{
    u8 currentQuest = GetCurrentQuestId();
    s8 previousQuest;

    if (currentQuest >= QUEST_COUNT)
    {
        PrintText(sText_StoryComplete, 8, 38, FONT_NORMAL);
        PrintText(sText_StoryCompleteDesc, 8, 62, FONT_NARROW);
        StringCopy(gStringVar4, sText_PreviousMilestone);
        StringAppend(gStringVar4, sMainQuests[QUEST_POKEMON_LEAGUE].title);
        PrintText(gStringVar4, 8, 132, FONT_SMALL_NARROW);
        return;
    }

    PrintText(sMainQuests[currentQuest].title, 8, 38, FONT_NORMAL);
    PrintText(sText_Objective, 8, 57, FONT_SMALL_NARROW);
    PrintText(sMainQuests[currentQuest].objective, 8, 69, FONT_NARROW);
    PrintText(sText_Location, 8, 105, FONT_SMALL_NARROW);
    PrintText(sMainQuests[currentQuest].location, 8, 115, FONT_NARROW);

    previousQuest = GetPreviousMilestone(currentQuest);
    StringCopy(gStringVar4, sText_PreviousMilestone);
    if (previousQuest >= 0)
        StringAppend(gStringVar4, sMainQuests[previousQuest].title);
    else
        StringAppend(gStringVar4, sText_NoPreviousMilestone);
    PrintText(gStringVar4, 8, 134, FONT_SMALL_NARROW);
}

static void DrawCompletedQuests(void)
{
    u8 completedCount = CountCompletedQuests();
    u8 row;

    if (completedCount == 0)
    {
        PrintText(sText_NoCompleted, 8, 48, FONT_NARROW);
        return;
    }

    for (row = 0; row < QUESTS_VISIBLE_COMPLETED; row++)
    {
        u8 listIndex = sCompletedScroll + row;
        u8 questId;

        if (listIndex >= completedCount)
            break;

        questId = GetCompletedQuestByListIndex(listIndex);
        if (questId < QUEST_COUNT)
        {
            StringCopy(gStringVar4, sText_Checkmark);
            StringAppend(gStringVar4, sMainQuests[questId].title);
            PrintText(gStringVar4, 8, 42 + row * 16, FONT_NARROW);
        }
    }

    ConvertIntToDecimalStringN(gStringVar1, sCompletedScroll + 1, STR_CONV_MODE_LEFT_ALIGN, 2);
    ConvertIntToDecimalStringN(gStringVar2,
                               min(sCompletedScroll + QUESTS_VISIBLE_COMPLETED, completedCount),
                               STR_CONV_MODE_LEFT_ALIGN, 2);
    ConvertIntToDecimalStringN(gStringVar3, completedCount, STR_CONV_MODE_LEFT_ALIGN, 2);
    StringExpandPlaceholders(gStringVar4, sText_Showing);
    PrintText(gStringVar4, 8, 133, FONT_SMALL_NARROW);
}

static void DrawQuestLog(void)
{
    FillWindowPixelBuffer(sQuestWindowId, PIXEL_FILL(1));
    PutWindowTilemap(sQuestWindowId);
    DrawStdWindowFrame(sQuestWindowId, FALSE);

    PrintText(sText_QuestLog, 8, 1, FONT_NORMAL);
    DrawStoryProgress();
    DrawTabs();

    if (sQuestTab == QUEST_TAB_CURRENT)
        DrawCurrentQuest();
    else
        DrawCompletedQuests();

    CopyWindowToVram(sQuestWindowId, COPYWIN_FULL);
}

void QuestLog_Open(void)
{
    u8 completedCount = CountCompletedQuests();

    sQuestTab = QUEST_TAB_CURRENT;
    sCompletedScroll = (completedCount > QUESTS_VISIBLE_COMPLETED)
                     ? completedCount - QUESTS_VISIBLE_COMPLETED
                     : 0;

    sQuestWindowId = AddWindow(&sQuestWindowTemplate);
    if (sQuestWindowId != WINDOW_NONE)
        DrawQuestLog();
}

void QuestLog_Close(void)
{
    if (sQuestWindowId != WINDOW_NONE)
    {
        ClearStdWindowAndFrameToTransparent(sQuestWindowId, TRUE);
        RemoveWindow(sQuestWindowId);
        sQuestWindowId = WINDOW_NONE;
    }
}

bool8 QuestLog_Update(void)
{
    u8 completedCount = CountCompletedQuests();

    if (sQuestWindowId == WINDOW_NONE)
        return TRUE;

    if (JOY_NEW(B_BUTTON))
    {
        PlaySE(SE_SELECT);
        return TRUE;
    }

    if (JOY_NEW(L_BUTTON | R_BUTTON))
    {
        PlaySE(SE_SELECT);
        sQuestTab ^= 1;
        DrawQuestLog();
        return FALSE;
    }

    if (sQuestTab == QUEST_TAB_COMPLETED)
    {
        if (JOY_NEW(DPAD_UP) && sCompletedScroll > 0)
        {
            PlaySE(SE_SELECT);
            sCompletedScroll--;
            DrawQuestLog();
        }
        else if (JOY_NEW(DPAD_DOWN)
              && sCompletedScroll + QUESTS_VISIBLE_COMPLETED < completedCount)
        {
            PlaySE(SE_SELECT);
            sCompletedScroll++;
            DrawQuestLog();
        }
    }

    return FALSE;
}

bool8 QuestLog_HasActiveQuest(void)
{
    return GetCurrentQuestId() < QUEST_COUNT;
}

const u8 *QuestLog_GetCurrentTitle(void)
{
    u8 currentQuest = GetCurrentQuestId();

    if (currentQuest >= QUEST_COUNT)
        return sText_StoryComplete;
    return sMainQuests[currentQuest].title;
}

u8 QuestLog_GetStoryProgress(void)
{
    return CountCompletedQuests();
}

u8 QuestLog_GetStoryTotal(void)
{
    return QUEST_COUNT;
}

u16 QuestLog_GetCurrentTargetMapSecId(void)
{
    u8 currentQuest = GetCurrentQuestId();

    if (currentQuest >= QUEST_COUNT)
        return MAPSEC_NONE;

    if (currentQuest == QUEST_MT_CHIMNEY && FlagGet(FLAG_MET_ARCHIE_METEOR_FALLS))
        return MAPSEC_MT_CHIMNEY;

    return sMainQuests[currentQuest].mapSecId;
}
