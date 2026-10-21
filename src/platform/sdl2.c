#ifdef PLATFORM_SDL2
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#include <windows.h>
#include <xinput.h>
#endif

#ifdef __ANDROID__
#include <SDL.h>
#else
#include <SDL2/SDL.h>
#endif

#include "global.h"
#include "platform.h"
#include "link.h"
#include "rtc.h"
#include "gba/defines.h"
#include "gba/m4a_internal.h"
#include "cgb_audio.h"
#include "gba/flash_internal.h"
#include "platform/dma.h"
#include "platform/framedraw.h"
/* Optional v0.8 managed profiles; legacy save remains the default. */
#include "../profile/save_profiles.h"
#include "../lnet/lnet_start_gate.h"
#include "../lnet/lnet_wait_overlay.h"

/* Controlled on the GBA game thread; no access to renderer from link.c. */
extern int PortLanDedicatedSessionGate(void);
extern int PortLanDedicatedRoomSnapshot(void);
extern int PortLanDedicatedSetManualReady(void);
extern int PortLanDedicatedToggleReady(void);

extern void (*const gIntrTable[])(void);

SDL_Thread *mainLoopThread;
SDL_Window *sdlWindow;
SDL_Renderer *sdlRenderer;
SDL_Texture *sdlTexture;
SDL_sem *vBlankSemaphore;
SDL_atomic_t isFrameAvailable;
SDL_atomic_t fastForwardActive;
SDL_atomic_t fastForwardMultiplier;
unsigned int videoScale = 1;
bool isRunning = true;
double lastGameTime = 0;
double curGameTime = 0;
double fixedTimestep = 1.0 / 60.0; // Port timing; one game tick per frame
struct SiiRtcInfo internalClock;

static FILE *sSaveFile = NULL;
static char sActiveSavePath[SP_PATH_CAP] = "pokeemerald.sav";
static SpProfileLock sActiveProfileLock;
static bool sProfileLocked = false;
static LNetStartGate sEhl8StartGate;
static SDL_atomic_t sEhl8WaitUiState; /* 0=offline,1=waiting,2=online,3=initial fail,4=reconnecting,5=offline after START */
static SDL_atomic_t sEhl8RoomSnapshot; /* -1 until validated PLAYER_LIST */
static bool sEhl8ManualReady; /* configured before starting game thread */
static SDL_atomic_t sEhl8ReadyToggles; /* F9 events from SDL thread */
static SDL_atomic_t sEhl8OwnReady; /* 0/1, shown only before START */
static int sEhl8ProcessedReadyToggles; /* game thread only */
#ifdef __ANDROID__
static char sAndroidSavePath[1024] = "pokeemerald.sav";
#endif

extern void AgbMain(void);

int DoMain(void *param);
void ProcessEvents(void);
void VDraw(SDL_Texture *texture);

static void RenderFastForwardIndicator(void);
static void CycleFastForwardMultiplier(void);

static void ReadSaveFile(char *path);
static void StoreSaveFile(void);
static void CloseSaveFile(void);

static void UpdateInternalClock(void);

