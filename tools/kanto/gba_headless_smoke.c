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
    // Begin with a clean disposable emulator (never load a user's save).
    // Simulate Start once near the end, but never assert menu/gameplay.
    // The real screen contents must be inspected separately.
    for (i = 1; i <= 4200; ++i) {
        if (i == 3601)
            core->setKeys(core, UINT32_C(1) << 3); // GBA KEY_START
        if (i == 3607)
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
        }
    }
    after_start = fingerprint(pixels, width, height);
    colors_final = color_count_capped(pixels, width, height);
    save_ppm("gba-boot-frame-4200-after-start.ppm", pixels, width, height);
    {
        FILE *report = fopen("gba-headless-smoke.txt", "w");
        if (report) {
            fprintf(report, "mode=MGBA_HEADLESS_FRAME_SMOKE_NOT_GAMEPLAY\n");
            fprintf(report, "frames=4200\n");
            fprintf(report, "screen=%ux%u\n", width, height);
            fprintf(report, "frame120_fnv1a=%016" PRIx64 "\n", early);
            fprintf(report, "frame420_fnv1a=%016" PRIx64 "\n", gamefreak);
            fprintf(report, "frame1800_fnv1a=%016" PRIx64 "\n", mid);
            fprintf(report, "frame3600_fnv1a=%016" PRIx64 "\n", title);
            fprintf(report, "frame4200_after_start_fnv1a=%016" PRIx64 "\n", after_start);
            fprintf(report, "frame420_unique_colors_capped_64=%u\n", colors_420);
            fprintf(report, "final_unique_colors_capped_64=%u\n", colors_final);
            fprintf(report, "start_pressed_for_six_frames=true\n");
            fprintf(report, "title_verified=false\n");
            fprintf(report, "gameplay_verified=false\nsave_reload_verified=false\n");
            fclose(report);
        }
    }
    printf("mGBA simulated 4200 frames; colors420=%u final=%u early=%016" PRIx64
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
