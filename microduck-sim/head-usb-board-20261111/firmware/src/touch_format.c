// Touch line formatting, free of SDK dependencies so tools/test_pio.py can compile it on the host.
// Original work for this project (BSD-3-Clause, see ../README.md, Licences).
#include "touch.h"

void touch_format_block(const uint8_t block[TOUCH_BLOCK_BYTES], char out[TOUCH_LINE_MAX]) {
    static const char hex[] = "0123456789abcdef";
    char *p = out;
    *p++ = 'T';
    *p++ = ' ';
    for (int i = 0; i < TOUCH_BLOCK_BYTES; i++) {
        *p++ = hex[block[i] >> 4];
        *p++ = hex[block[i] & 15];
    }
    *p = 0;
}
