/* Compare exact byte encodings across ARM APCS (GBA) and host GCC32.
 * Mirrors the two small World types whose sizeof differs between ABIs.
 * Never reads or writes a real Pokémon save.
 */
#include <stdint.h>
typedef int16_t s16;
typedef int8_t s8;
typedef uint16_t u16;

struct Time
{
    s16 days;
    s8 hours;
    s8 minutes;
    s8 seconds;
}
#ifdef PORTABLE
__attribute__((aligned(4)))
#endif
;

struct BattleDomeTrainer
{
    u16 trainerId:10;
    u16 isEliminated:1;
    u16 eliminatedAt:2;
    u16 forfeited:3;
}
#ifdef PORTABLE
__attribute__((aligned(4)))
#endif
;

_Static_assert(sizeof(struct Time) == 8, "Time ABI requires 8 bytes");
_Static_assert(sizeof(struct BattleDomeTrainer) == 4, "Dome ABI requires 4 bytes");

const struct Time gw_test_times[3]
    __attribute__((used, section(".gw_times"))) = {
        {0, 0, 0, 0},
        {-120, 23, 59, 59},
        {32000, 12, 30, 45},
    };

const struct BattleDomeTrainer gw_test_dome[5]
    __attribute__((used, section(".gw_dome"))) = {
        {0, 0, 0, 0},
        {1, 1, 1, 1},
        {1023, 1, 3, 7},
        {512, 0, 2, 6},
        {37, 1, 0, 4},
    };
