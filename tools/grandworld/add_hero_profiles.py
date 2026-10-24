#!/usr/bin/env python3
"""M1/M8: six persistent region-themed hero profiles from the existing sprite palette set.
Brendan, May, Red, Leaf, Ethan, Lyra. No unlicensed new raster imports.
The actual overworld anatomy stays Brendan/May; these are named palette-based
visual proxies until unique per-character animation sheets are validated.
The gender picker precedes a three-entry hero picker, producing six choices.
"""
from pathlib import Path
import sys

def once(s,old,new,path):
    n=s.count(old)
    if n!=1:
        raise ValueError(f"{path}: expected exactly one anchor, saw {n}: {old[:65]}")
    return s.replace(old,new,1)

def patch(root: Path):
    oak=root/"src/oak_speech.c"
    new=root/"src/new_game.c"
    src=oak.read_text()
    intro=new.read_text()
    old_labels='''static const u8 sText_Outfit_Red[] = _("RED");
static const u8 sText_Outfit_Blue[] = _("BLUE");
static const u8 sText_Outfit_Green[] = _("GREEN");
static const u8 sText_Outfit_Purple[] = _("PURPLE");
static const u8 sText_Outfit_Black[] = _("BLACK");
static const u8 sText_Outfit_Pink[] = _("PINK");

static const u8 *const sOutfitOptions[NUM_PLAYER_OUTFITS] = {
    [PLAYER_OUTFIT_RED]    = sText_Outfit_Red,
    [PLAYER_OUTFIT_BLUE]   = sText_Outfit_Blue,
    [PLAYER_OUTFIT_GREEN]  = sText_Outfit_Green,
    [PLAYER_OUTFIT_PURPLE] = sText_Outfit_Purple,
    [PLAYER_OUTFIT_BLACK]  = sText_Outfit_Black,
    [PLAYER_OUTFIT_PINK]   = sText_Outfit_Pink,
};'''
    replacement='''/* Six role identities, three per selected gender. The six existing GBA
 * palette combinations are stand-in costumes, NOT faithful Red/Leaf/HGSS art. */
static const u8 sHeroBrendan[] = _("BRENDAN");
static const u8 sHeroMay[] = _("MAY");
static const u8 sHeroRed[] = _("RED");
static const u8 sHeroLeaf[] = _("LEAF");
static const u8 sHeroEthan[] = _("ETHAN");
static const u8 sHeroLyra[] = _("LYRA");
static const u8 *const sHeroMale[3] = {sHeroBrendan, sHeroRed, sHeroEthan};
static const u8 *const sHeroFemale[3] = {sHeroMay, sHeroLeaf, sHeroLyra};

static u8 GrandWorldHeroSlot(u8 regionTheme)
{
    return (u8)(regionTheme * 2 + (gSaveBlock2Ptr->playerGender == FEMALE));
}'''
    src=once(src,old_labels,replacement,oak)
    src=once(src,'_("And your outfit?\\nIt\\'s for keeps!")',
                 '_("Choose a hero!\\nPick your style.")',oak)
    oldloop='''        for (i = 0; i < NUM_PLAYER_OUTFITS; i++)
            AddTextPrinterParameterized3(gTasks[taskId].tMenuWindowId, FONT_NORMAL, 8, i * step + 1, sOakSpeechResources->textColor, 0, sOutfitOptions[i]);
        InitMenuNormal(gTasks[taskId].tMenuWindowId, FONT_NORMAL, 0, 1, step, NUM_PLAYER_OUTFITS, 0);'''
    newloop='''        for (i = 0; i < 3; i++)
            AddTextPrinterParameterized3(gTasks[taskId].tMenuWindowId, FONT_NORMAL, 8, i * step + 1, sOakSpeechResources->textColor, 0,
                 gSaveBlock2Ptr->playerGender == FEMALE ? sHeroFemale[i] : sHeroMale[i]);
        InitMenuNormal(gTasks[taskId].tMenuWindowId, FONT_NORMAL, 0, 1, step, 3, 0);'''
    src=once(src,oldloop,newloop,oak)
    src=once(src,'VarSet(VAR_PLAYER_PALETTE, cursorPos);',
             'VarSet(VAR_PLAYER_PALETTE, GrandWorldHeroSlot(cursorPos));',oak)
    src=once(src,'    VarSet(VAR_PLAYER_PALETTE, input);\n    ReloadOutfitPreviewBase();',
             '    VarSet(VAR_PLAYER_PALETTE, GrandWorldHeroSlot(input));\n    VarSet(VAR_PLAYER_CHARACTER, GrandWorldHeroSlot(input));\n    ReloadOutfitPreviewBase();',oak)
    intro=once(intro,'    u16 playerOutfit = VarGet(VAR_PLAYER_PALETTE);',
               '    u16 playerOutfit = VarGet(VAR_PLAYER_PALETTE);\n    u16 playerHero = VarGet(VAR_PLAYER_CHARACTER);',new)
    intro=once(intro,'    VarSet(VAR_PLAYER_PALETTE, playerOutfit); // restore the intro outfit pick wiped by ClearSav1',
               '    VarSet(VAR_PLAYER_PALETTE, playerOutfit); // persistent hero costume\n    VarSet(VAR_PLAYER_CHARACTER, playerHero); // persistent six-protagonist identity',new)
    return {oak:src,new:intro}

if __name__=="__main__":
    if len(sys.argv)!=2:sys.exit("usage: add_hero_profiles.py /isolated/pokemon-world")
    root=Path(sys.argv[1])
    try:
        result=patch(root)
        (root/"src/oak_speech.c").write_text(result["oak"])
        (root/"src/new_game.c").write_text(result["new"])
        print("M1: six profiles in intro, world-global identity persisted without save layout edits.")
    except (ValueError,OSError) as e:
        sys.exit("FAIL-CLOSED: "+str(e))
