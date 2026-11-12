// MicroDuck head USB board firmware: USB Audio Class 2 sound card (3 microphones in, amplifier out) plus a CDC
// serial port that carries the touch board's readings. Original work for this project (BSD-3-Clause, see
// ../README.md, Licences). Untested on hardware as of 2026-11-12.
//
// Core 0: USB (TinyUSB device task), audio rings, CDC port, LED.
// Core 1: touch I2C polling and the debug UART (touch.c).

#include <stdio.h>
#include <string.h>

#include "hardware/clocks.h"
#include "hardware/gpio.h"
#include "pico/multicore.h"
#include "pico/stdlib.h"
#include "tusb.h"

#include "audio.h"
#include "touch.h"

#define FIRMWARE_VERSION "0.1.0"

static void led_task(void) {
    static absolute_time_t next;
    static bool on;
    if (absolute_time_diff_us(next, get_absolute_time()) < 0) return;
    // slow blink: configured by a USB host; fast blink: running but no host
    next = make_timeout_time_ms(tud_mounted() ? 500 : 100);
    on = !on;
    gpio_put(PICO_DEFAULT_LED_PIN, on);
}

static void cdc_write_line(const char *text) {
    size_t len = strlen(text);
    if (!tud_cdc_connected()) return;                        // nobody has the port open
    if (tud_cdc_write_available() < len + 1) return;         // reader is not keeping up: drop, never block
    tud_cdc_write(text, len);
    tud_cdc_write_char('\n');
}

static void cdc_status_line(void) {
    char text[160];
    uint16_t peaks[3];
    audio_take_peaks(peaks);
    snprintf(text, sizeof(text),
             "S version=" FIRMWARE_VERSION " mic=%lu resync=%lu spk=%lu underrun=%lu drop=%lu repeat=%lu peak=%u,%u,%u gain=%u",
             (unsigned long)audio_stats.mic_frames, (unsigned long)audio_stats.mic_resyncs,
             (unsigned long)audio_stats.spk_frames, (unsigned long)audio_stats.spk_underruns,
             (unsigned long)audio_stats.spk_dropped, (unsigned long)audio_stats.spk_repeated,
             peaks[0], peaks[1], peaks[2], audio_get_mic_gain_shift());
    cdc_write_line(text);
}

// Host commands, one per line: RS RD HD HC go to the XIAO as two bytes (what the A7Z wrote to 0x2A before);
// "?" asks for a status line; "G0".."G8" sets the microphone gain shift.
static void cdc_command(const char *cmd) {
    if (strcmp(cmd, "?") == 0) {
        cdc_status_line();
    } else if (cmd[0] == 'G' && cmd[1] >= '0' && cmd[1] <= '8' && cmd[2] == 0) {
        audio_set_mic_gain_shift((unsigned)(cmd[1] - '0'));
        cdc_status_line();
    } else if (strcmp(cmd, "RS") == 0 || strcmp(cmd, "RD") == 0 || strcmp(cmd, "HD") == 0 || strcmp(cmd, "HC") == 0) {
        if (!touch_send_command(cmd[0], cmd[1])) cdc_write_line("# busy");
    } else if (cmd[0] != 0) {
        cdc_write_line("# unknown command");
    }
}

static void cdc_task(void) {
    static char cmd[8];
    static size_t cmd_len;
    static bool cmd_overflow;

    touch_line_t line;
    bool wrote = false;
    while (touch_take_line(&line)) {
        cdc_write_line(line.text);
        wrote = true;
    }

    while (tud_cdc_available()) {
        int32_t ch = tud_cdc_read_char();
        if (ch < 0) break;
        if (ch == '\n' || ch == '\r') {
            cmd[cmd_len] = 0;
            if (!cmd_overflow) cdc_command(cmd);
            cmd_len = 0;
            cmd_overflow = false;
            wrote = true;
        } else if (cmd_len < sizeof(cmd) - 1) {
            cmd[cmd_len++] = (char)ch;
        } else {
            cmd_overflow = true;
        }
    }
    if (wrote) tud_cdc_write_flush();
}

int main(void) {
    // 61.44 MHz makes both I2S bit clocks an exact integer division (audio.h).
    set_sys_clock_pll(AUDIO_PLL_VCO_HZ, AUDIO_PLL_POSTDIV1, AUDIO_PLL_POSTDIV2);

    stdio_uart_init_full(uart0, 115200, PICO_DEFAULT_UART_TX_PIN, -1);   // TX only, test pad TP6
    printf("\nmicroduck head usb %s, clk_sys %lu Hz\n", FIRMWARE_VERSION, (unsigned long)clock_get_hz(clk_sys));

    gpio_init(PICO_DEFAULT_LED_PIN);
    gpio_set_dir(PICO_DEFAULT_LED_PIN, GPIO_OUT);

    if (clock_get_hz(clk_sys) != AUDIO_SYS_CLOCK_HZ) {
        // Wrong audio clock would mean wrong pitch and out-of-range I2S clocks: stop here, LED on solid.
        gpio_put(PICO_DEFAULT_LED_PIN, 1);
        panic("clk_sys is not %u Hz", AUDIO_SYS_CLOCK_HZ);
    }

    audio_init();
    touch_init();
    multicore_launch_core1(touch_core1_main);
    tud_init(BOARD_TUD_RHPORT);

    for (;;) {
        tud_task();
        audio_task();
        cdc_task();
        led_task();
    }
}
