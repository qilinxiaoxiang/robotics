#include <Arduino.h>
// MicroDuck touch readout on the Seeed XIAO ESP32-S3 (D-013, ../../PLAN.md).
// Reads the five copper pads with the ESP32-S3 touch peripheral at 50 Hz and serves them two ways:
//   USB serial, 115200: one line per sample, "T,<ms>,<L1>,<R1>,<L2>,<R2>,<M>" (raw counts; on the S3 a touch raises them).
//   I2C slave 0x2A on D4 (SDA) / D5 (SCL): a 24-byte block, uint32 LE sequence number then the five uint32 LE counts.
// Pads: L1 D0 (GPIO1, T1), R1 D1 (GPIO2, T2), L2 D2 (GPIO3, T3), R2 D3 (GPIO4, T4), M D8 (GPIO7, T7).
//
// Self-recovery (2026-10-31: the slave wedged three times in two days, acking its address and then stalling every
// read until the duck was powered off; the XIAO has no reset or USB line to the A7Z, so it must heal itself):
//   - a line held low (SCL, or SDA while SCL is high) for STUCK_MS restarts the I2C slave;
//   - the A7Z can write the two bytes "RS" to 0x2A to restart the whole XIAO;
//   - the task watchdog restarts the XIAO if the loop stops (a pad shorted to metal can block touchRead);
//   - the reason for the last start rides on USB serial as "R,<reason>" once a second.

#include <Wire.h>
#include <esp_task_wdt.h>
#include <driver/gpio.h>

static const uint8_t PAD_PINS[5] = {1, 2, 3, 4, 7};
static const uint8_t I2C_ADDR = 0x2A;
static const uint32_t PERIOD_MS = 20;
static const uint32_t STUCK_MS = 30;     // the A7Z master never holds a line this long; its transfer is 2.2 ms
static const uint32_t RESTART_GAP_MS = 1000;  // a powered-off A7Z holds both lines low: restart at most once a second
static const uint32_t WDT_S = 3;

static volatile uint32_t block[6];       // seq, L1, R1, L2, R2, M
static portMUX_TYPE block_mux = portMUX_INITIALIZER_UNLOCKED;
static volatile bool restart_asked = false;
static uint32_t slave_restarts = 0;

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
}

static void startSlave() {
  Wire.onRequest(onRequest);
  Wire.onReceive(onReceive);
  Wire.begin(I2C_ADDR, D4, D5, 100000);   // slave: address, SDA, SCL, clock; the core's slave init enables the internal pull-ups
}

static uint32_t stuck_since = 0;   // millis() when a line was first seen low in this stretch, 0 while the bus is idle

// Time a line has been held in a stuck state; 0 while the bus looks normal.
static uint32_t stuckFor(uint32_t now) {
  int scl = gpio_get_level((gpio_num_t)D5), sda = gpio_get_level((gpio_num_t)D4);
  bool stuck = scl == 0 || sda == 0;   // idle is both high; a byte holds either low for microseconds only
  if (!stuck) stuck_since = 0;
  else if (!stuck_since) stuck_since = now ? now : 1;
  return stuck_since ? now - stuck_since : 0;
}

void setup() {
  Serial.begin(115200);
  esp_task_wdt_config_t wdt = {.timeout_ms = WDT_S * 1000, .idle_core_mask = 0, .trigger_panic = true};
  if (esp_task_wdt_reconfigure(&wdt) != ESP_OK) esp_task_wdt_init(&wdt);
  esp_task_wdt_add(NULL);
  startSlave();
}

void loop() {
  static uint32_t next = 0, seq = 0, next_note = 0, last_restart = 0;
  uint32_t now = millis();
  esp_task_wdt_reset();

  if (restart_asked) {
    Serial.println("R,restart asked over I2C");
    Serial.flush();
    ESP.restart();
  }
  if (stuckFor(now) > STUCK_MS && (slave_restarts == 0 || now - last_restart >= RESTART_GAP_MS)) {
    Wire.end();
    startSlave();
    slave_restarts++;
    last_restart = now;
    stuck_since = 0;   // the new slave gets a fresh STUCK_MS before it counts as stuck again
  }
  if ((int32_t)(now - next_note) >= 0) {
    next_note = now + 1000;
    Serial.printf("R,reset_reason=%d,slave_restarts=%lu\n", (int)esp_reset_reason(), (unsigned long)slave_restarts);
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
