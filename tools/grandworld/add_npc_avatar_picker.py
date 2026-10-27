#!/usr/bin/env python3
"""Isolated World GBA NPC-skin picker, inspired by Quetzal's avatar-choice UX.

No sprite ROM data or unverified Quetzal slot/name mappings are imported.
Uses existing source-verified, animated human object graphics in PKMN-World.
Apply AFTER add_hero_profiles.py, to the pinned, disposable World checkout.
"""
from pathlib import Path
import argparse
import json
import re
import sys

# Approved human NPC graphical identities: excludes water poses, bikes, dolls,
# inanimate props, monster objects and Quetzal's unverified slot/name mapping.
HUMAN_NPCS = """
NINJA_BOY TWIN BOY_1 GIRL_1 BOY_2 GIRL_2 LITTLE_BOY LITTLE_GIRL
BOY_3 GIRL_3 RICH_BOY WOMAN_1 FAT_MAN POKEFAN_F MAN_1 WOMAN_2
EXPERT_M EXPERT_F MAN_2 WOMAN_3 POKEFAN_M WOMAN_4 COOK
LINK_RECEPTIONIST OLD_MAN OLD_WOMAN CAMPER PICNICKER MAN_3 WOMAN_5
YOUNGSTER BUG_CATCHER PSYCHIC_M SCHOOL_KID_M MANIAC HEX_MANIAC
SWIMMER_M SWIMMER_F BLACK_BELT BEAUTY SCIENTIST_1 LASS GENTLEMAN
SAILOR FISHERMAN RUNNING_TRIATHLETE_M RUNNING_TRIATHLETE_F TUBER_F
TUBER_M HIKER PROF_BIRCH MAN_4 MAN_5 REPORTER_M REPORTER_F BARD
ANABEL TUCKER GRETA SPENSER NOLAND LUCY MART_EMPLOYEE
ROOFTOP_SALE_WOMAN TEALA ARTIST CAMERAMAN SCIENTIST_2 DEVON_EMPLOYEE
AQUA_MEMBER_M AQUA_MEMBER_F MAGMA_MEMBER_M MAGMA_MEMBER_F
SIDNEY PHOEBE GLACIA DRAKE ROXANNE BRAWLY WATTSON FLANNERY NORMAN
WINONA LIZA TATE WALLACE STEVEN WALLY LITTLE_BOY_3
HOT_SPRINGS_OLD_WOMAN GAMEBOY_KID CONTEST_JUDGE ARCHIE MAXIE MOM
JUAN SCOTT MYSTERY_GIFT_MAN UNION_ROOM_NURSE RED LEAF BRANDON
RED_NORMAL GREEN_NORMAL LITTLE_BOY_FRLG LITTLE_GIRL_FRLG
YOUNGSTER_FRLG BOY BUG_CATCHER_FRLG LASS_FRLG WOMAN_1_FRLG
CRUSH_GIRL MAN ROCKER FAT_MAN_FRLG WOMAN_2_FRLG BEAUTY_FRLG
BALDING_MAN WOMAN_3_FRLG OLD_MAN_1 OLD_MAN_2 OLD_WOMAN_FRLG
TUBER_F_FRLG TUBER_M_LAND CAMPER_FRLG PICNICKER_FRLG COOLTRAINER_M
COOLTRAINER_F SWIMMER_M_LAND SWIMMER_F_LAND WORKER_M WORKER_F
ROCKET_M ROCKET_F GBA_KID POKE_MANIAC_FRLG BLACK_BELT_FRLG SCIENTIST
HIKER_FRLG FISHER CHANNELER CHEF POLICEMAN GENTLEMAN_FRLG
SAILOR_FRLG CAPTAIN CABLE_CLUB_RECEPTIONIST UNION_ROOM_RECEPTIONIST
CLERK MG_DELIVERYMAN TRAINER_TOWER_DUDE PROF_OAK BLUE BILL LANCE
AGATHA DAISY LORELEI MR_FUJI BRUNO BROCK MISTY LT_SURGE ERIKA
KOGA SABRINA BLAINE GIOVANNI MOM_FRLG CELIO TEACHY_TV_HOST
EUSINE FALKNER BUGSY WHITNEY MORTY CHUCK JASMINE PRYCE CLAIR WILL
KAREN JANINE PROF_ELM KURT KIMONO_GIRL ARCHER ARIANA PETREL PROTON
FIREBREATHER SAGE
""".split()
ANIMS = {"sAnimTable_Standard", "sAnimTable_BrendanMayNormal",
         "sAnimTable_Red", "sAnimTable_RedNormal"}