int main(int argc, char **argv)
{
    const char *profileRoot = NULL;
    const char *profileId = NULL;
    const char *sessionEndpoint = NULL;
    const char *sessionPin = NULL;
    bool sessionPinFromStdin = false;
    bool sessionWaitForStart = false;
    bool sessionManualReady = false;
    char sessionPinBuffer[16] = {0};
    bool legacyLinkRequested = false;
    // Optional headless LAN configuration on desktop. The in-game Cable Club
    // still performs the real Emerald link handshake after the TCP peer joins.
    // Accept only valid 1..65535 ports; never auto-advance game state.
    for (int i = 1; i < argc; i++)
    {
        if (strcmp(argv[i], "--lan-log") == 0 && i + 1 < argc)
        {
            PortLanSetLogFile(argv[++i]);
        }
    }
    for (int i = 1; i < argc; i++)
    {
        if (strncmp(argv[i], "--profile-root=", 15) == 0)
            profileRoot = argv[i] + 15;
        else if (strncmp(argv[i], "--profile-id=", 13) == 0)
            profileId = argv[i] + 13;
        else if (strncmp(argv[i], "--session-client=", 17) == 0)
            sessionEndpoint = argv[i] + 17;
        else if (strncmp(argv[i], "--session-pin=", 14) == 0)
            sessionPin = argv[i] + 14;
        else if (strcmp(argv[i], "--session-pin-stdin") == 0)
            sessionPinFromStdin = true;
        else if (strcmp(argv[i], "--session-wait-for-start") == 0)
            sessionWaitForStart = true;
        else if (strcmp(argv[i], "--session-manual-ready") == 0)
            sessionManualReady = true;
        else if (strncmp(argv[i], "--lan-host=", 11) == 0)
        {
            legacyLinkRequested = true;
            char *end = NULL;
            unsigned long port = strtoul(argv[i] + 11, &end, 10);
            if (end && *end == '\0' && port > 0 && port <= 65535)
                PortLanRequestHost((u16)port);
        }
        else if (strncmp(argv[i], "--lan-client=", 13) == 0)
        {
            legacyLinkRequested = true;
            const char *spec = argv[i] + 13;
            const char *colon = strrchr(spec, ':');
            if (colon != NULL && colon > spec && (colon - spec) < 64)
            {
                char ip[64];
                char *end = NULL;
                unsigned long port = strtoul(colon + 1, &end, 10);
                if (end && *end == '\0' && port > 0 && port <= 65535)
                {
                    memcpy(ip, spec, colon - spec);
                    ip[colon - spec] = '\0';
                    PortLanRequestClient(ip, (u16)port);
                }
            }
        }
    }

    /* Managed profiles opt in explicitly; missing/busy profiles must fail
     * rather than silently open the wrong trainer's legacy save. */
    if (profileRoot != NULL || profileId != NULL)
    {
        int n;
        SpStatus status;
        if (profileRoot == NULL || profileId == NULL ||
            !*profileRoot || !sp_valid_id(profileId))
        {
            fprintf(stderr, "Invalid profile: supply --profile-root and --profile-id\n");
            return 2;
        }
        status = sp_lock(profileRoot, profileId, &sActiveProfileLock);
        if (status != SP_OK)
        {
            fprintf(stderr, "Could not lock selected profile (code %d)\n", (int)status);
            return 2;
        }
        n = snprintf(sActiveSavePath, sizeof(sActiveSavePath),
                     "%s/pokeemerald.sav", sActiveProfileLock.directory);
        if (n < 0 || n >= (int)sizeof(sActiveSavePath))
        {
            sp_unlock(&sActiveProfileLock);
            fprintf(stderr, "Selected profile path is too long\n");
            return 2;
        }
        sProfileLocked = true;
    }
    /* An EHL8 session is NOT the legacy raw-SIO LAN connection.
     * Both a selected profile and a six-digit PIN are mandatory.
     * Reject mixed modes; never quietly fall back to another save/trainer. */
    if (sessionManualReady && !sessionWaitForStart)
    {
        fprintf(stderr, "Manual READY requires EHL8 wait-for-start.\n");
        if (sProfileLocked)
            sp_unlock(&sActiveProfileLock);
        return 2;
    }
    if (sessionWaitForStart && !sessionEndpoint)
    {
        fprintf(stderr, "START wait requires an EHL8 session endpoint.\n");
        if (sProfileLocked)
            sp_unlock(&sActiveProfileLock);
        return 2;
    }
    if (sessionEndpoint || sessionPin || sessionPinFromStdin)
    {
        if (sessionPinFromStdin && sessionPin == NULL &&
            fgets(sessionPinBuffer, sizeof(sessionPinBuffer), stdin) != NULL)
        {
            sessionPinBuffer[strcspn(sessionPinBuffer, "\r\n")] = '\0';
            sessionPin = sessionPinBuffer;
        }
        else if (sessionPinFromStdin)
        {
            sessionPin = NULL; /* wrong/missing PIN or mixed secret sources */
        }
        const char *colon = sessionEndpoint ? strrchr(sessionEndpoint, ':') : NULL;
        char host[64];
        char *end = NULL;
        unsigned long port = 0;
        bool valid = sessionEndpoint && sessionPin && profileId &&
                     !legacyLinkRequested && strlen(sessionPin) == 6 &&
                     colon && colon > sessionEndpoint &&
                     (colon - sessionEndpoint) < (int)sizeof(host);
        if (valid)
        {
            int n;
            for (n = 0; n < 6; n++)
                if (sessionPin[n] < '0' || sessionPin[n] > '9')
                    valid = false;
            port = strtoul(colon + 1, &end, 10);
            if (!end || *end != '\0' || port < 1 || port > 65534)
                valid = false;
        }
        if (valid)
        {
            memcpy(host, sessionEndpoint, colon - sessionEndpoint);
            host[colon - sessionEndpoint] = '\0';
            valid = PortLanRequestDedicatedClient(host, (u16)port, sessionPin, profileId);
            if (valid && sessionManualReady)
                valid = PortLanDedicatedSetManualReady() != 0;
        }
        memset(sessionPinBuffer, 0, sizeof(sessionPinBuffer));
        if (!valid)
        {
            fprintf(stderr, "Invalid EHL8 session configuration: "
                    "requires selected profile, IPv4:port and 6-digit PIN; "
                    "cannot mix with legacy LAN flags.\\n");
            if (sProfileLocked)
                sp_unlock(&sActiveProfileLock);
            return 2;
        }
    }

#ifndef __ANDROID__
    ReadSaveFile(sActiveSavePath);
    if (sSaveFile == NULL)
    {
        if (sProfileLocked)
            sp_unlock(&sActiveProfileLock);
        return 2;
    }
#endif

    /* No gameplay key reaches Emerald before EHL8 START on opted-in launches.
     * The engine must keep running to poll TCP and draw frames while waiting. */
    sEhl8StartGate.enabled = sessionWaitForStart;
    sEhl8StartGate.released = 0;
    SDL_AtomicSet(&sEhl8WaitUiState, sessionWaitForStart ? 1 : 0);
    SDL_AtomicSet(&sEhl8RoomSnapshot, -1);
    sEhl8ManualReady = sessionManualReady;
    SDL_AtomicSet(&sEhl8ReadyToggles, 0);
    SDL_AtomicSet(&sEhl8OwnReady, sessionManualReady ? 0 : 1);
    sEhl8ProcessedReadyToggles = 0;

    if(SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO) < 0)
    {
        DBGPRINTF("SDL could not initialize! SDL_Error: %s\n", SDL_GetError());
        return 1;
    }

