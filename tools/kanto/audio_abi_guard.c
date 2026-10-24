/*
 * M8 legacy audio ABI guard. Compile this for ARM EABI with both MODERN=0/1.
 * No ROM assets, linker changes, or runtime effects.
 * Abort if C89-compatible audio headers silently change GBA field offsets.
 */
#include <stddef.h>
#include "sound_mixer.h"
#include "music_player.h"
#include "cgb_audio.h"

#define ABI_ASSERT(name, check) typedef char abi_##name[(check) ? 1 : -1]
ABI_ASSERT(arm_pointer_32_bit, sizeof(void *) == 4);
ABI_ASSERT(mixer_source_padding_38, offsetof(struct MixerSource, padding7) == 0x38);
ABI_ASSERT(mixer_source_blockcount_3c, offsetof(struct MixerSource, blockCount) == 0x3C);
ABI_ASSERT(mixer_source_size_64, sizeof(struct MixerSource) == 0x40);
ABI_ASSERT(instrument_size_twelve_bytes, sizeof(struct MP2KInstrument) == 12);
ABI_ASSERT(instrument_wave_at_four, offsetof(struct MP2KInstrument, wav) == 4);
ABI_ASSERT(wave_data_sample_offset_sixteen, offsetof(struct WaveData2, data) == 16);
ABI_ASSERT(cgb_output_alignment,
           offsetof(struct AudioCGB, outBuffer) % 4 == 0);
ABI_ASSERT(mixer_output_alignment,
           offsetof(struct SoundMixerState, outBuffer) % 4 == 0);