PAGE_SIZE = 6
VAR_ID = "0x40E5"


def replace_once(content, old, new, label):
    count = content.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected exactly one anchor, saw {count}")
    return content.replace(old, new, 1)


def roster(world):
    pointer_file = (world / "src/data/object_events/object_event_graphics_info_pointers.h").read_text()
    info_file = (world / "src/data/object_events/object_event_graphics_info.h").read_text()
    enum_file = (world / "include/constants/event_objects.h").read_text()
    pointer = dict(re.findall(
        r"\[OBJ_EVENT_GFX_([A-Z0-9_]+)\]\s*=\s*&gObjectEventGraphicsInfo_(\w+)",
        pointer_file))
    enum_entries = set(re.findall(r"(?m)^\s*OBJ_EVENT_GFX_([A-Z0-9_]+)\s*[,=]", enum_file))
    if len(pointer) < 390 or len(enum_entries) < 390:
        raise ValueError("World object graphics tables unexpectedly small")
    if len(HUMAN_NPCS) != len(set(HUMAN_NPCS)):
        raise ValueError("duplicate human character name")
    approved = []
    for name in HUMAN_NPCS:
        if name not in enum_entries or name not in pointer:
            raise ValueError(f"missing original NPC graphic ID and pointer: {name}")
        info = pointer[name]
        matches = re.findall(
            r"const struct ObjectEventGraphicsInfo gObjectEventGraphicsInfo_"
            + re.escape(info) + r"\s*=\s*\{(.*?)\n\};", info_file, re.S)
        if len(matches) != 1:
            raise ValueError(f"cannot verify unique object graphics: {name} -> {info}")
        body = matches[0]
        for field, expected in (
            ("inanimate", "FALSE"), ("tracks", "TRACKS_FOOT")
        ):
            if re.search(r"\." + field + r"\s*=\s*" + expected + r"\s*,", body) is None:
                raise ValueError(f"{name} lacks {field}={expected}")
        for field in ("width", "height"):
            a = re.search(r"\." + field + r"\s*=\s*(\d+)\s*,", body)
            if a is None or int(a.group(1)) not in (16, 32):
                raise ValueError(f"{name} has unsupported {field}")
        anim = re.search(r"\.anims\s*=\s*(\w+)\s*,", body)
        if anim is None or anim.group(1) not in ANIMS:
            raise ValueError(f"{name} lacks validated walking animation: {anim}")
        if re.search(r"\.images\s*=\s*sPicTable_\w+", body) is None:
            raise ValueError(f"{name} has no original sprite frames")
        approved.append(name)
    return approved


