"""Exact inverse of the reviewed v0.8 SDL2 managed-profile integration.
This helper is intentionally strict: legacy audit MUST still be able to hash
the previously protected v0.3.4/v0.7 SDL2 source without changing any other
byte. Activated ONLY under EMERALD_V080_QA=1, not as a blanket exemption.
"""
def strip_v080_profile_patch(native: str) -> str:
    def once(old: str, new: str) -> None:
        nonlocal native
        if native.count(old) != 1:
            raise AssertionError("v0.8 profile integration drift: " + old[:60])
        native = native.replace(old, new, 1)

    once('/* Optional v0.8 managed profiles; legacy save remains the default. */\n'
         '#include "../profile/save_profiles.h"\n', '')
    once('static FILE *sSaveFile = NULL;\n'
         'static char sActiveSavePath[SP_PATH_CAP] = "pokeemerald.sav";\n'
         'static SpProfileLock sActiveProfileLock;\n'
         'static bool sProfileLocked = false;',
         'static FILE *sSaveFile = NULL;')
    once('int main(int argc, char **argv)\n'
         '{\n    const char *profileRoot = NULL;\n'
         '    const char *profileId = NULL;\n',
         'int main(int argc, char **argv)\n{\n')
    once('        if (strncmp(argv[i], "--profile-root=", 15) == 0)\n'
         '            profileRoot = argv[i] + 15;\n'
         '        else if (strncmp(argv[i], "--profile-id=", 13) == 0)\n'
         '            profileId = argv[i] + 13;\n'
         '        else if (strncmp(argv[i], "--lan-host=", 11) == 0)',
         '        if (strncmp(argv[i], "--lan-host=", 11) == 0)')

    start = '    /* Managed profiles opt in explicitly; missing/busy profiles must fail'
    end = '    if(SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO) < 0)'
    if native.count(start) != 1 or native.count(end) != 1:
        raise AssertionError("missing exact opt-in profile block")
    a = native.index(start)
    b = native.index(end, a)
    old = native[a:b]
    expected_tail = '#endif\n\n'
    if not old.endswith(expected_tail) or 'sp_lock(profileRoot, profileId' not in old or \
            'ReadSaveFile(sActiveSavePath)' not in old or 'sp_unlock(&sActiveProfileLock)' not in old:
        raise AssertionError("unexpected managed profile block: review before updating audit")
    native = native[:a] + '#ifndef __ANDROID__\n    ReadSaveFile("pokeemerald.sav");\n#endif\n\n' + native[b:]

    once('        if (!sProfileLocked)\n'
         '            SDL_snprintf(sActiveSavePath, sizeof(sActiveSavePath),\n'
         '                         "%spokeemerald.sav", prefPath);\n'
         '        SDL_free(prefPath);\n'
         '        ReadSaveFile(sActiveSavePath);\n'
         '        if (sSaveFile == NULL)\n'
         '        {\n'
         '            if (sProfileLocked)\n'
         '                sp_unlock(&sActiveProfileLock);\n'
         '            SDL_Quit();\n'
         '            return 2;\n'
         '        }',
         '        SDL_snprintf(sAndroidSavePath, sizeof(sAndroidSavePath), "%spokeemerald.sav", prefPath);\n'
         '        SDL_free(prefPath);\n'
         '        ReadSaveFile(sAndroidSavePath);')
    once('    CloseSaveFile();\n'
         '    /* Hold this OS lock until every flash read/write thread has stopped. */\n'
         '    if (sProfileLocked)\n'
         '        sp_unlock(&sActiveProfileLock);\n',
         '    CloseSaveFile();\n')
    once('        if (!sProfileLocked)\n'
         '            sSaveFile = fopen(path, "w+b");',
         '        sSaveFile = fopen(path, "w+b");')
    once('    if (sSaveFile == NULL)\n'
         '    {\n'
         '        memset(FLASH_BASE, 0xFF, sizeof(FLASH_BASE));\n'
         '        fprintf(stderr, "Unable to open save file: %s\\n", path);\n'
         '        return;\n'
         '    }\n\n'
         '    fseek(sSaveFile, 0, SEEK_END);',
         '    fseek(sSaveFile, 0, SEEK_END);')
    once('    /* Use the same managed profile for flash reads as for save writes. */\n'
         '    FILE * savefile = fopen(sActiveSavePath, "rb");',
         '#ifdef __ANDROID__\n'
         '    FILE * savefile = fopen(sAndroidSavePath, "r+b");\n'
         '#else\n'
         '    FILE * savefile = fopen("pokeemerald.sav", "r+b");\n'
         '#endif')
    once('        fclose(sSaveFile);\n'
         '        sSaveFile = NULL;\n'
         '    }\n'
         '}\n\n'
         '// Key mappings',
         '        fclose(sSaveFile);\n'
         '    }\n'
         '}\n\n'
         '// Key mappings')
    return native
