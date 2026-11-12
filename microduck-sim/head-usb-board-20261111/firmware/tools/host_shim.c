// Host-side wrapper so tools/test_pio.py can call the firmware's own conversion and formatting code through ctypes.
// Compiled with the host C compiler by the test; not part of the firmware image.
#include "audio_convert.h"
#include "touch.h"

void shim_mic_frame_to_usb(const uint32_t *words, int16_t *out, unsigned gain_shift) {
    audio_mic_frame_to_usb(words, out, gain_shift);
}

void shim_usb_frame_to_spk(const int16_t *in, uint32_t *words) {
    audio_usb_frame_to_spk(in, words);
}

void shim_touch_format_block(const uint8_t *block, char *out) {
    touch_format_block(block, out);
}