#ifdef __ANDROID__
    // Android must open save files inside the application's writable storage.
    // SDL_GetPrefPath is available only after SDL_Init.
    {
        char *prefPath = SDL_GetPrefPath("EmeraldHybrid", "EmeraldHybrid");
        if (prefPath == NULL)
        {
            SDL_Log("Unable to obtain Android writable save path");
            return 1;
        }
        if (!sProfileLocked)
            SDL_snprintf(sActiveSavePath, sizeof(sActiveSavePath),
                         "%spokeemerald.sav", prefPath);
        SDL_free(prefPath);
        ReadSaveFile(sActiveSavePath);
        if (sSaveFile == NULL)
        {
            if (sProfileLocked)
                sp_unlock(&sActiveProfileLock);
            SDL_Quit();
            return 2;
        }
    }
#endif

#ifndef __ANDROID__
    /* V0802_VIDEO_INIT_BEGIN: auto integer zoom, never force a window offscreen. */
    {
        SDL_Rect area;
        videoScale = 3;
        if (SDL_GetDisplayUsableBounds(0, &area) == 0)
        {
            int maxW = (area.w - 32) / DISPLAY_WIDTH;
            int maxH = (area.h - 48) / DISPLAY_HEIGHT;
            int fit = maxW < maxH ? maxW : maxH;
            if (fit >= 1)
                videoScale = (unsigned int)fit;
        }
    }
    /* V0802_VIDEO_INIT_END */
