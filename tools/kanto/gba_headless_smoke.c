/*
 * Optional headless mGBA smoke test. Does NOT touch real player saves,
 * test gameplay, or certify accurate audio/graphics. Invoked only inside
 * a clean GitHub Actions runner with disposable ROM files.
 *
 * Upstream reference: mgba/src/platform/example/client-server/server.c.
 */
#include <mgba/core/core.h>
#include <mgba/core/config.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>

static uint64_t fingerprint(const color_t *data, unsigned width, unsigned height)
{
    uint64_t hash = UINT64_C(14695981039346656037);
    unsigned y, x;
    for (y = 0; y < height; ++y) {
        for (x = 0; x < width; ++x) {
            uint32_t value = data[y * width + x];
            hash ^= value;
            hash *= UINT64_C(1099511628211);
        }
    }
    return hash;
}

static unsigned color_count_capped(const color_t *data, unsigned width, unsigned height)
{
    uint32_t seen[64];
    unsigned count = 0, x, y, i;
    for (y = 0; y < height; ++y) {
        for (x = 0; x < width; ++x) {
            uint32_t pixel = data[y * width + x];
            for (i = 0; i < count; ++i)
                if (seen[i] == pixel)
                    break;
            if (i == count && count < 64)
                seen[count++] = pixel;
            if (count == 64)
                return count;
        }
    }
    return count;
}

static int save_ppm(const char *filename, const color_t *pixels,
                    unsigned width, unsigned height)
{
    FILE *fp = fopen(filename, "wb");
    unsigned x, y;
    if (!fp) return -1;
    fprintf(fp, "P6\n%u %u\n255\n", width, height);
    for (y = 0; y < height; ++y)
        for (x = 0; x < width; ++x) {
            uint32_t p = pixels[y * width + x];
            unsigned char rgb[3] = {(unsigned char)p,
                                    (unsigned char)(p >> 8),
                                    (unsigned char)(p >> 16)};
            if (fwrite(rgb, 1, 3, fp) != 3) {
                fclose(fp);
                return -1;
            }
        }
    return fclose(fp) == 0 ? 0 : -1;
}

