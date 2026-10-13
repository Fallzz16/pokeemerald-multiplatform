"""Inverse of Android-only save-path additions for strict Hybrid SDL QA.

This is deliberately exact-string-based. If native SDL, audio or fast-forward
changes unexpectedly, the reconstructed original Git blob hash will differ.
"""
def strip_android_save_patch(source: str) -> str:
    def change(before: str, after: str, reason: str) -> None:
        nonlocal source
        if source.count(before) != 1:
            raise AssertionError(f"Android SDL patch inverse no longer unique: {reason}")
        source = source.replace(before, after, 1)

    change('static FILE *sSaveFile = NULL;\n'
           '#ifdef __ANDROID__\n'
           'static char sAndroidSavePath[1024] = "pokeemerald.sav";\n'
           '#endif\n',
           'static FILE *sSaveFile = NULL;\n', 'save path variable')

    change('#ifndef __ANDROID__\n'
           '    ReadSaveFile("pokeemerald.sav");\n'
           '#endif\n',
           '    ReadSaveFile("pokeemerald.sav");\n', 'legacy desktop path')

    change('''#ifdef __ANDROID__
    // Android must open save files inside the application's writable storage.
    // SDL_GetPrefPath is available only after SDL_Init.
    {
        char *prefPath = SDL_GetPrefPath("EmeraldHybrid", "EmeraldHybrid");
        if (prefPath == NULL)
        {
            SDL_Log("Unable to obtain Android writable save path");
            return 1;
        }
        SDL_snprintf(sAndroidSavePath, sizeof(sAndroidSavePath), "%spokeemerald.sav", prefPath);
        SDL_free(prefPath);
        ReadSaveFile(sAndroidSavePath);
    }
#endif

    sdlWindow = SDL_CreateWindow(''',
           '    sdlWindow = SDL_CreateWindow(', 'Android SDL storage setup')

    change('''#ifdef __ANDROID__
    if (sSaveFile == NULL)
    {
        memset(FLASH_BASE, 0xFF, sizeof(FLASH_BASE));
        SDL_Log("Unable to open Android save file: %s", path);
        return;
    }
#endif

    fseek(sSaveFile, 0, SEEK_END);''',
           '    fseek(sSaveFile, 0, SEEK_END);', 'Android save failure guard')

    change('''#ifdef __ANDROID__
    FILE * savefile = fopen(sAndroidSavePath, "r+b");
#else
    FILE * savefile = fopen("pokeemerald.sav", "r+b");
#endif''',
           '    FILE * savefile = fopen("pokeemerald.sav", "r+b");',
           'Android flash sector reads')
    return source