def header_text(names):
    lines = [
        "#ifndef GUARD_GW_NPC_AVATAR_CATALOG_H",
        "#define GUARD_GW_NPC_AVATAR_CATALOG_H",
        "/* Generated from SOURCE-VALIDATED World NPC graphics. No Quetzal ROM art.",
        " * Index zero = classic hero, others use a human World object graphic.",
        " * These labels identify World gfx, not Quetzal avatar slots. */",
        "struct GWAvatarChoice { const u8 *name; u16 graphicsId; };",
        "#define GW_AVATAR_CHOICES_COUNT " + str(len(names) + 1),
        "#define GW_AVATAR_PAGE_SIZE 6",
        "extern const struct GWAvatarChoice sGWAvatarChoices[GW_AVATAR_CHOICES_COUNT];",
        "/* Generate assets ONCE in field_player_avatar.c, never each include. */",
        "#ifdef GW_NPC_AVATAR_DEFINE",
        'static const u8 sGWAvatarClassicName[] = _("CLASSICO");',
    ]
    for i, name in enumerate(names, 1):
        # GBA menu width: 14 tiles. Keep visible label at most 12 characters.
        label = name.replace("_", " ")[:10]
        lines.append(f'static const u8 sGWAvatarName{i:03}[] = _("{label}");')
    lines.append("const struct GWAvatarChoice sGWAvatarChoices[GW_AVATAR_CHOICES_COUNT] = {")
    lines.append("    {sGWAvatarClassicName, 0},")
    for i, name in enumerate(names, 1):
        lines.append(f"    {{sGWAvatarName{i:03}, OBJ_EVENT_GFX_{name}}},")
    lines += ["};", "#endif /* GW_NPC_AVATAR_DEFINE */", "#endif /* include guard */"]
    return "\n".join(lines) + "\n"