#endif

    sdlWindow = SDL_CreateWindow("pokeemerald", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, DISPLAY_WIDTH * videoScale, DISPLAY_HEIGHT * videoScale, SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE);
    if (sdlWindow == NULL)
    {
        DBGPRINTF("Window could not be created! SDL_Error: %s\n", SDL_GetError());
        return 1;
    }

    sdlRenderer = SDL_CreateRenderer(sdlWindow, -1, SDL_RENDERER_PRESENTVSYNC);
    if (sdlRenderer == NULL)
    {
        DBGPRINTF("Renderer could not be created! SDL_Error: %s\n", SDL_GetError());
        return 1;
    }

    SDL_SetRenderDrawColor(sdlRenderer, 0, 0, 0, 255);
    SDL_RenderClear(sdlRenderer);
    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "0");
    SDL_RenderSetLogicalSize(sdlRenderer, DISPLAY_WIDTH, DISPLAY_HEIGHT);
    SDL_RenderSetIntegerScale(sdlRenderer, SDL_TRUE);

    sdlTexture = SDL_CreateTexture(sdlRenderer,
                                   SDL_PIXELFORMAT_ABGR1555,
                                   SDL_TEXTUREACCESS_STREAMING,
                                   DISPLAY_WIDTH, DISPLAY_HEIGHT);
    if (sdlTexture == NULL)
    {
        DBGPRINTF("Texture could not be created! SDL_Error: %s\n", SDL_GetError());
        return 1;
    }

    curGameTime = lastGameTime = SDL_GetPerformanceCounter();

    isFrameAvailable.value = 0;
    SDL_AtomicSet(&fastForwardActive, 0);
    SDL_AtomicSet(&fastForwardMultiplier, 2);
    vBlankSemaphore = SDL_CreateSemaphore(0);

    SDL_AudioSpec want;

    SDL_memset(&want, 0, sizeof(want)); /* or SDL_zero(want) */
    want.freq = 42060;
    want.format = AUDIO_F32;
    want.channels = 2;
    want.samples = 1024;
    cgb_audio_init(want.freq);


    if (SDL_OpenAudio(&want, 0) < 0)
        SDL_Log("Failed to open audio: %s", SDL_GetError());
    else
    {
        if (want.format != AUDIO_F32) /* we let this one thing change. */
            SDL_Log("We didn't get Float32 audio format.");
        SDL_PauseAudio(0);
    }
    
    VDraw(sdlTexture);
    mainLoopThread = SDL_CreateThread(DoMain, "AgbMain", NULL);

    double accumulator = 0.0;

    memset(&internalClock, 0, sizeof(internalClock));
    internalClock.status = SIIRTCINFO_24HOUR;
    UpdateInternalClock();

    int lastWaitUiState = -1;
    while (isRunning)
    {
        ProcessEvents();
        if (sessionWaitForStart)
        {
            int waitUiState = SDL_AtomicGet(&sEhl8WaitUiState);
            if (waitUiState != lastWaitUiState)
            {
                const char *caption = "Emerald Hybrid — EHL8 iniciado";
                if (waitUiState == 1)
                    caption = "Emerald Hybrid — aguardando segundo jogador e START";
                else if (waitUiState == 3)
                    caption = "Emerald Hybrid — EHL8 falhou; feche para tentar novamente";
                else if (waitUiState == 4)
                    caption = "Emerald Hybrid — reconectando ao amigo (jogo local liberado)";
                else if (waitUiState == 5)
                    caption = "Emerald Hybrid — sem conexao EHL8; jogo local liberado";
                SDL_SetWindowTitle(sdlWindow, caption);
                lastWaitUiState = waitUiState;
            }
        }

        const int speedMultiplier = SDL_AtomicGet(&fastForwardActive)
                                  ? SDL_AtomicGet(&fastForwardMultiplier)
                                  : 1;
        const double dt = fixedTimestep / speedMultiplier;

        curGameTime = SDL_GetPerformanceCounter();
        double deltaTime = (double)((curGameTime - lastGameTime) / (double)SDL_GetPerformanceFrequency());
        if (deltaTime > (dt * 5))
            deltaTime = dt;
        lastGameTime = curGameTime;

        accumulator += deltaTime;

        while (accumulator >= dt)
        {
            if (SDL_AtomicGet(&isFrameAvailable))
            {
                VDraw(sdlTexture);
                SDL_RenderClear(sdlRenderer);
                SDL_RenderCopy(sdlRenderer, sdlTexture, NULL, NULL);
                SDL_AtomicSet(&isFrameAvailable, 0);

                REG_DISPSTAT |= INTR_FLAG_VBLANK;

                RunDMAs(DMA_HBLANK);

                if (REG_DISPSTAT & DISPSTAT_VBLANK_INTR)
                    gIntrTable[4]();
                REG_DISPSTAT &= ~INTR_FLAG_VBLANK;

                SDL_SemPost(vBlankSemaphore);

                accumulator -= dt;
            }
            else
            {
                /* EHL8_FRAME_WAIT: AgbMain has not produced a new frame yet.
                 * Leave the accumulator loop; otherwise the UI thread can
                 * spin forever without processing SDL input or shutdown. */
                break;
            }
        }

        if (SDL_AtomicGet(&fastForwardActive))
            RenderFastForwardIndicator();

        /* EHL8 room wait is a real player-facing screen, not just a frozen
         * title menu. Keep rendering and network/game ticks alive. */
        if (sessionWaitForStart)
        {
            int uiState = SDL_AtomicGet(&sEhl8WaitUiState);
            lnet_wait_overlay_render(sdlRenderer, uiState);
            if (uiState == 1)
            {
                lnet_wait_overlay_room(sdlRenderer, SDL_AtomicGet(&sEhl8RoomSnapshot));
                if (sEhl8ManualReady)
                    lnet_wait_overlay_ready_hint(sdlRenderer, SDL_AtomicGet(&sEhl8OwnReady));
            }
        }

        SDL_RenderPresent(sdlRenderer);
    }

    //StoreSaveFile();
    CloseSaveFile();
    /* Hold this OS lock until every flash read/write thread has stopped. */
    if (sProfileLocked)
        sp_unlock(&sActiveProfileLock);

    SDL_DestroyWindow(sdlWindow);
    SDL_Quit();
    return 0;
}

