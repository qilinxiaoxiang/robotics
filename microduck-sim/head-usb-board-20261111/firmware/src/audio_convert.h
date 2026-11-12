// Sample conversion between the PIO word layout and USB PCM. Pure C with no SDK dependency, so the host-side test
// (tools/test_pio.py) compiles this same file and runs it on the words the PIO programs produce.
// Original work for this project (BSD-3-Clause, see ../README.md, Licences).
#ifndef AUDIO_CONVERT_H
#define AUDIO_CONVERT_H

#include <stdint.h>

#define MIC_WORDS_PER_FRAME 4  // i2s_mic.pio: left high, left low, right high, right low
#define MIC_USB_CHANNELS 4     // ch0 left ear, ch1 right ear, ch2 back microphone, ch3 silence
#define SPK_WORDS_PER_FRAME 2  // i2s_spk.pio: left slot word, right slot word
#define SPK_USB_CHANNELS 2

// Gather the even bits of x (bit 30 -> bit 15 ... bit 0 -> bit 0).
static inline uint32_t audio_even_bits(uint32_t x) {
    x &= 0x55555555u;
    x = (x | (x >> 1)) & 0x33333333u;
    x = (x | (x >> 2)) & 0x0F0F0F0Fu;
    x = (x | (x >> 4)) & 0x00FF00FFu;
    x = (x | (x >> 8)) & 0x0000FFFFu;
    return x;
}

// 24-bit microphone sample of one data line from the two words of a slot. line 0 = ears (even bits), 1 = back.
static inline int32_t audio_mic_sample24(uint32_t word_hi, uint32_t word_lo, unsigned line) {
    uint32_t hi = audio_even_bits(word_hi >> line);        // sample bits 23..8
    uint32_t lo = audio_even_bits(word_lo >> line) >> 8;   // sample bits 7..0 (first 8 periods of the low word)
    uint32_t s = (hi << 8) | lo;
    return (int32_t)(s << 8) >> 8;                         // sign-extend from bit 23
}

// 24-bit sample to signed 16-bit. gain_shift 0 keeps the top 16 bits (what S32_LE >> 16 gave on the A7Z);
// gain_shift n (1..8) multiplies by 2^n first and saturates.
static inline int16_t audio_s24_to_s16(int32_t s24, unsigned gain_shift) {
    int32_t v = s24 >> (8u - gain_shift);
    if (v > 32767) v = 32767;
    if (v < -32768) v = -32768;
    return (int16_t)v;
}

// One microphone frame (4 PIO words) to 4 USB channels.
static inline void audio_mic_frame_to_usb(const uint32_t *w, int16_t *out, unsigned gain_shift) {
    out[0] = audio_s24_to_s16(audio_mic_sample24(w[0], w[1], 0), gain_shift);  // ears line, left slot
    out[1] = audio_s24_to_s16(audio_mic_sample24(w[2], w[3], 0), gain_shift);  // ears line, right slot
    out[2] = audio_s24_to_s16(audio_mic_sample24(w[0], w[1], 1), gain_shift);  // back line, left slot
    out[3] = 0;                                                                // back line, right slot: no microphone
}

// One USB playback frame (left, right) to the two PIO slot words.
static inline void audio_usb_frame_to_spk(const int16_t *in, uint32_t *w) {
    w[0] = (uint32_t)(uint16_t)in[0] << 16;
    w[1] = (uint32_t)(uint16_t)in[1] << 16;
}

#endif
