#!/usr/bin/env python3
"""M1: use pre-existing FireRed Red/Leaf *normal walking* sprites when selected.
Other movement poses safely retain existing Brendan/May fallbacks, avoiding
unsupported Acro/underwater animations for the FRLG sprite formats.
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
    new='''    /* Grand World M1: distinct Red/Leaf sprites on foot, independent of
     * geographic region. Moving to another region retains chosen identity.
     * FRLG bike, surf and underwater require animation-specific QA before
     * enabling; fallback to the known-safe Emerald atlas in those states. */
    if (state == PLAYER_AVATAR_STATE_NORMAL)
    {
        u16 hero = VarGet(VAR_PLAYER_CHARACTER);
        if (hero == 2 && gender == MALE)
            return OBJ_EVENT_GFX_RED_NORMAL;
        if (hero == 3 && gender == FEMALE)
            return OBJ_EVENT_GFX_GREEN_NORMAL;
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
