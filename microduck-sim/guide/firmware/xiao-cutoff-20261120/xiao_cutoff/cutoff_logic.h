// MicroDuck power V2: decision logic of the XIAO SAMD21 low-voltage cutoff (PS-2, PV-2).
// Pure C++ with no Arduino dependency, so the same file compiles in the sketch and in the host test
// (../test/test_cutoff_logic.cpp, g++).
//
// Inputs are volts at the divider tops, already scaled by the sketch:
//   pack_v  A0: Pololu VOUT (the pack node while the switch is on; the dock voltage when charging)
//   mid_v   A1: middle cell tap of the XH balance lead = cell 1 (pack- to middle)
//   dock_v  A2: charge contact + ahead of the 1N5822
//   on_v    A3: button NO contact (the 10 k side); equals the pack node while the button is pressed
// Rules (power-switch-20261119/README.md PS-2, power-system-20261119/README.md PV-2, concept_v2.py wiring list):
//   - cut when the pack is under 6.3 V or either cell under 3.1 V, held 3 s;
//   - no cut during a 3 s grace after power-on (the XIAO starts when the button switches the robot on);
//   - the button holds the switch on only; holding it 2 s while on, then letting go, is a shutdown request:
//     the XIAO cuts. The cut fires on release so the Pololu never sees ON and OFF at the same time.
//     The press that switched the robot on is not counted: holds are armed only after the button was seen up.
//   - balance lead unplugged (middle tap reads near 0) is not a weak cell: the cell check pauses, pack check stays.
//   - once cut, latched (the XIAO loses its supply a moment later).
#pragma once
#include <stdint.h>

namespace cutoff {

struct Config {
  float pack_min_v = 6.30f;      // PS-2: 3.15 V per cell, above the DFR1202's 6 V input minimum
  float cell_min_v = 3.10f;      // PV-2
  float pack_hyst_v = 0.05f;     // the hold timer restarts only when every value is back above min + hysteresis
  float cell_hyst_v = 0.03f;
  uint32_t hold_ms = 3000;       // a foot-strike sag lasts well under this
  uint32_t grace_ms = 3000;      // after power-on
  uint32_t button_hold_ms = 2000;
  float press_frac = 0.60f;      // pressed when the NO contact reads above 60 % of the pack node
  float press_min_v = 3.0f;
  float dock_present_v = 7.0f;   // dock 8.6 V at the contacts; 0 V otherwise
  float xh_min_v = 1.0f;         // middle tap under this: balance lead unplugged
};

enum Reason : uint8_t { NONE = 0, PACK_LOW, CELL_LOW, BUTTON };

inline const char* reason_name(Reason r) {
  switch (r) {
    case PACK_LOW: return "pack_low";
    case CELL_LOW: return "cell_low";
    case BUTTON: return "button";
    default: return "-";
  }
}

struct Inputs {
  uint32_t t_ms;   // millis() since the XIAO started
  float pack_v, mid_v, dock_v, on_v;
};

struct State {
  // latched result
  bool cut = false;
  Reason reason = NONE;
  // derived each step, for the status line
  float cell1_v = 0, cell2_v = 0;
  bool xh_ok = false, charging = false, pressed = false, in_grace = true;
  uint32_t low_ms = 0;             // how long the undervoltage has been held
  // internal
  bool low_active = false;
  uint32_t low_since = 0;
  bool btn_armed = false;          // set once the button is seen up after power-on
  bool btn_down = false;
  uint32_t btn_since = 0;
  uint32_t held_ms = 0;            // current press length
};

inline void step(const Config& c, State& s, const Inputs& in) {
  if (s.cut) return;
  s.in_grace = in.t_ms < c.grace_ms;
  s.charging = in.dock_v >= c.dock_present_v;

  // cells: cell 1 is the middle tap, cell 2 the rest of the pack
  s.xh_ok = in.mid_v >= c.xh_min_v && in.mid_v <= in.pack_v - c.xh_min_v;
  s.cell1_v = s.xh_ok ? in.mid_v : 0.0f;
  s.cell2_v = s.xh_ok ? in.pack_v - in.mid_v : 0.0f;

  bool pack_low = in.pack_v < c.pack_min_v;
  bool cell_low = s.xh_ok && (s.cell1_v < c.cell_min_v || s.cell2_v < c.cell_min_v);
  bool all_clear = in.pack_v >= c.pack_min_v + c.pack_hyst_v &&
                   (!s.xh_ok || (s.cell1_v >= c.cell_min_v + c.cell_hyst_v && s.cell2_v >= c.cell_min_v + c.cell_hyst_v));

  if (pack_low || cell_low) {
    if (!s.low_active) { s.low_active = true; s.low_since = in.t_ms; }
  } else if (all_clear) {
    s.low_active = false;
  }
  s.low_ms = s.low_active ? in.t_ms - s.low_since : 0;
  if (s.low_active && s.low_ms >= c.hold_ms && !s.in_grace && (pack_low || cell_low)) {
    s.cut = true;
    s.reason = pack_low ? PACK_LOW : CELL_LOW;
    return;
  }

  // button
  s.pressed = in.on_v >= c.press_min_v && in.on_v >= c.press_frac * in.pack_v;
  if (s.pressed) {
    if (!s.btn_down) { s.btn_down = true; s.btn_since = in.t_ms; }
    s.held_ms = in.t_ms - s.btn_since;
  } else {
    bool long_press = s.btn_down && s.btn_armed && s.held_ms >= c.button_hold_ms;
    s.btn_down = false;
    s.held_ms = 0;
    if (long_press && !s.in_grace) {
      s.cut = true;
      s.reason = BUTTON;
      return;
    }
    s.btn_armed = true;
  }
}

}  // namespace cutoff
