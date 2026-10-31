#include <Arduino.h>
// MicroDuck touch readout on the Seeed XIAO ESP32-S3 (D-013, ../../PLAN.md).
// Reads the five copper pads with the ESP32-S3 touch peripheral at 50 Hz and serves them two ways:
//   USB serial, 115200: one line per sample, "T,<ms>,<L1>,<R1>,<L2>,<R2>,<M>" (raw counts; on the S3 a touch raises them).
//   I2C slave 0x2A on D4 (SDA) / D5 (SCL): a 24-byte block, uint32 LE sequence number then the five uint32 LE counts.
// Pads: L1 D0 (GPIO1, T1), R1 D1 (GPIO2, T2), L2 D2 (GPIO3, T3), R2 D3 (GPIO4, T4), M D8 (GPIO7, T7).
//
// Self-recovery (2026-10-31: the slave wedged three times in two days, acking its address and then stalling every
// read until the duck was powered off; the XIAO has no reset or USB line to the A7Z, so it must heal itself). The core's
// slave keeps unsent bytes in its TX FIFO when a read is cut short, and the next read then runs dry mid-block and
// stretches SCL for good. Restarting only the slave (Wire.end/begin) is unsafe in esp32 3.3.12: end() frees the buffers
// even when the slave deinit fails and leaves is_slave set, so begin() returns at once and the slave never acks again
// (seen 2026-10-31 18:43), and the deinit can wait on a lock the slave task holds (the task watchdog fired). So:
//   - once the bus has been idle (both lines high) since boot, a line held low for STUCK_MS restarts the whole XIAO;
//     a powered-off or booting A7Z holds both lines low from the start, which never counts;
//   - the A7Z can write "RS" to 0x2A to restart the XIAO, and "RD" to switch the line watchdog off for RD_MS (the
//     induced-wedge test uses it to see the wedge itself, then the recovery once the window ends);
//   - the task watchdog restarts the XIAO if the loop stops (a pad shorted to metal can block touchRead);
//   - USB serial says once a second why the XIAO last started and how many line-watchdog restarts it has made.

#include <Wire.h>
#include <esp_task_wdt.h>
#include <driver/gpio.h>
#include <esp_attr.h>

static const uint8_t PAD_PINS[5] = {1, 2, 3, 4, 7};
static const uint8_t I2C_ADDR = 0x2A;
static const uint32_t PERIOD_MS = 20;
static const uint32_t STUCK_MS = 30;     // the A7Z master never holds a line this long; its transfer is 2.2 ms
static const uint32_t STUCK_SAMPLES = 50;
static const uint32_t RD_MS = 20000;
static const uint32_t WDT_S = 3;
static const uint32_t MAGIC = 0x7a51c0de;

static volatile uint32_t block[6];       // seq, L1, R1, L2, R2, M
static portMUX_TYPE block_mux = portMUX_INITIALIZER_UNLOCKED;
static volatile bool restart_asked = false, recovery_off_asked = false;
RTC_NOINIT_ATTR static uint32_t rtc_magic, rtc_line_restarts;  // survive esp_restart, cleared on power-up

static void onRequest() {
  uint8_t out[24];
  portENTER_CRITICAL(&block_mux);
  for (int i = 0; i < 6; i++) {
    uint32_t v = block[i];
    out[4 * i] = v & 0xFF;
    out[4 * i + 1] = (v >> 8) & 0xFF;
    out[4 * i + 2] = (v >> 16) & 0xFF;
    out[4 * i + 3] = (v >> 24) & 0xFF;
  }
  portEXIT_CRITICAL(&block_mux);
  Wire.write(out, sizeof(out));
}

static void onReceive(int n) {
  uint8_t a = n > 0 ? Wire.read() : 0, b = n > 1 ? Wire.read() : 0;
  while (Wire.available()) Wire.read();
  if (a == 'R' && b == 'S') restart_asked = true;
  if (a == 'R' && b == 'D') recovery_off_asked = true;
}

void setup() {
  Serial.begin(115200);
  if (rtc_magic != MAGIC) {
    rtc_magic = MAGIC;
    rtc_line_restarts = 0;
  }
  esp_task_wdt_config_t wdt = {.timeout_ms = WDT_S * 1000, .idle_core_mask = 0, .trigger_panic = true};
  if (esp_task_wdt_reconfigure(&wdt) != ESP_OK) esp_task_wdt_init(&wdt);
  esp_task_wdt_add(NULL);
  Wire.onRequest(onRequest);
  Wire.onReceive(onReceive);
  Wire.begin(I2C_ADDR, D4, D5, 100000);   // slave: address, SDA, SCL, clock; the core's slave init enables the internal pull-ups
}

void loop() {
  static uint32_t next = 0, seq = 0, next_note = 0, stuck_since = 0, stuck_samples = 0, recovery_off_until = 0;
  static bool bus_seen_idle = false;
  uint32_t now = millis();
  esp_task_wdt_reset();

  if (restart_asked) {
    Serial.println("R,restart asked over I2C");
    Serial.flush();
    ESP.restart();
  }
  if (recovery_off_asked) {
    recovery_off_asked = false;
    recovery_off_until = now + RD_MS;
  }
  bool idle = gpio_get_level((gpio_num_t)D5) && gpio_get_level((gpio_num_t)D4);  // a byte holds a line low for us only
  if (idle) {
    bus_seen_idle = true;
    stuck_since = stuck_samples = 0;
  } else {
    if (!stuck_since) stuck_since = now ? now : 1;
    stuck_samples++;
  }
  bool recovery_on = recovery_off_until == 0 || (int32_t)(now - recovery_off_until) >= 0;
  // both a span and a count: a sample just before a long touchRead and one just after can both land inside transfers
  if (recovery_on && bus_seen_idle && stuck_since && now - stuck_since > STUCK_MS && stuck_samples >= STUCK_SAMPLES) {
    rtc_line_restarts++;
    Serial.printf("R,line held low %lu ms: restarting\n", (unsigned long)(now - stuck_since));
    Serial.flush();
    ESP.restart();
  }
  if ((int32_t)(now - next_note) >= 0) {
    next_note = now + 1000;
    Serial.printf("R,reset_reason=%d,line_restarts=%lu,bus_seen_idle=%d,recovery=%d\n", (int)esp_reset_reason(),
                  (unsigned long)rtc_line_restarts, (int)bus_seen_idle, (int)recovery_on);
  }
  if ((int32_t)(now - next) < 0) return;
  next = now + PERIOD_MS;

  uint32_t v[5];
  for (int i = 0; i < 5; i++) v[i] = touchRead(PAD_PINS[i]);

  portENTER_CRITICAL(&block_mux);
  block[0] = ++seq;
  for (int i = 0; i < 5; i++) block[i + 1] = v[i];
  portEXIT_CRITICAL(&block_mux);

  Serial.printf("T,%lu,%lu,%lu,%lu,%lu,%lu\n", (unsigned long)now, (unsigned long)v[0], (unsigned long)v[1],
                (unsigned long)v[2], (unsigned long)v[3], (unsigned long)v[4]);
}