static void ReadSaveFile(char *path)
{
    // Check whether the saveFile exists, and create it if not
    sSaveFile = fopen(path, "r+b");
    if (sSaveFile == NULL)
    {
        if (!sProfileLocked)
            sSaveFile = fopen(path, "w+b");
    }

#ifdef __ANDROID__
    if (sSaveFile == NULL)
    {
        memset(FLASH_BASE, 0xFF, sizeof(FLASH_BASE));
        SDL_Log("Unable to open Android save file: %s", path);
        return;
    }
#endif

    if (sSaveFile == NULL)
    {
        memset(FLASH_BASE, 0xFF, sizeof(FLASH_BASE));
        fprintf(stderr, "Unable to open save file: %s\n", path);
        return;
    }

    fseek(sSaveFile, 0, SEEK_END);
    int fileSize = ftell(sSaveFile);
    fseek(sSaveFile, 0, SEEK_SET);

    // Only read as many bytes as fit inside the buffer
    // or as many bytes as are in the file
    int bytesToRead = (fileSize < sizeof(FLASH_BASE)) ? fileSize : sizeof(FLASH_BASE);

    int bytesRead = fread(FLASH_BASE, 1, bytesToRead, sSaveFile);

    // Fill the buffer if the savefile was just created or smaller than the buffer itself
    for (int i = bytesRead; i < sizeof(FLASH_BASE); i++)
    {
        FLASH_BASE[i] = 0xFF;
    }
}

static void StoreSaveFile()
{
    if (sSaveFile != NULL)
    {
        fseek(sSaveFile, 0, SEEK_SET);
        fwrite(FLASH_BASE, 1, sizeof(FLASH_BASE), sSaveFile);
    }
}

void Platform_StoreSaveFile(void)
{
    StoreSaveFile();
}

void Platform_ReadFlash(u16 sectorNum, u32 offset, u8 *dest, u32 size)
{
    DBGPRINTF("ReadFlash(sectorNum=0x%04X,offset=0x%08X,size=0x%02X)\n",sectorNum,offset,size);
    /* Use the same managed profile for flash reads as for save writes. */
    FILE * savefile = fopen(sActiveSavePath, "rb");
    if (savefile == NULL)
    {
        puts("Error opening save file.");
        return;
    }
    if (fseek(savefile, (sectorNum << gFlash->sector.shift) + offset, SEEK_SET))
    {
        fclose(savefile);
        return;
    }
    if (fread(dest, 1, size, savefile) != size)
    {
        fclose(savefile);
        return;
    }
    fclose(savefile);
}

void Platform_QueueAudio(float *audioBuffer, s32 audioBytes)
{
    // Keep the normal-speed path exactly equivalent to the stable v0.3.1 build.
    if (!SDL_AtomicGet(&fastForwardActive))
    {
        SDL_QueueAudio(1, audioBuffer, audioBytes);
        return;
    }

    // During fast-forward the whole game clock runs N times faster, including
    // BGM, sound effects and cries. Compact the final interleaved stereo stream
    // by the same factor so SDL still receives roughly one real-time second of
    // audio per real-time second. This produces traditional turbo pitch/tempo.
    enum { MAX_FAST_FORWARD_AUDIO_FLOATS = 4096 };
    static float compressedAudio[MAX_FAST_FORWARD_AUDIO_FLOATS];
    const int multiplier = SDL_AtomicGet(&fastForwardMultiplier);
    const s32 inputFrames = audioBytes / (s32)(sizeof(float) * 2);
    s32 outputFrames = 0;

    for (s32 sourceFrame = 0;
         sourceFrame < inputFrames && (outputFrames * 2 + 1) < MAX_FAST_FORWARD_AUDIO_FLOATS;
         sourceFrame += multiplier)
    {
        compressedAudio[outputFrames * 2]     = audioBuffer[sourceFrame * 2];
        compressedAudio[outputFrames * 2 + 1] = audioBuffer[sourceFrame * 2 + 1];
        outputFrames++;
    }

    SDL_QueueAudio(1, compressedAudio, outputFrames * 2 * (s32)sizeof(float));
}


static void CloseSaveFile()
{
    if (sSaveFile != NULL)
    {
        fclose(sSaveFile);
        sSaveFile = NULL;
    }
}

// Key mappings
#define KEY_A_BUTTON      SDLK_z
#define KEY_B_BUTTON      SDLK_x
#define KEY_START_BUTTON  SDLK_RETURN
#define KEY_SELECT_BUTTON SDLK_BACKSLASH
#define KEY_L_BUTTON      SDLK_a
#define KEY_R_BUTTON      SDLK_s
#define KEY_DPAD_UP       SDLK_UP
#define KEY_DPAD_DOWN     SDLK_DOWN
#define KEY_DPAD_LEFT     SDLK_LEFT
#define KEY_DPAD_RIGHT    SDLK_RIGHT

