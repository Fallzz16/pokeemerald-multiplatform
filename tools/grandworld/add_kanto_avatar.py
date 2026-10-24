#!/usr/bin/env python3
"""M1: use pre-existing FireRed Red/Leaf *normal walking* sprites when selected.
Supports the six original FRLG standard-state pose families. Complex Acro,
underwater and watering animations safely retain Emerald stand-ins.
No new save fields or art files. All replacements are fail-closed.
"""
from pathlib import Path
import sys

def swap(text,old,new,path):
    if text.count(old)!=1:
        raise ValueError(f"source drift in {path}: {old[:65]!r} found {text.count(old)} times")
    return text.replace(old,new,1)

def patch(world):
    avatar_path=world/"src/field_player_avatar.c"
    palette_path=world/"src/palette_swap.c"
    avatar=avatar_path.read_text()
    palette=palette_path.read_text()
    old='''    // Region merge: the player is Brendan/May in every region now (Kanto no longer uses
    // the FRLG Red/Leaf overworld sprites; Red's sprites are reused for the Johto rival).
    return sPlayerAvatarGfxIds[state][gender];'''
    new='''    /* Grand World M8: use source-native FRLG artwork for validated poses,
     * independent of current region. Red and Leaf retain their identity on
     * standard bike, surf, field move, fishing, and Vs Seeker states.
     * Acro tricks, underwater and watering have no validated FRLG equivalent:
     * deliberately keep the safe Emerald stand-ins there. */
    u16 hero = VarGet(VAR_PLAYER_CHARACTER);
    if (hero == 2 && gender == MALE)
    {
        switch (state)
        {
        case PLAYER_AVATAR_STATE_NORMAL: return OBJ_EVENT_GFX_RED_NORMAL;
        case PLAYER_AVATAR_STATE_MACH_BIKE: return OBJ_EVENT_GFX_RED_BIKE;
        case PLAYER_AVATAR_STATE_SURFING: return OBJ_EVENT_GFX_RED_SURF;
        case PLAYER_AVATAR_STATE_FIELD_MOVE: return OBJ_EVENT_GFX_RED_FIELD_MOVE;
        case PLAYER_AVATAR_STATE_FISHING: return OBJ_EVENT_GFX_RED_FISH;
        case PLAYER_AVATAR_STATE_VSSEEKER: return OBJ_EVENT_GFX_RED_VS_SEEKER;
        }
    }
    else if (hero == 3 && gender == FEMALE)
    {
        switch (state)
        {
        case PLAYER_AVATAR_STATE_NORMAL: return OBJ_EVENT_GFX_GREEN_NORMAL;
        case PLAYER_AVATAR_STATE_MACH_BIKE: return OBJ_EVENT_GFX_GREEN_BIKE;
        case PLAYER_AVATAR_STATE_SURFING: return OBJ_EVENT_GFX_GREEN_SURF;
        case PLAYER_AVATAR_STATE_FIELD_MOVE: return OBJ_EVENT_GFX_GREEN_FIELD_MOVE;
        case PLAYER_AVATAR_STATE_FISHING: return OBJ_EVENT_GFX_GREEN_FISH;
        case PLAYER_AVATAR_STATE_VSSEEKER: return OBJ_EVENT_GFX_GREEN_VS_SEEKER;
        }
    }
    return sPlayerAvatarGfxIds[state][gender];'''
    avatar=swap(avatar,old,new,avatar_path)
    # On map reload return the actual portrait determined by the chosen hero,
    # otherwise this function would restore Brendan/May even if spawn was Red/Leaf.
    avatar=swap(avatar,'            return table[gPlayerAvatar.gender][i].graphicsId;',
               '            return GetPlayerAvatarGraphicsIdByStateIdAndGender(i, gPlayerAvatar.gender);',avatar_path)
    # Guard the FRLG sprite palettes: their indices differ from Brendan/May's
    # palette-swap authored indices. Never repaint Red/Leaf with Hoenn palettes.
    palette=swap(palette,'    u16 val = VarGet(VAR_PLAYER_PALETTE);',
          '''    u16 hero = VarGet(VAR_PLAYER_CHARACTER);
    if (hero == 2 || hero == 3)
        return PLAYER_OUTFIT_RED;
    u16 val = VarGet(VAR_PLAYER_PALETTE);''',palette_path)
    return avatar,palette

if __name__=="__main__":
    if len(sys.argv)!=2:sys.exit("usage: add_kanto_avatar.py /isolated/world")
    root=Path(sys.argv[1])
    try:
        a,b=patch(root)
        (root/"src/field_player_avatar.c").write_text(a)
        (root/"src/palette_swap.c").write_text(b)
        print("FRLG Red/Leaf normal-state sprites selected from persistent hero identity.")
    except (OSError,ValueError) as e:
        sys.exit("FAIL-CLOSED: "+str(e))
