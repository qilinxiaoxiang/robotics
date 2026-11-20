// MicroDuck power V2: low-voltage cutoff and button shutdown on a Seeed XIAO SAMD21 (PS-2, PV-2).
// Board: Seeed SAMD Boards -> "Seeeduino XIAO" (FQBN Seeeduino:samd:seeed_XIAO_m0).
// Wiring (guide chapter 12, step bv2-harness):
//   A0 <- Pololu VOUT through 100 k (top) / 33 k (to GND)
//   A1 <- battery XH middle pin through 100 k / 100 k
//   A2 <- charge contact + (1N5822 input end) through 100 k / 33 k
//   A3 <- button NO contact (10 k side) through 100 k / 33 k
//   D6 -> 1N4148 -> Pololu 2813 OFF (100 k OFF to GND on the Pololu side)
//   5V / GND from the DFR1202 5 V output
// The decision rules live in cutoff_logic.h (host-tested in ../test).
//
// Live feedback:
//   - the orange user LED (pin 13, active low): one short blink a second = watching, all fine; two short blinks =
//     the charge contacts carry dock voltage; fast blink (5 Hz) = undervoltage being timed or the button held 2 s
//     (let go now to switch off); steady = cutting.
//   - USB serial, 115200: one status line every 0.5 s (volts, raw ADC counts for calibration, state). See README.md
//     for the 5 V back-feed caveat before plugging USB in while the XIAO sits in the harness.

#include "cutoff_logic.h"

// ---------------------------------------------------------------- calibration (edit here)
// Divider ratios from the nominal resistors; *_TRIM corrects each channel after a bench check against a meter:
// TRIM = meter volts / printed volts. VREF is the 3.3 V analog supply (Seeed wiki: 12-bit reads, 0-3.3 V).
static const float VREF = 3.30f;
static const float ADC_FULL = 4095.0f;
static const float DIV_PACK = (100.0f + 33.0f) / 33.0f;   // A0
static const float DIV_MID = (100.0f + 100.0f) / 100.0f;  // A1
static const float DIV_DOCK = (100.0f + 33.0f) / 33.0f;   // A2
static const float DIV_ON = (100.0f + 33.0f) / 33.0f;     // A3
static const float PACK_TRIM = 1.000f;
static const float MID_TRIM = 1.000f;
static const float DOCK_TRIM = 1.000f;
static const float ON_TRIM = 1.000f;
static const int N_AVG = 16;            // reads averaged per channel per step
static const uint32_t STEP_MS = 50;     // decision period
static const uint32_t STATUS_MS = 500;  // serial status period

// CUT_ prefix: the core's variant.h already defines PIN_LED and friends as macros
static const int CUT_PIN_PACK = A0, CUT_PIN_MID = A1, CUT_PIN_DOCK = A2, CUT_PIN_ON = A3;
static const int CUT_PIN_OFF = 6;       // D6
static const int CUT_PIN_LED = 13;      // user LED, active low

static cutoff::Config cfg;
static cutoff::State st;
static uint32_t last_step = 0, last_status = 0;
static uint16_t raw_pack, raw_mid, raw_dock, raw_on;
static float v_pack, v_mid, v_dock, v_on;

static uint16_t read_avg(int pin) {
  analogRead(pin);  // discard the first read after the mux change (100 k source impedance)
  uint32_t sum = 0;
  for (int i = 0; i < N_AVG; i++) sum += analogRead(pin);
  return (uint16_t)(sum / N_AVG);
}

static float to_volts(uint16_t raw, float div, float trim) { return raw * (VREF / ADC_FULL) * div * trim; }

static void led(bool on) { digitalWrite(CUT_PIN_LED, on ? LOW : HIGH); }

static void led_pattern(uint32_t now) {
  if (st.cut) { led(true); return; }
  bool urgent = st.low_active || (st.btn_down && st.btn_armed && st.held_ms >= cfg.button_hold_ms);
  if (urgent) { led((now / 100) % 2 == 0); return; }
  uint32_t ph = now % 1000;
  bool on = ph < 60 || (st.charging && ph >= 180 && ph < 240);
  led(on);
}

static void print_status(uint32_t now) {
  if (!Serial) return;  // no host attached: never block
  // Serial.print(float, 2) instead of printf: newlib-nano printf has no %f on this core
  Serial.print("t="); Serial.print(now);
  Serial.print(" pack="); Serial.print(v_pack, 2);
  Serial.print(" c1="); Serial.print(st.cell1_v, 2);
  Serial.print(" c2="); Serial.print(st.cell2_v, 2);
  Serial.print(" dock="); Serial.print(v_dock, 2);
  Serial.print(" on="); Serial.print(v_on, 2);
  Serial.print(" xh="); Serial.print(st.xh_ok);
  Serial.print(" chg="); Serial.print(st.charging);
  Serial.print(" btn="); Serial.print(st.pressed);
  Serial.print(" held="); Serial.print(st.held_ms);
  Serial.print(" grace="); Serial.print(st.in_grace);
  Serial.print(" low_ms="); Serial.print(st.low_ms);
  Serial.print(" cut="); Serial.print(st.cut);
  Serial.print(" reason="); Serial.print(cutoff::reason_name(st.reason));
  Serial.print(" raw="); Serial.print(raw_pack); Serial.print(',');
  Serial.print(raw_mid); Serial.print(','); Serial.print(raw_dock); Serial.print(',');
  Serial.println(raw_on);
}

void setup() {
  // OFF line low before anything else: a floating D6 must never switch the robot off
  pinMode(CUT_PIN_OFF, OUTPUT);
  digitalWrite(CUT_PIN_OFF, LOW);
  pinMode(CUT_PIN_LED, OUTPUT);
  led(false);
  analogReadResolution(12);
  // longest sampling time: the dividers present about 25 k (A1 50 k); the core sets SAMPCTRL 5 (wiring.c)
  ADC->SAMPCTRL.reg = ADC_SAMPCTRL_SAMPLEN(63);
  while (ADC->STATUS.bit.SYNCBUSY) {}
  Serial.begin(115200);
}

void loop() {
  uint32_t now = millis();
  if (now - last_step >= STEP_MS) {
    last_step = now;
    raw_pack = read_avg(CUT_PIN_PACK);
    raw_mid = read_avg(CUT_PIN_MID);
    raw_dock = read_avg(CUT_PIN_DOCK);
    raw_on = read_avg(CUT_PIN_ON);
    v_pack = to_volts(raw_pack, DIV_PACK, PACK_TRIM);
    v_mid = to_volts(raw_mid, DIV_MID, MID_TRIM);
    v_dock = to_volts(raw_dock, DIV_DOCK, DOCK_TRIM);
    v_on = to_volts(raw_on, DIV_ON, ON_TRIM);
    bool was_cut = st.cut;
    cutoff::step(cfg, st, cutoff::Inputs{now, v_pack, v_mid, v_dock, v_on});
    if (st.cut) {
      digitalWrite(CUT_PIN_OFF, HIGH);  // held high until the switch removes our supply
      if (!was_cut) print_status(now);
    }
  }
  if (now - last_status >= STATUS_MS) {
    last_status = now;
    print_status(now);
  }
  led_pattern(now);
}