#define HANDLE_KEYUP(key) \
case KEY_##key:  keys &= ~key; break;

#define HANDLE_KEYDOWN(key) \
case KEY_##key:  keys |= key; break;

static u16 keys;

void ProcessEvents(void)
{
    SDL_Event event;

    while (SDL_PollEvent(&event))
    {
        switch (event.type)
        {
        case SDL_QUIT:
            isRunning = false;
            break;
        case SDL_KEYUP:
            switch (event.key.keysym.sym)
            {
            HANDLE_KEYUP(A_BUTTON)
            HANDLE_KEYUP(B_BUTTON)
            HANDLE_KEYUP(START_BUTTON)
            HANDLE_KEYUP(SELECT_BUTTON)
            HANDLE_KEYUP(L_BUTTON)
            HANDLE_KEYUP(R_BUTTON)
            HANDLE_KEYUP(DPAD_UP)
            HANDLE_KEYUP(DPAD_DOWN)
            HANDLE_KEYUP(DPAD_LEFT)
            HANDLE_KEYUP(DPAD_RIGHT)
            case SDLK_TAB:
                SDL_AtomicSet(&fastForwardActive, 0);
                break;
            }
            break;
        case SDL_KEYDOWN:
#ifndef __ANDROID__
            /* V0802_VIDEO_KEYS_BEGIN: F11 or Alt+Enter switch borderless fullscreen. */
            if (!event.key.repeat && (event.key.keysym.sym == SDLK_F11 ||
                (event.key.keysym.sym == SDLK_RETURN && (event.key.keysym.mod & KMOD_ALT))))
            {
                Uint32 next = (SDL_GetWindowFlags(sdlWindow) & SDL_WINDOW_FULLSCREEN_DESKTOP)
                            ? 0 : SDL_WINDOW_FULLSCREEN_DESKTOP;
                if (SDL_SetWindowFullscreen(sdlWindow, next) != 0)
                    SDL_Log("Fullscreen toggle failed: %s", SDL_GetError());
                break;
            }
            /* V0802_VIDEO_KEYS_END */
#endif
            switch (event.key.keysym.sym)
            {
            HANDLE_KEYDOWN(A_BUTTON)
            HANDLE_KEYDOWN(B_BUTTON)
            HANDLE_KEYDOWN(START_BUTTON)
            HANDLE_KEYDOWN(SELECT_BUTTON)
            HANDLE_KEYDOWN(L_BUTTON)
            HANDLE_KEYDOWN(R_BUTTON)
            HANDLE_KEYDOWN(DPAD_UP)
            HANDLE_KEYDOWN(DPAD_DOWN)
            HANDLE_KEYDOWN(DPAD_LEFT)
            HANDLE_KEYDOWN(DPAD_RIGHT)
            case SDLK_TAB:
                if (!event.key.repeat)
                    SDL_AtomicSet(&fastForwardActive, 1);
                break;
            case SDLK_F6:
                if (!event.key.repeat)
                    CycleFastForwardMultiplier();
                break;
            case SDLK_F9:
                if (!event.key.repeat && sEhl8ManualReady &&
                    SDL_AtomicGet(&sEhl8WaitUiState) == 1)
                    SDL_AtomicAdd(&sEhl8ReadyToggles, 1);
                break;
            }
            break;
        }
    }
}

#ifdef _WIN32
#define STICK_THRESHOLD 0.5f
u16 GetXInputKeys()
{
    XINPUT_STATE state;
    ZeroMemory(&state, sizeof(XINPUT_STATE));

    DWORD dwResult = XInputGetState(0, &state);
    u16 xinputKeys = 0;

    if (dwResult == ERROR_SUCCESS)
    {
        /* A */      xinputKeys |= (state.Gamepad.wButtons & XINPUT_GAMEPAD_A) >> 12;
        /* B */      xinputKeys |= (state.Gamepad.wButtons & XINPUT_GAMEPAD_X) >> 13;
        /* Start */  xinputKeys |= (state.Gamepad.wButtons & XINPUT_GAMEPAD_START) >> 1;
        /* Select */ xinputKeys |= (state.Gamepad.wButtons & XINPUT_GAMEPAD_BACK) >> 3;
        /* L */      xinputKeys |= (state.Gamepad.wButtons & XINPUT_GAMEPAD_LEFT_SHOULDER) << 1;
        /* R */      xinputKeys |= (state.Gamepad.wButtons & XINPUT_GAMEPAD_RIGHT_SHOULDER) >> 1;
        /* Up */     xinputKeys |= (state.Gamepad.wButtons & XINPUT_GAMEPAD_DPAD_UP) << 6;
        /* Down */   xinputKeys |= (state.Gamepad.wButtons & XINPUT_GAMEPAD_DPAD_DOWN) << 6;
        /* Left */   xinputKeys |= (state.Gamepad.wButtons & XINPUT_GAMEPAD_DPAD_LEFT) << 3;
        /* Right */  xinputKeys |= (state.Gamepad.wButtons & XINPUT_GAMEPAD_DPAD_RIGHT) << 1;


        /* Control Stick */
        float xAxis = (float)state.Gamepad.sThumbLX / (float)SHRT_MAX;
        float yAxis = (float)state.Gamepad.sThumbLY / (float)SHRT_MAX;

        if (xAxis < -STICK_THRESHOLD) xinputKeys |= DPAD_LEFT;
        if (xAxis >  STICK_THRESHOLD) xinputKeys |= DPAD_RIGHT;
        if (yAxis < -STICK_THRESHOLD) xinputKeys |= DPAD_DOWN;
        if (yAxis >  STICK_THRESHOLD) xinputKeys |= DPAD_UP;
    }

    return xinputKeys;
}
#endif // _WIN32

