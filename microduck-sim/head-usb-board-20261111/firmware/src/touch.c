// Touch board bridge, core 1. Original work for this project (BSD-3-Clause, see ../README.md, Licences).
//
// I2C reads block for up to a few milliseconds, and a jammed touch bus (FAULTS.json touch-twi0-jam) can hold them to
// their timeout, so they run on core 1 where they cannot delay the USB audio packets that core 0 serves every
// millisecond. Core 1 also owns the debug UART (a printf there blocks for milliseconds too).

#include "touch.h"

#include <stdio.h>
#include <string.h>

#include "audio.h"
#include "hardware/gpio.h"
#include "hardware/i2c.h"
#include "pico/stdlib.h"
#include "pico/util/queue.h"

#define TOUCH_I2C i2c0
#define TOUCH_BAUD 100000              // the XIAO's Wire slave was brought up for 100 kHz
#define TOUCH_READ_TIMEOUT_US 8000     // a 24-byte read takes 2.5 ms at 100 kHz
#define TOUCH_WRITE_TIMEOUT_US 4000
#define TOUCH_REINIT_AFTER_FAILS 5
#define STATS_PERIOD_US 5000000

typedef struct {
    char bytes[2];
} touch_command_t;

static queue_t line_queue;      // core 1 -> core 0
static queue_t command_queue;   // core 0 -> core 1

void touch_init(void) {
    queue_init(&line_queue, sizeof(touch_line_t), 16);
    queue_init(&command_queue, sizeof(touch_command_t), 4);
}

bool touch_take_line(touch_line_t *line) {
    return queue_try_remove(&line_queue, line);
}

bool touch_send_command(char a, char b) {
    touch_command_t c = {{a, b}};
    return queue_try_add(&command_queue, &c);
}

static void post(const char *text) {
    touch_line_t line;
    strncpy(line.text, text, sizeof(line.text) - 1);
    line.text[sizeof(line.text) - 1] = 0;
    queue_try_add(&line_queue, &line);   // a full queue (nobody reading the port) drops the line
}

static void bus_init(void) {
    i2c_init(TOUCH_I2C, TOUCH_BAUD);
    gpio_set_function(PICO_DEFAULT_I2C_SDA_PIN, GPIO_FUNC_I2C);
    gpio_set_function(PICO_DEFAULT_I2C_SCL_PIN, GPIO_FUNC_I2C);
    gpio_pull_up(PICO_DEFAULT_I2C_SDA_PIN);   // the board carries 2.2 k pull-ups (R10, R11); these only add to them
    gpio_pull_up(PICO_DEFAULT_I2C_SCL_PIN);
}

static const char *reason(int result) {
    if (result == PICO_ERROR_TIMEOUT) return "E timeout";
    if (result == PICO_ERROR_GENERIC) return "E nack";
    return "E short";
}

void touch_core1_main(void) {
    bus_init();
    printf("touch: polling 0x%02X every %d ms\n", TOUCH_I2C_ADDR, TOUCH_PERIOD_US / 1000);

    absolute_time_t next_poll = make_timeout_time_us(TOUCH_PERIOD_US);
    absolute_time_t next_stats = make_timeout_time_us(STATS_PERIOD_US);
    uint32_t ok = 0, failed = 0, fails_in_row = 0;
    char text[TOUCH_LINE_MAX];

    for (;;) {
        touch_command_t cmd;
        while (queue_try_remove(&command_queue, &cmd)) {
            int r = i2c_write_timeout_us(TOUCH_I2C, TOUCH_I2C_ADDR, (const uint8_t *)cmd.bytes, 2, false,
                                         TOUCH_WRITE_TIMEOUT_US);
            snprintf(text, sizeof(text), "# %c%c %s", cmd.bytes[0], cmd.bytes[1], r == 2 ? "sent" : "failed");
            post(text);
        }

        uint8_t block[TOUCH_BLOCK_BYTES];
        int r = i2c_read_timeout_us(TOUCH_I2C, TOUCH_I2C_ADDR, block, sizeof(block), false, TOUCH_READ_TIMEOUT_US);
        if (r == TOUCH_BLOCK_BYTES) {
            touch_format_block(block, text);
            post(text);
            ok++;
            fails_in_row = 0;
        } else {
            post(reason(r));
            failed++;
            if (++fails_in_row % TOUCH_REINIT_AFTER_FAILS == 0) {
                i2c_deinit(TOUCH_I2C);   // clear a controller left mid-transfer by a timeout
                bus_init();
            }
        }

        audio_scan_peaks();   // the 20 ms since the last poll are 960 frames; the ring holds 1024

        if (absolute_time_diff_us(next_stats, get_absolute_time()) >= 0) {
            next_stats = make_timeout_time_us(STATS_PERIOD_US);
            printf("touch ok %lu fail %lu | mic frames %lu resync %lu | spk frames %lu underrun %lu drop %lu repeat %lu\n",
                   (unsigned long)ok, (unsigned long)failed,
                   (unsigned long)audio_stats.mic_frames, (unsigned long)audio_stats.mic_resyncs,
                   (unsigned long)audio_stats.spk_frames, (unsigned long)audio_stats.spk_underruns,
                   (unsigned long)audio_stats.spk_dropped, (unsigned long)audio_stats.spk_repeated);
        }

        sleep_until(next_poll);
        next_poll = delayed_by_us(next_poll, TOUCH_PERIOD_US);
        if (absolute_time_diff_us(next_poll, get_absolute_time()) > 0) {
            next_poll = make_timeout_time_us(TOUCH_PERIOD_US);   // fell behind (timeouts): do not burst to catch up
        }
    }
}
