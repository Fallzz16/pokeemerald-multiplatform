#ifndef EMERALD_SAVE_PROFILES_H
#define EMERALD_SAVE_PROFILES_H
/* Portable, standalone local save-profile core. Does NOT parse Trainer data,
 * change GBA save bytes or integrate with the running game yet. */
#include <stddef.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <sys/types.h>
#endif

#define SP_PATH_CAP 4096
#define SP_ID_CAP 49
#define SP_EMERALD_SIZE 131072u
#define SP_EMULATOR_EXTRA_SIZE 16u

typedef enum {
    SP_OK=0, SP_BAD_ARG=-1, SP_IO=-2, SP_EXISTS=-3,
    SP_BAD_SAVE=-4, SP_BUSY=-5, SP_NOT_FOUND=-6
} SpStatus;

typedef struct {
    char directory[SP_PATH_CAP];
#ifdef _WIN32
    HANDLE handle;
#else
    int fd;
#endif
    int held;
} SpProfileLock;

int sp_valid_id(const char *id);
/* Checks structural sector identifiers/signatures; this is NOT an exhaustive
 * game-data/checksum validation. Source files are never changed. */
SpStatus sp_validate_file(const char *source);
/* root must already exist. Profile directory is created exclusively. */
SpStatus sp_import(const char *root, const char *id, const char *source);
/* Creates 128 KiB of erased flash (0xFF): game starts its normal New Game. */
SpStatus sp_create_empty(const char *root, const char *id);
/* Exclusive advisory/Win32 profile lock; all managed instances MUST use it. */
SpStatus sp_lock(const char *root, const char *id, SpProfileLock *lock);
void sp_unlock(SpProfileLock *lock);
/* Require exclusive lock. Call ONLY when the game is not writing the file. */
SpStatus sp_backup(const SpProfileLock *lock, unsigned *sequence);
SpStatus sp_restore(const SpProfileLock *lock, unsigned sequence);
/* Keep latest 'keep' backups by sequence, allow 1..1000. */
SpStatus sp_prune(const SpProfileLock *lock, unsigned keep);
#endif