static void CycleFastForwardMultiplier(void)
{
    const int current = SDL_AtomicGet(&fastForwardMultiplier);
    int next;

    switch (current)
    {
    case 2:
        next = 4;
        break;
    case 4:
        next = 8;
        break;
    default:
        next = 2;
        break;
    }

    SDL_AtomicSet(&fastForwardMultiplier, next);
}

static void DrawFastForwardGlyph(const u8 rows[5], int x, int y)
{
    SDL_Rect pixel = {0, 0, 1, 1};

    for (int row = 0; row < 5; row++)
    {
        for (int col = 0; col < 3; col++)
        {
            if (rows[row] & (1 << (2 - col)))
            {
                pixel.x = x + col;
                pixel.y = y + row;
                SDL_RenderFillRect(sdlRenderer, &pixel);
            }
        }
    }
}

static void RenderFastForwardIndicator(void)
{
    static const u8 glyphGreater[5] = {0x4, 0x2, 0x1, 0x2, 0x4};
    static const u8 glyph2[5]       = {0x7, 0x1, 0x7, 0x4, 0x7};
    static const u8 glyph4[5]       = {0x5, 0x5, 0x7, 0x1, 0x1};
    static const u8 glyph8[5]       = {0x7, 0x5, 0x7, 0x5, 0x7};
    static const u8 glyphX[5]       = {0x5, 0x5, 0x2, 0x5, 0x5};
    const int multiplier = SDL_AtomicGet(&fastForwardMultiplier);
    const u8 *digit;
    SDL_Rect box = {DISPLAY_WIDTH - 27, 4, 23, 9};

    switch (multiplier)
    {
    case 4:
        digit = glyph4;
        break;
    case 8:
        digit = glyph8;
        break;
    default:
        digit = glyph2;
        break;
    }

    SDL_SetRenderDrawBlendMode(sdlRenderer, SDL_BLENDMODE_BLEND);
    SDL_SetRenderDrawColor(sdlRenderer, 0, 0, 0, 190);
    SDL_RenderFillRect(sdlRenderer, &box);

    SDL_SetRenderDrawColor(sdlRenderer, 255, 255, 255, 255);
    DrawFastForwardGlyph(glyphGreater, DISPLAY_WIDTH - 24, 6);
    DrawFastForwardGlyph(glyphGreater, DISPLAY_WIDTH - 20, 6);
    DrawFastForwardGlyph(digit,        DISPLAY_WIDTH - 14, 6);
    DrawFastForwardGlyph(glyphX,       DISPLAY_WIDTH - 10, 6);

    SDL_SetRenderDrawBlendMode(sdlRenderer, SDL_BLENDMODE_NONE);
    SDL_SetRenderDrawColor(sdlRenderer, 0, 0, 0, 255);
}

u16 Platform_GetKeyInput(void)
{
    /* Game-thread input gate: do not pause VBlank, gameplay callbacks or
     * PortLanDebugPump; START can only arrive while frames are progressing.
     * Once released, a network drop does not re-lock the local trainer. */
    if (sEhl8StartGate.enabled)
    {
        int state = PortLanDedicatedSessionGate();
        SDL_AtomicSet(&sEhl8RoomSnapshot, PortLanDedicatedRoomSnapshot());
        if (sEhl8ManualReady && !sEhl8StartGate.released)
        {
            int count = SDL_AtomicGet(&sEhl8ReadyToggles);
            while (sEhl8ProcessedReadyToggles != count)
            {
                int ready = PortLanDedicatedToggleReady();
                if (ready >= 0)
                    SDL_AtomicSet(&sEhl8OwnReady, ready);
                sEhl8ProcessedReadyToggles++;
            }
        }
        if (!sEhl8StartGate.released)
        {
            if (lnet_start_gate_blocked(&sEhl8StartGate, state))
            {
                SDL_AtomicSet(&sEhl8WaitUiState, state < 0 ? 3 : 1);
                return 0;
            }
            SDL_AtomicSet(&sEhl8WaitUiState, 2);
        }
        else
        {
            /* A transient network loss must NOT freeze the solo adventure.
             * Distinguish reconnecting and permanently failed sessions from
             * ordinary gameplay using the state already polled by EHL8. */
            SDL_AtomicSet(&sEhl8WaitUiState, state == 1 ? 2 : (state < 0 ? 5 : 4));
        }
    }
#ifdef _WIN32
    u16 gamepadKeys = GetXInputKeys();
    return (gamepadKeys != 0) ? gamepadKeys : keys;
#endif

    return keys;
}