int main(int argc, char **argv)
{
    struct mCore *core;
    color_t *pixels;
    unsigned width = 0, height = 0, i, colors_420 = 0, colors_final = 0;
    uint64_t early = 0, gamefreak = 0, mid = 0, title = 0, after_start = 0;
    const char *rom;
    int failed = 0;
    if (argc != 2) {
        fprintf(stderr, "usage: %s ROM.gba\n", argv[0]);
        return 2;
    }
    rom = argv[1];
    core = mCoreFind(rom);
    if (!core || !core->init(core)) {
        fprintf(stderr, "Could not init mGBA core\n");
        return 3;
    }
    core->desiredVideoDimensions(core, &width, &height);
    if (width != 240 || height != 160) {
        fprintf(stderr, "Unexpected GBA frame dimensions %u x %u\n", width, height);
        core->deinit(core);
        return 4;
    }
    pixels = calloc((size_t)width * height, sizeof(color_t));
    if (!pixels) {
        core->deinit(core);
        return 5;
    }
    core->setVideoBuffer(core, pixels, width);
    if (!mCoreLoadFile(core, rom)) {
        fprintf(stderr, "mGBA rejected ROM\n");
        free(pixels);
        core->deinit(core);
        return 6;
    }
    mCoreInitConfig(core, NULL);
    mCoreLoadConfig(core);
    core->reset(core);
    // Only use a disposable, empty mGBA profile. The following deterministic
    // key presses are exploration probes, not a claim that gameplay was reached.
    // Keypresses after the title are deliberately spaced for scene transitions.
    for (i = 1; i <= 45000; ++i) {
        if (i == 3601 || i == 4501)
            core->setKeys(core, UINT32_C(1) << 3); // GBA KEY_START
        else if (i == 4901 || i == 5501 || i == 6401 || i == 7601 || i == 8501)
            core->setKeys(core, UINT32_C(1)); // GBA KEY_A
        else if (i == 3607 || i == 4507 || i == 4907 || i == 5507
              || i == 6407 || i == 7607 || i == 8507)
            core->setKeys(core, 0);
        // From frame 9700 onward probe the dialogue and character-selection
        // flow. A single short A pulse every 130 frames is deterministic
        // and never touches disk saves; it may stop at naming menus.
        else if (i > 9700 && i < 29800 && (i - 9701) % 130 == 0)
            core->setKeys(core, UINT32_C(1)); // KEY_A
        else if (i > 9700 && i < 29800 && (i - 9707) % 130 == 0)
            core->setKeys(core, 0);
        // Exercise the first-truck scene without edits to maps or save RAM.
        // Dismiss box dialogue, move right around the crate, then head down.
        // Second route (left/down) is a fallback if the first hits collision.
        else if (i == 30051 || i == 30101)
            core->setKeys(core, UINT32_C(1)); // KEY_A
        else if (i == 30057 || i == 30107)
            core->setKeys(core, 0);
        else if (i == 30301)
            core->setKeys(core, UINT32_C(1) << 4); // KEY_RIGHT
        else if (i == 30351)
            core->setKeys(core, 0);
        else if (i == 30401 || i == 31901)
            core->setKeys(core, UINT32_C(1) << 7); // KEY_DOWN
        else if (i == 30801 || i == 32201)
            core->setKeys(core, 0);
        else if (i == 31801)
            core->setKeys(core, UINT32_C(1) << 5); // KEY_LEFT
        else if (i == 31851)
            core->setKeys(core, 0);
        // Advance post-truck NPC prompts (if reached). Not an automatic
        // verification of reaching the world, or of persistent save data.
        else if (i > 33000 && i < 44700 && (i - 33001) % 160 == 0)
            core->setKeys(core, UINT32_C(1)); // KEY_A
        else if (i > 33000 && i < 44700 && (i - 33007) % 160 == 0)
            core->setKeys(core, 0);
        core->runFrame(core);
        if (i == 120) {
            early = fingerprint(pixels, width, height);
            save_ppm("gba-boot-frame-120.ppm", pixels, width, height);
        } else if (i == 420) {
            gamefreak = fingerprint(pixels, width, height);
            colors_420 = color_count_capped(pixels, width, height);
            save_ppm("gba-boot-frame-420.ppm", pixels, width, height);
        } else if (i == 1800) {
            mid = fingerprint(pixels, width, height);
            save_ppm("gba-boot-frame-1800.ppm", pixels, width, height);
        } else if (i == 3600) {
            title = fingerprint(pixels, width, height);
            save_ppm("gba-boot-frame-3600.ppm", pixels, width, height);
        } else if (i == 4200) {
            save_ppm("gba-boot-frame-4200-after-start.ppm", pixels, width, height);
        } else if (i == 4700) {
            save_ppm("gba-navigation-frame-4700.ppm", pixels, width, height);
        } else if (i == 5200) {
            save_ppm("gba-navigation-frame-5200.ppm", pixels, width, height);
        } else if (i == 6000) {
            save_ppm("gba-navigation-frame-6000.ppm", pixels, width, height);
        } else if (i == 7400) {
            save_ppm("gba-navigation-frame-7400.ppm", pixels, width, height);
        } else if (i == 9600) {
            save_ppm("gba-navigation-frame-9600.ppm", pixels, width, height);
        } else if (i == 12000) {
            save_ppm("gba-navigation-frame-12000.ppm", pixels, width, height);
        } else if (i == 16000) {
            save_ppm("gba-navigation-frame-16000.ppm", pixels, width, height);
        } else if (i == 20000) {
            save_ppm("gba-navigation-frame-20000.ppm", pixels, width, height);
        } else if (i == 25000) {
            save_ppm("gba-navigation-frame-25000.ppm", pixels, width, height);
        } else if (i == 30000) {
            save_ppm("gba-navigation-frame-30000.ppm", pixels, width, height);
        } else if (i == 30400) {
            save_ppm("gba-navigation-frame-30400.ppm", pixels, width, height);
        } else if (i == 30900) {
            save_ppm("gba-navigation-frame-30900.ppm", pixels, width, height);
        } else if (i == 32500) {
            save_ppm("gba-navigation-frame-32500.ppm", pixels, width, height);
        } else if (i == 38000) {
            save_ppm("gba-navigation-frame-38000.ppm", pixels, width, height);
        } else if (i == 45000) {
            save_ppm("gba-navigation-frame-45000.ppm", pixels, width, height);
        }
    }
    after_start = fingerprint(pixels, width, height);
    colors_final = color_count_capped(pixels, width, height);
    {
        FILE *report = fopen("gba-headless-smoke.txt", "w");
        if (report) {
            fprintf(report, "mode=MGBA_HEADLESS_FRAME_SMOKE_NOT_GAMEPLAY\n");
            fprintf(report, "frames=45000\n");
            fprintf(report, "screen=%ux%u\n", width, height);
            fprintf(report, "frame120_fnv1a=%016" PRIx64 "\n", early);
            fprintf(report, "frame420_fnv1a=%016" PRIx64 "\n", gamefreak);
            fprintf(report, "frame1800_fnv1a=%016" PRIx64 "\n", mid);
            fprintf(report, "frame3600_fnv1a=%016" PRIx64 "\n", title);
            fprintf(report, "frame_final_fnv1a=%016" PRIx64 "\n", after_start);
            fprintf(report, "frame420_unique_colors_capped_64=%u\n", colors_420);
            fprintf(report, "final_unique_colors_capped_64=%u\n", colors_final);
            fprintf(report, "start_pressed_for_six_frames=true\n");
            fprintf(report, "additional_start_and_a_probes=true\n");
            fprintf(report, "navigation_is_advisory=true\n");
            fprintf(report, "additional_dialogue_a_pulses_130_frames=true\n");
            fprintf(report, "new_game_intro_probed=true\n");
            fprintf(report, "truck_exit_direction_probe=true\n");
            fprintf(report, "player_movement_not_yet_verified=true\n");
            fprintf(report, "overworld_verified=false\n");
            fprintf(report, "title_verified=false\n");
            fprintf(report, "gameplay_verified=false\nsave_reload_verified=false\n");
            fclose(report);
        }
    }
    printf("mGBA simulated 45000 frames; colors420=%u final=%u early=%016" PRIx64
           " final=%016" PRIx64 "\n", colors_420, colors_final, early, after_start);
    if (colors_420 <= 1 || early == gamefreak || early == after_start) {
        fprintf(stderr, "No frame progression or colored game intro\n");
        failed = 1;
    }
    mCoreConfigDeinit(&core->config);
    core->deinit(core);
    free(pixels);
    return failed ? 7 : 0;
}