INTRO_FUNCTIONS = r'''
// GBA M9: 6 old hero identities remain unchanged; NPC appearance is optional.
// L/R changes a 6-row page. B returns to original hero appearance.
static const u8 sGWAvatarHelp[] = _("NPC: L/R PAG.");
static const struct WindowTemplate sGWAvatarWindow = {
    .bg = 0, .tilemapLeft = 16, .tilemapTop = 1,
    .width = 12, .height = 10, .paletteNum = 15, .baseBlock = 360
};

static void GW_DrawAvatarChoices(u8 taskId, bool8 firstDraw)
{
    s16 *data = gTasks[taskId].data; // tPromptWindowId expands to data[index]
    u8 i, count;
    u16 start = (u16)gTasks[taskId].data[13] * GW_AVATAR_PAGE_SIZE;
    u8 window = gTasks[taskId].tMenuWindowId;
    u8 step = GetFontAttribute(FONT_SMALL, FONTATTR_MAX_LETTER_HEIGHT) + 2;
    // Reuse one buffer across all 33 pages: AddWindow/Free each L/R
    // fragmented Oak's EWRAM and crashed at window.c:185 after several pages.
    // 12 * 10 tiles = 3840 bytes; baseBlock 360 + 120 = 480 (< 512).
    if (firstDraw)
    {
        window = AddWindow(&sGWAvatarWindow);
        if (window == WINDOW_NONE)
        {
            // If memory is exhausted, leave the save on the classic skin,
            // skip this OPTIONAL menu, and NEVER dereference WINDOW_NONE.
            VarSet(VAR_GW_NPC_AVATAR, 0);
            gTasks[taskId].tMenuWindowId = WINDOW_NONE;
            ClearDialogWindowAndFrame(tPromptWindowId, TRUE);
            RemoveWindow(tPromptWindowId);
            gTasks[taskId].func = Task_OakSpeech_AskHardMode;
            return;
        }
        gTasks[taskId].tMenuWindowId = window;
        PutWindowTilemap(window);
        DrawStdFrameWithCustomTileAndPalette(window, TRUE, STD_WINDOW_BASE_TILE_NUM, 14);
    }
    FillWindowPixelBuffer(window, PIXEL_FILL(1));
    count = GW_AVATAR_CHOICES_COUNT - start;
    if (count > GW_AVATAR_PAGE_SIZE)
        count = GW_AVATAR_PAGE_SIZE;
    for (i = 0; i < count; i++)
        AddTextPrinterParameterized3(window, FONT_SMALL, 8, i * step + 1,
                                     sOakSpeechResources->textColor, 0,
                                     sGWAvatarChoices[start + i].name);
    InitMenuNormal(window, FONT_SMALL, 0, 1, step, count, 0);
    // BG tilemap stays unchanged across pages. Avoid a redundant 2KiB
    // tilemap DMA on every L/R; only the 4bpp window pixels need refreshing.
    CopyWindowToVram(window, firstDraw ? COPYWIN_FULL : COPYWIN_GFX);
}

static void GW_CloseAvatarChoices(u8 taskId)
{
    s16 *data = gTasks[taskId].data;
    if (gTasks[taskId].tMenuWindowId != WINDOW_NONE)
    {
        ClearStdWindowAndFrameToTransparent(gTasks[taskId].tMenuWindowId, TRUE);
        RemoveWindow(gTasks[taskId].tMenuWindowId);
    }
    gTasks[taskId].tMenuWindowId = WIN_INTRO_TEXTBOX;
    ClearDialogWindowAndFrame(tPromptWindowId, TRUE);
    RemoveWindow(tPromptWindowId);
}

static void GW_AvatarMenuStart(u8 taskId)
{
    s16 *data = gTasks[taskId].data;
    gTasks[taskId].data[13] = 0;
    VarSet(VAR_GW_NPC_AVATAR, 0); // 0 is compatible with pre-M9 saves
    gTasks[taskId].tMenuWindowId = WINDOW_NONE;
    // Use the EXISTING outfit prompt window (small, on the left).
    // Printing into the 28x15 Oak textbox covered the top-right NPC list.
    // Also avoids another large text-window allocation.
    tPromptWindowId = AddWindow(&sOutfitPromptWindowTemplate);
    if (tPromptWindowId == WINDOW_NONE)
    {
        gTasks[taskId].func = Task_OakSpeech_AskHardMode;
        return;
    }
    DrawDialogueFrame(tPromptWindowId, FALSE);
    AddTextPrinterParameterized2(tPromptWindowId, FONT_SMALL, sGWAvatarHelp,
        sOakSpeechResources->textSpeed, NULL, TEXT_COLOR_DARK_GRAY,
        TEXT_COLOR_WHITE, TEXT_COLOR_LIGHT_GRAY);
    CopyWindowToVram(tPromptWindowId, COPYWIN_FULL);
    gTasks[taskId].func = GW_AvatarMenuShow;
}

static void GW_AvatarMenuShow(u8 taskId)
{
    s16 *data = gTasks[taskId].data;
    if (!IsTextPrinterActiveOnWindow(tPromptWindowId))
    {
        GW_DrawAvatarChoices(taskId, TRUE);
        if (gTasks[taskId].tMenuWindowId != WINDOW_NONE)
            gTasks[taskId].func = GW_AvatarMenuInput;
    }
}

static void GW_AvatarMenuInput(u8 taskId)
{
    s8 input;
    // 12*10 tiles + baseBlock 360 = 480, safely within BG0's 512-tile charblock.
    // Apply page navigation BEFORE Menu_ProcessInputNoWrap to avoid accidental commits.
    if (gMain.newKeys & (L_BUTTON | R_BUTTON))
    {
        s16 page = gTasks[taskId].data[13];
        s16 maxPage = (GW_AVATAR_CHOICES_COUNT - 1) / GW_AVATAR_PAGE_SIZE;
        if (gMain.newKeys & R_BUTTON)
            page = page == maxPage ? 0 : page + 1;
        else
            page = page == 0 ? maxPage : page - 1;
        gTasks[taskId].data[13] = page;
        GW_DrawAvatarChoices(taskId, FALSE); // no heap churn when flipping pages
        PlaySE(SE_SELECT);
        return;
    }

    input = Menu_ProcessInputNoWrap();
    if (input == MENU_NOTHING_CHOSEN)
        return;
    if (input == MENU_B_PRESSED)
        VarSet(VAR_GW_NPC_AVATAR, 0);
    else
    {
        u16 index = (u16)gTasks[taskId].data[13] * GW_AVATAR_PAGE_SIZE + input;
        if (index >= GW_AVATAR_CHOICES_COUNT)
            return; // fail closed, never persist a graphics ID outside the catalog
        VarSet(VAR_GW_NPC_AVATAR, index);
    }
    PlaySE(SE_SELECT);
    GW_CloseAvatarChoices(taskId);
    gTasks[taskId].func = Task_OakSpeech_AskHardMode;
}

'''


