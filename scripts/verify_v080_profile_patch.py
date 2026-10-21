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

    # M3.3 user-only manual READY: precisely restore the M3.2 SDL2 source.
    # Reviewed M3.3 manual READY change 1
    once("extern int PortLanDedicatedSetManualReady(void);\nextern int PortLanDedicatedToggleReady(void);\n", "")
    # Reviewed M3.3 manual READY change 2
    once("static bool sEhl8ManualReady; /* configured before starting game thread */\nstatic SDL_atomic_t sEhl8ReadyToggles; /* F9 events from SDL thread */\nstatic SDL_atomic_t sEhl8OwnReady; /* 0/1, shown only before START */\nstatic int sEhl8ProcessedReadyToggles; /* game thread only */\n", "")
    # Reviewed M3.3 manual READY change 3
    once("    bool sessionManualReady = false;\n", "")
    # Reviewed M3.3 manual READY change 4
    once("        else if (strcmp(argv[i], \"--session-manual-ready\") == 0)\n            sessionManualReady = true;\n", "")
    # Reviewed M3.3 manual READY change 5
    once("    if (sessionManualReady && !sessionWaitForStart)\n    {\n        fprintf(stderr, \"Manual READY requires EHL8 wait-for-start.\\n\");\n        if (sProfileLocked)\n            sp_unlock(&sActiveProfileLock);\n        return 2;\n    }\n", "")
    # Reviewed M3.3 manual READY change 6
    once("            if (valid && sessionManualReady)\n                valid = PortLanDedicatedSetManualReady() != 0;\n", "")
    # Reviewed M3.3 manual READY change 7
    once("    sEhl8ManualReady = sessionManualReady;\n    SDL_AtomicSet(&sEhl8ReadyToggles, 0);\n    SDL_AtomicSet(&sEhl8OwnReady, sessionManualReady ? 0 : 1);\n    sEhl8ProcessedReadyToggles = 0;\n", "")
    # Reviewed M3.3 manual READY change 8
    once("            if (uiState == 1)\n            {\n                lnet_wait_overlay_room(sdlRenderer, SDL_AtomicGet(&sEhl8RoomSnapshot));\n                if (sEhl8ManualReady)\n                    lnet_wait_overlay_ready_hint(sdlRenderer, SDL_AtomicGet(&sEhl8OwnReady));\n            }\n", "            if (uiState == 1)\n                lnet_wait_overlay_room(sdlRenderer, SDL_AtomicGet(&sEhl8RoomSnapshot));\n")
    # Reviewed M3.3 manual READY change 9
    once("            case SDLK_F9:\n                if (!event.key.repeat && sEhl8ManualReady &&\n                    SDL_AtomicGet(&sEhl8WaitUiState) == 1)\n                    SDL_AtomicAdd(&sEhl8ReadyToggles, 1);\n                break;\n", "")
    # Reviewed M3.3 manual READY change 10
    once("        if (sEhl8ManualReady && !sEhl8StartGate.released)\n        {\n            int count = SDL_AtomicGet(&sEhl8ReadyToggles);\n            while (sEhl8ProcessedReadyToggles != count)\n            {\n                int ready = PortLanDedicatedToggleReady();\n                if (ready >= 0)\n                    SDL_AtomicSet(&sEhl8OwnReady, ready);\n                sEhl8ProcessedReadyToggles++;\n            }\n        }\n", "")

    # M3.2 room roster HUD: exact audited inverse before the protected
    # SDL2 source comparison; unrelated changes still fail the historic hash.
    once('extern int PortLanDedicatedRoomSnapshot(void);\n', '')
    once('static SDL_atomic_t sEhl8RoomSnapshot; /* -1 until validated PLAYER_LIST */\n', '')
    once('    SDL_AtomicSet(&sEhl8RoomSnapshot, -1);\n', '')
    once('        SDL_AtomicSet(&sEhl8RoomSnapshot, PortLanDedicatedRoomSnapshot());\n', '')
    once('        if (sessionWaitForStart)\n'
         '        {\n'
         '            int uiState = SDL_AtomicGet(&sEhl8WaitUiState);\n'
         '            lnet_wait_overlay_render(sdlRenderer, uiState);\n'
         '            if (uiState == 1)\n'
         '                lnet_wait_overlay_room(sdlRenderer, SDL_AtomicGet(&sEhl8RoomSnapshot));\n'
         '        }',
         '        if (sessionWaitForStart)\n'
         '            lnet_wait_overlay_render(sdlRenderer, SDL_AtomicGet(&sEhl8WaitUiState));')

    # M3.0 player-facing room overlay: strictly invert the two reviewed
    # SDL2 insertions before checking the protected legacy source hash.
    once('#include "../lnet/lnet_wait_overlay.h"\n', '')
    once('        /* EHL8 room wait is a real player-facing screen, not just a frozen\n'
         '         * title menu. Keep rendering and network/game ticks alive. */\n'
         '        if (sessionWaitForStart)\n'
         '            lnet_wait_overlay_render(sdlRenderer, SDL_AtomicGet(&sEhl8WaitUiState));\n'
         '\n', '')

    # M3.0 EHL8 gameplay START input gate: reverse only nine precisely
    # enumerated additions. Keep the historic SDL2 blob hash check strict.
    # Reviewed M3.0 START gate addition 1
    once("#include \"../lnet/lnet_start_gate.h\"\n\n/* Controlled on the GBA game thread; no access to renderer from link.c. */\nextern int PortLanDedicatedSessionGate(void);\n\n", "\n")
    # Reviewed M3.0 START gate addition 2
    once("static LNetStartGate sEhl8StartGate;\nstatic SDL_atomic_t sEhl8WaitUiState; /* 0=offline,1=waiting,2=online,3=initial fail,4=reconnecting,5=offline after START */\n", "")
    # Reviewed M3.0 START gate addition 3
    once("    bool sessionWaitForStart = false;\n", "")
    # Reviewed M3.0 START gate addition 4
    once("        else if (strcmp(argv[i], \"--session-wait-for-start\") == 0)\n            sessionWaitForStart = true;\n", "")
    # Reviewed M3.0 START gate addition 5
    once("    if (sessionWaitForStart && !sessionEndpoint)\n    {\n        fprintf(stderr, \"START wait requires an EHL8 session endpoint.\\n\");\n        if (sProfileLocked)\n            sp_unlock(&sActiveProfileLock);\n        return 2;\n    }\n", "")
    # Reviewed M3.0 START gate addition 6
    once("    /* No gameplay key reaches Emerald before EHL8 START on opted-in launches.\n     * The engine must keep running to poll TCP and draw frames while waiting. */\n    sEhl8StartGate.enabled = sessionWaitForStart;\n    sEhl8StartGate.released = 0;\n    SDL_AtomicSet(&sEhl8WaitUiState, sessionWaitForStart ? 1 : 0);\n\n", "")
    # Reviewed M3.0 START gate addition 7
    once("    int lastWaitUiState = -1;\n", "")
    # Reviewed M3.0 START gate addition 8
    once("        if (sessionWaitForStart)\n        {\n            int waitUiState = SDL_AtomicGet(&sEhl8WaitUiState);\n            if (waitUiState != lastWaitUiState)\n            {\n                const char *caption = \"Emerald Hybrid — EHL8 iniciado\";\n                if (waitUiState == 1)\n                    caption = \"Emerald Hybrid — aguardando segundo jogador e START\";\n                else if (waitUiState == 3)\n                    caption = \"Emerald Hybrid — EHL8 falhou; feche para tentar novamente\";\n                else if (waitUiState == 4)\n                    caption = \"Emerald Hybrid — reconectando ao amigo (jogo local liberado)\";\n                else if (waitUiState == 5)\n                    caption = \"Emerald Hybrid — sem conexao EHL8; jogo local liberado\";\n                SDL_SetWindowTitle(sdlWindow, caption);\n                lastWaitUiState = waitUiState;\n            }\n        }\n\n", "\n")
    # Reviewed M3.0 START gate addition 9
    once("    /* Game-thread input gate: do not pause VBlank, gameplay callbacks or\n     * PortLanDebugPump; START can only arrive while frames are progressing.\n     * Once released, a network drop does not re-lock the local trainer. */\n    if (sEhl8StartGate.enabled)\n    {\n        int state = PortLanDedicatedSessionGate();\n        if (!sEhl8StartGate.released)\n        {\n            if (lnet_start_gate_blocked(&sEhl8StartGate, state))\n            {\n                SDL_AtomicSet(&sEhl8WaitUiState, state < 0 ? 3 : 1);\n                return 0;\n            }\n            SDL_AtomicSet(&sEhl8WaitUiState, 2);\n        }\n        else\n        {\n            /* A transient network loss must NOT freeze the solo adventure.\n             * Distinguish reconnecting and permanently failed sessions from\n             * ordinary gameplay using the state already polled by EHL8. */\n            SDL_AtomicSet(&sEhl8WaitUiState, state == 1 ? 2 : (state < 0 ? 5 : 4));\n        }\n    }\n", "")

    # Exact inverse of only the reviewed SDL pending-frame guard.
    once("            else\n            {\n                /* EHL8_FRAME_WAIT: AgbMain has not produced a new frame yet.\n                 * Leave the accumulator loop; otherwise the UI thread can\n                 * spin forever without processing SDL input or shutdown. */\n                break;\n            }\n", '')

    # v0.8 video improvements are small, explicitly allowlisted changes.
    # Remove ONLY these reviewed fragments before hashing the exact old SDL2.
    # Any other change (audio, gameplay, flash, turbo) still fails the audit.
    once('#ifndef __ANDROID__\n'
         '    /* V0802_VIDEO_INIT_BEGIN: auto integer zoom, never force a window offscreen. */\n'
         '    {\n'
         '        SDL_Rect area;\n'
         '        videoScale = 3;\n'
         '        if (SDL_GetDisplayUsableBounds(0, &area) == 0)\n'
         '        {\n'
         '            int maxW = (area.w - 32) / DISPLAY_WIDTH;\n'
         '            int maxH = (area.h - 48) / DISPLAY_HEIGHT;\n'
         '            int fit = maxW < maxH ? maxW : maxH;\n'
         '            if (fit >= 1)\n'
         '                videoScale = (unsigned int)fit;\n'
         '        }\n'
         '    }\n'
         '    /* V0802_VIDEO_INIT_END */\n'
         '#endif\n\n', '')

    once('#ifndef __ANDROID__\n'
         '            /* V0802_VIDEO_KEYS_BEGIN: F11 or Alt+Enter switch borderless fullscreen. */\n'
         '            if (!event.key.repeat && (event.key.keysym.sym == SDLK_F11 ||\n'
         '                (event.key.keysym.sym == SDLK_RETURN && (event.key.keysym.mod & KMOD_ALT))))\n'
         '            {\n'
         '                Uint32 next = (SDL_GetWindowFlags(sdlWindow) & SDL_WINDOW_FULLSCREEN_DESKTOP)\n'
         '                            ? 0 : SDL_WINDOW_FULLSCREEN_DESKTOP;\n'
         '                if (SDL_SetWindowFullscreen(sdlWindow, next) != 0)\n'
         '                    SDL_Log("Fullscreen toggle failed: %s", SDL_GetError());\n'
         '                break;\n'
         '            }\n'
         '            /* V0802_VIDEO_KEYS_END */\n'
         '#endif\n', '')

    # M2/2 parser additions are separately enumerated and reversed; the
    # actual profile block below is already reverted as one audited region.
    once('    const char *sessionEndpoint = NULL;\n'
         '    const char *sessionPin = NULL;\n'
         '    bool sessionPinFromStdin = false;\n'
         '    char sessionPinBuffer[16] = {0};\n'
         '    bool legacyLinkRequested = false;\n', '')
    once('        else if (strcmp(argv[i], "--session-pin-stdin") == 0)\n'
         '            sessionPinFromStdin = true;\n', '')
    once('        else if (strncmp(argv[i], "--session-client=", 17) == 0)\n'
         '            sessionEndpoint = argv[i] + 17;\n'
         '        else if (strncmp(argv[i], "--session-pin=", 14) == 0)\n'
         '            sessionPin = argv[i] + 14;\n', '')
    once('        {\n'
         '            legacyLinkRequested = true;\n'
         '            char *end = NULL;', 
         '        {\n'
         '            char *end = NULL;')
    once('        {\n'
         '            legacyLinkRequested = true;\n'
         '            const char *spec = argv[i] + 13;',
         '        {\n'
         '            const char *spec = argv[i] + 13;')

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
            'ReadSaveFile(sActiveSavePath)' not in old or 'sp_unlock(&sActiveProfileLock)' not in old or \
            old.count('PortLanRequestDedicatedClient(host, (u16)port, sessionPin, profileId)') != 1:
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
