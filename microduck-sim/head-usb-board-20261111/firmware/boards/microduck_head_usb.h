// Board definition for the MicroDuck head USB board (pin map: ../../sch/netlist.py).
// Original work for this project (BSD-3-Clause, see ../README.md, Licences).

// pico_cmake_set PICO_PLATFORM=rp2040

#ifndef _BOARDS_MICRODUCK_HEAD_USB_H
#define _BOARDS_MICRODUCK_HEAD_USB_H

// For board detection
#define MICRODUCK_HEAD_USB

// --- debug UART: TX only, on test pad TP6 ---
#define PICO_DEFAULT_UART 0
#define PICO_DEFAULT_UART_TX_PIN 0

// --- LED D1 ---
#define PICO_DEFAULT_LED_PIN 25

// --- touch board (XIAO ESP32-S3, I2C slave 0x2A) ---
#define PICO_DEFAULT_I2C 0
#define PICO_DEFAULT_I2C_SDA_PIN 4
#define PICO_DEFAULT_I2C_SCL_PIN 5

// --- microphones (INMP441 x3) and amplifier (MAX98357A) ---
#define HEAD_MIC_SCK_PIN 10
#define HEAD_MIC_WS_PIN 11
#define HEAD_MIC_SD_EARS_PIN 12
#define HEAD_MIC_SD_BACK_PIN 13
#define HEAD_SPK_BCLK_PIN 18
#define HEAD_SPK_LRC_PIN 19
#define HEAD_SPK_DIN_PIN 20

// --- flash: W25Q16JV, 2 MB, on the Raspberry Pi minimal-design circuit ---
// Second-stage boot: boot2_w25q080 (the SDK's stage for the Winbond W25Q family, the one the Pico's W25Q16JV uses).
#define PICO_BOOT_STAGE2_CHOOSE_W25Q080 1
#ifndef PICO_FLASH_SPI_CLKDIV
#define PICO_FLASH_SPI_CLKDIV 2
#endif
// pico_cmake_set_default PICO_FLASH_SIZE_BYTES = (2 * 1024 * 1024)
#ifndef PICO_FLASH_SIZE_BYTES
#define PICO_FLASH_SIZE_BYTES (2 * 1024 * 1024)
#endif

// --- crystal: 12 MHz YXC X322512MMB4SI (LCSC C50430), 10 pF load, 80 ohm maximum ESR. The Raspberry Pi circuit
// (15 pF + 15 pF, 1 k series resistor R5) is tuned for the ABM8-272-T3 at 50 ohm, so this crystal may start more
// slowly. 64 x the default start-up wait (about 1 ms -> about 64 ms) is the SDK's setting for slow-starting
// crystals. If the oscillator does not start at all on the bench, lower R5 from 1 k (README, known risks). ---
#ifndef PICO_XOSC_STARTUP_DELAY_MULTIPLIER
#define PICO_XOSC_STARTUP_DELAY_MULTIPLIER 64
#endif

#ifndef PICO_RP2040_B0_SUPPORTED
#define PICO_RP2040_B0_SUPPORTED 0
#endif

#endif
