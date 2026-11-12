// Touch board bridge: core 1 polls the XIAO ESP32-S3 (I2C slave 0x2A) and hands text lines to core 0 for the CDC port.
// Original work for this project (BSD-3-Clause, see ../README.md, Licences).
#ifndef TOUCH_H
#define TOUCH_H

#include <stdbool.h>
#include <stdint.h>

#define TOUCH_I2C_ADDR 0x2A
#define TOUCH_BLOCK_BYTES 24          // uint32 LE sequence number, then L1, R1, L2, R2, M (touch_main.cpp)
#define TOUCH_PERIOD_US 20000         // the XIAO scans every 20 ms; the A7Z reader polled at the same rate
#define TOUCH_LINE_MAX 64

typedef struct {
    char text[TOUCH_LINE_MAX];        // one line, no line ending
} touch_line_t;

void touch_init(void);                          // creates the queues; call before starting core 1
void touch_core1_main(void);                    // entry for multicore_launch_core1; never returns
bool touch_take_line(touch_line_t *line);       // core 0: next line for the CDC port, false if none
bool touch_send_command(char a, char b);        // core 0: queue a two-byte write to the XIAO ("RS", "RD", "HD", "HC")

// Formats the line for one poll. Pure function, also compiled by the host-side test.
//   ok:    "T " + 48 lower-case hex digits (the 24 bytes exactly as read, so the host keeps its alignment check)
//   fail:  "E " + reason
void touch_format_block(const uint8_t block[TOUCH_BLOCK_BYTES], char out[TOUCH_LINE_MAX]);

#endif