void VDraw(SDL_Texture *texture)
{
    static uint16_t image[DISPLAY_WIDTH * DISPLAY_HEIGHT];

    memset(image, 0, sizeof(image));
    DrawFrame(image);
    SDL_UpdateTexture(texture, NULL, image, DISPLAY_WIDTH * sizeof (Uint16));
    REG_VCOUNT = 161; // prep for being in VBlank period
}

int DoMain(void *data)
{
    AgbMain();
}

void VBlankIntrWait(void)
{
    SDL_AtomicSet(&isFrameAvailable, 1);
    SDL_SemWait(vBlankSemaphore);
}

u8 BinToBcd(u8 bin)
{
    int placeCounter = 1;
    u8 out = 0;
    do
    {
        out |= (bin % 10) * placeCounter;
        placeCounter *= 16;
    }
    while ((bin /= 10) > 0);

    return out;
}

void Platform_GetStatus(struct SiiRtcInfo *rtc)
{
    rtc->status = internalClock.status;
}

void Platform_SetStatus(struct SiiRtcInfo *rtc)
{
    internalClock.status = rtc->status;
}

static void UpdateInternalClock(void)
{
    time_t rawTime = time(NULL);
    struct tm *time = localtime(&rawTime);

    internalClock.year = BinToBcd(time->tm_year - 100);
    internalClock.month = BinToBcd(time->tm_mon + 1);
    internalClock.day = BinToBcd(time->tm_mday);
    internalClock.dayOfWeek = BinToBcd(time->tm_wday);
    internalClock.hour = BinToBcd(time->tm_hour);
    internalClock.minute = BinToBcd(time->tm_min);
    internalClock.second = BinToBcd(time->tm_sec);
}

void Platform_GetDateTime(struct SiiRtcInfo *rtc)
{
    UpdateInternalClock();

    rtc->year = internalClock.year;
    rtc->month = internalClock.month;
    rtc->day = internalClock.day;
    rtc->dayOfWeek = internalClock.dayOfWeek;
    rtc->hour = internalClock.hour;
    rtc->minute = internalClock.minute;
    rtc->second = internalClock.second;
    DBGPRINTF("GetDateTime: %d-%02d-%02d %02d:%02d:%02d\n", ConvertBcdToBinary(rtc->year),
                                                         ConvertBcdToBinary(rtc->month),
                                                         ConvertBcdToBinary(rtc->day),
                                                         ConvertBcdToBinary(rtc->hour),
                                                         ConvertBcdToBinary(rtc->minute),
                                                         ConvertBcdToBinary(rtc->second));
}

void Platform_SetDateTime(struct SiiRtcInfo *rtc)
{
    internalClock.month = rtc->month;
    internalClock.day = rtc->day;
    internalClock.dayOfWeek = rtc->dayOfWeek;
    internalClock.hour = rtc->hour;
    internalClock.minute = rtc->minute;
    internalClock.second = rtc->second;
}

void Platform_GetTime(struct SiiRtcInfo *rtc)
{
    UpdateInternalClock();

    rtc->hour = internalClock.hour;
    rtc->minute = internalClock.minute;
    rtc->second = internalClock.second;
    DBGPRINTF("GetTime: %02d:%02d:%02d\n", ConvertBcdToBinary(rtc->hour),
                                        ConvertBcdToBinary(rtc->minute),
                                        ConvertBcdToBinary(rtc->second));
}

void Platform_SetTime(struct SiiRtcInfo *rtc)
{
    internalClock.hour = rtc->hour;
    internalClock.minute = rtc->minute;
    internalClock.second = rtc->second;
}

void Platform_SetAlarm(u8 *alarmData)
{
    // TODO
}

void SoftReset(u32 resetFlags)
{
    puts("Soft Reset called. Exiting.");
    exit(0);
}

#endif