def patch(world: Path, apply=False):
    required = ["src/oak_speech.c", "src/new_game.c", "src/field_player_avatar.c",
                "src/palette_swap.c",
                "include/constants/vars.h",
                "src/data/object_events/object_event_graphics_info_pointers.h",
                "src/data/object_events/object_event_graphics_info.h",
                "include/constants/event_objects.h", "Makefile"]
    if any(not (world / p).is_file() for p in required):
        raise ValueError("not a complete pinned World checkout")
    names = roster(world)
    oakp, newp, fieldp, palettep, varp = [world / p for p in (
        "src/oak_speech.c", "src/new_game.c", "src/field_player_avatar.c",
        "src/palette_swap.c", "include/constants/vars.h")]
    catp = world / "include/grandworld_avatar_catalog.h"
    if catp.exists():
        raise ValueError("avatar catalog already exists, refusing double-application")
    oak, new, field, palette, var = [p.read_text(encoding="utf-8") for p in (oakp, newp, fieldp, palettep, varp)]
    var = replace_once(var,
       "#define VAR_UNUSED_0x40E5                                0x40E5 // Unused Var",
       "#define VAR_UNUSED_0x40E5                                0x40E5 // Unused Var\n"
       "#define VAR_GW_NPC_AVATAR                               VAR_UNUSED_0x40E5 // M9 skin; 0=classic",
       "reserved non-save-expanding skin var")
    oak = replace_once(oak,
       '#include "menu.h"', '#include "menu.h"\n#include "main.h"',
       "GBA button state for L/R paginated NPC menu")
    oak = replace_once(oak,
       '#include "constants/vars.h"',
       '#include "constants/vars.h"\n#include "constants/event_objects.h"\n'
       '#include "grandworld_avatar_catalog.h"', "oak avatar catalog includes")
    oak = replace_once(oak,
       "static void Task_OakSpeech_AskHardMode(u8);",
       "static void GW_AvatarMenuStart(u8);\nstatic void GW_AvatarMenuShow(u8);\n"
       "static void GW_AvatarMenuInput(u8);\n"
       "static void Task_OakSpeech_AskHardMode(u8);", "menu prototypes")
    oak = replace_once(oak,
       "    gTasks[taskId].func = Task_OakSpeech_AskHardMode;\n}\n\n// QoL #2:",
       "    gTasks[taskId].func = GW_AvatarMenuStart;\n}\n\n// QoL #2:", "hero selection -> avatar selection")
    oak = replace_once(oak,
       "static void Task_OakSpeech_AskHardMode(u8 taskId)\n{",
       INTRO_FUNCTIONS + "static void Task_OakSpeech_AskHardMode(u8 taskId)\n{",
       "real NPC picker code")
    new = replace_once(new,
       "    u16 playerHero = VarGet(VAR_PLAYER_CHARACTER);",
       "    u16 playerHero = VarGet(VAR_PLAYER_CHARACTER);\n"
       "    u16 playerNpcAvatar = VarGet(VAR_GW_NPC_AVATAR);",
       "preserve NPC id across new game SaveBlock reset")
    new = replace_once(new,
       "    VarSet(VAR_PLAYER_CHARACTER, playerHero); // persistent six-protagonist identity",
       "    VarSet(VAR_PLAYER_CHARACTER, playerHero); // persistent six-protagonist identity\n"
       "    VarSet(VAR_GW_NPC_AVATAR, playerNpcAvatar); // M9 skin independent of hero identity",
       "restore NPC ID after new game SaveBlock reset")
    field = replace_once(field,
       '#include "constants/event_objects.h"',
       '#include "constants/event_objects.h"\n#include "constants/vars.h"\n'
       '#define GW_NPC_AVATAR_DEFINE\n#include "grandworld_avatar_catalog.h"',
       "player catalog includes")
    field = replace_once(field,
       "    u16 hero = VarGet(VAR_PLAYER_CHARACTER);\n    if (hero == 2 && gender == MALE)",
       "    u16 skin = VarGet(VAR_GW_NPC_AVATAR);\n"
       "    if (state == PLAYER_AVATAR_STATE_NORMAL && skin != 0\n"
       "        && skin < GW_AVATAR_CHOICES_COUNT)\n"
       "        return sGWAvatarChoices[skin].graphicsId;\n"
       "    u16 hero = VarGet(VAR_PLAYER_CHARACTER);\n    if (hero == 2 && gender == MALE)",
       "on-foot NPC override before original Red/Leaf special-state switch")
    field = replace_once(field,
       "enum Gender GetPlayerAvatarGenderByGraphicsId(u16 gfxId)\n{\n    switch (gfxId)",
       "enum Gender GetPlayerAvatarGenderByGraphicsId(u16 gfxId)\n{\n"
       "    u16 skin = VarGet(VAR_GW_NPC_AVATAR);\n"
       "    if (skin != 0 && skin < GW_AVATAR_CHOICES_COUNT\n"
       "        && gfxId == sGWAvatarChoices[skin].graphicsId)\n"
       "        return gSaveBlock2Ptr->playerGender; // visual skin never alters selected identity\n"
       "    switch (gfxId)", "skin gender must not rewrite legacy hero gender")
    # The existing M8 Kanto adapter already restores all player graphics states
    # through this central getter. Do not discard its validated FRLG bike/Surf art.
    if field.count("return GetPlayerAvatarGraphicsIdByStateIdAndGender(i, gPlayerAvatar.gender);") != 1:
        raise ValueError("M8 Kanto state routing absent: apply add_kanto_avatar.py first")
    palette = replace_once(palette,
       "    u16 hero = VarGet(VAR_PLAYER_CHARACTER);\n"
       "    if (hero == 2 || hero == 3)",
       "    if (VarGet(VAR_GW_NPC_AVATAR) != 0)\n"
       "        return PLAYER_OUTFIT_RED; // preserve NPC native palette instead of hero recolor\n"
       "    u16 hero = VarGet(VAR_PLAYER_CHARACTER);\n"
       "    if (hero == 2 || hero == 3)",
       "skip recoloring native NPC sprites")
    output = {oakp: oak, newp: new, fieldp: field, palettep: palette,
              varp: var, catp: header_text(names)}
    summary = {"npc_characters_from_original_world": len(names),
               "choices_including_classic": len(names) + 1,
               "menu_rows_per_page": PAGE_SIZE, "pages": (len(names) + PAGE_SIZE) // PAGE_SIZE,
               "source_validation": "original World pointers, foot tracking, animate and 16/32 graphics",
               "quetzal_113_slot_name_links_proven": 0,
               "quetzal_sprite_bytes_imported": False,
               "save_block_layout_modified": False,
               "legacy_6_hero_selection_preserved": True,
               "runtime_emulator_verified": False,
               "roster": names}
    if apply:
        for path, value in output.items():
            if path == catp or path.read_text(encoding="utf-8") != value:
                path.write_text(value, encoding="utf-8")
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("world", type=Path)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--report", type=Path)
    args = p.parse_args()
    try:
        result = patch(args.world, args.apply)
    except (OSError, ValueError) as err:
        sys.exit("FAIL CLOSED: " + str(err))
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "roster"}, indent=2))
