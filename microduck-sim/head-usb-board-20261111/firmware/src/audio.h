// I2S side of the head USB board: PIO state machines, DMA rings, and the frame hand-over to and from USB.
// Original work for this project (BSD-3-Clause, see ../README.md, Licences).
#ifndef AUDIO_H
#define AUDIO_H

#include <stdbool.h>
#include <stdint.h>

#include "audio_convert.h"

// clk_sys that makes the I2S clocks exact: 12 MHz x 128 = 1536 MHz VCO, / 5 / 5 = 61.44 MHz;
// PIO divider 10 -> 6.144 MHz, two PIO cycles per bit clock -> 3.072 MHz = 64 x 48 kHz.
#define AUDIO_SYS_CLOCK_HZ 61440000u
#define AUDIO_PLL_VCO_HZ 1536000000u
#define AUDIO_PLL_POSTDIV1 5
#define AUDIO_PLL_POSTDIV2 5
#define AUDIO_PIO_CLKDIV 10
#define AUDIO_PIO_CYCLES_PER_BIT 2
#define AUDIO_BITS_PER_FRAME 64

typedef struct {
    uint32_t mic_frames;        // frames handed to USB
    uint32_t mic_resyncs;       // times the capture reader fell behind and jumped to the newest audio
    uint32_t spk_frames;        // frames taken from USB
    uint32_t spk_underruns;     // times the amplifier ran out of USB audio in the middle of a stream
    uint32_t spk_dropped;       // single frames dropped because the host clock runs fast against ours
    uint32_t spk_repeated;      // single frames repeated because the host clock runs slow against ours
    uint16_t mic_peak[3];       // largest |sample| per microphone since the last audio_take_peaks(); runs with or
                                // without a USB capture stream (the microphones are always being recorded)
} audio_stats_t;

extern volatile audio_stats_t audio_stats;

void audio_init(void);                                            // claims PIO0 and four DMA channels, starts the clocks
void audio_task(void);                                            // every main-loop pass: keeps silence ahead of the amplifier
void audio_mic_restart(void);                                     // capture stream opened: start from the newest audio
uint32_t audio_mic_read(int16_t *out, uint32_t max_frames);       // interleaved 4-channel frames; returns frames written
void audio_spk_write(const int16_t *in, uint32_t frames);         // interleaved stereo frames from USB
void audio_set_mic_gain_shift(unsigned shift);                    // 0..8, see audio_convert.h
unsigned audio_get_mic_gain_shift(void);
void audio_scan_peaks(void);                                      // core 1: update the level meter from the microphone ring
void audio_take_peaks(uint16_t peaks[3]);                         // read and clear the microphone peaks

#endif
