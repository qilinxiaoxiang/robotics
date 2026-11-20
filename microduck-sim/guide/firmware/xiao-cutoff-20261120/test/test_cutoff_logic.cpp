// Host test of the XIAO cutoff decisions (../xiao_cutoff/cutoff_logic.h).
// Build and run: ./run_tests.sh   (g++ -std=c++11 -Wall -Wextra -Werror)
// Each case feeds a 50 ms sample stream, as the sketch does, and checks whether and when the cut fires.
#include <cmath>
#include <cstdio>
#include <functional>
#include "../xiao_cutoff/cutoff_logic.h"

using cutoff::Config;
using cutoff::Inputs;
using cutoff::State;

static int failures = 0, checks = 0;
#define CHECK(cond, ...)                                            \
  do {                                                              \
    ++checks;                                                       \
    if (!(cond)) {                                                  \
      ++failures;                                                   \
      std::printf("  FAIL %s:%d: ", __FILE__, __LINE__);            \
      std::printf(__VA_ARGS__);                                     \
      std::printf("\n");                                            \
    }                                                               \
  } while (0)

struct Sample { float pack, mid, dock, on; };
struct Result { bool cut; cutoff::Reason reason; uint32_t cut_t; State st; };

// run gen(t) every 50 ms from t=0 to end_ms; report the first cut
static Result run(const std::function<Sample(uint32_t)>& gen, uint32_t end_ms, const Config& c = Config()) {
  State s;
  Result r{false, cutoff::NONE, 0, s};
  for (uint32_t t = 0; t <= end_ms; t += 50) {
    Sample x = gen(t);
    cutoff::step(c, s, Inputs{t, x.pack, x.mid, x.dock, x.on});
    if (s.cut && !r.cut) { r.cut = true; r.reason = s.reason; r.cut_t = t; }
  }
  r.st = s;
  return r;
}

static Sample healthy(float pack = 7.9f) { return Sample{pack, pack / 2, 0.0f, 0.0f}; }

static void case_healthy() {
  std::puts("healthy pack, 60 s: no cut");
  Result r = run([](uint32_t) { return healthy(7.9f); }, 60000);
  CHECK(!r.cut, "cut at %u ms (%s)", r.cut_t, cutoff::reason_name(r.reason));
  CHECK(r.st.xh_ok && std::fabs(r.st.cell1_v - 3.95f) < 1e-3 && std::fabs(r.st.cell2_v - 3.95f) < 1e-3, "cells %.3f %.3f",
        r.st.cell1_v, r.st.cell2_v);
}

static void case_slow_sag() {
  std::puts("slow sag 7.0 -> 6.0 V over 100 s: cut 3 s after crossing 6.3 V");
  // 0.01 V per second; crosses 6.3 V at t = 70 s
  Result r = run([](uint32_t t) { float v = 7.0f - 0.01f * t / 1000.0f; return healthy(v); }, 100000);
  CHECK(r.cut && r.reason == cutoff::PACK_LOW, "cut=%d reason=%s", r.cut, cutoff::reason_name(r.reason));
  CHECK(r.cut_t >= 73000 && r.cut_t <= 73150, "cut at %u ms, expected about 73000", r.cut_t);
}

static void case_one_weak_cell() {
  std::puts("one weak cell: cell 1 sags to 3.0 V while the pack stays 7.1 V: cut on the cell");
  // cell 1 falls 3.6 -> 3.0 V over 60 s (crosses 3.1 V at 50 s); cell 2 stays at 4.1 V
  Result r = run([](uint32_t t) {
    float c1 = 3.6f - 0.01f * t / 1000.0f;
    if (c1 < 3.0f) c1 = 3.0f;
    float c2 = 4.1f;
    return Sample{c1 + c2, c1, 0.0f, 0.0f};
  }, 70000);
  CHECK(r.cut && r.reason == cutoff::CELL_LOW, "cut=%d reason=%s", r.cut, cutoff::reason_name(r.reason));
  CHECK(r.cut_t >= 53000 && r.cut_t <= 53150, "cut at %u ms, expected about 53000", r.cut_t);
  // the same with the weak cell on top (cell 2 = pack - middle tap)
  Result r2 = run([](uint32_t t) {
    float c2 = 3.6f - 0.01f * t / 1000.0f;
    if (c2 < 3.0f) c2 = 3.0f;
    return Sample{4.1f + c2, 4.1f, 0.0f, 0.0f};
  }, 70000);
  CHECK(r2.cut && r2.reason == cutoff::CELL_LOW && r2.cut_t >= 53000 && r2.cut_t <= 53150, "top cell: cut=%d at %u",
        r2.cut, r2.cut_t);
}

static void case_brief_dip() {
  std::puts("brief dips under 3 s: 0.3 s to 5.8 V and 2.9 s to 6.1 V: no cut; 3.2 s to 6.1 V: cut");
  Result r = run([](uint32_t t) {
    if (t >= 10000 && t < 10300) return healthy(5.8f);   // PS-2 validation: no trip on a 0.3 s dip to 5.8 V
    if (t >= 20000 && t < 22900) return healthy(6.1f);
    return healthy(7.6f);
  }, 40000);
  CHECK(!r.cut, "cut at %u ms (%s)", r.cut_t, cutoff::reason_name(r.reason));
  Result r2 = run([](uint32_t t) { return (t >= 20000 && t < 23200) ? healthy(6.1f) : healthy(7.6f); }, 40000);
  CHECK(r2.cut && r2.reason == cutoff::PACK_LOW && r2.cut_t == 23000, "3.2 s dip: cut=%d at %u", r2.cut, r2.cut_t);
  // a dip that recovers only to inside the hysteresis band does not restart the timer
  Result r3 = run([](uint32_t t) {
    if (t >= 20000 && t < 21500) return healthy(6.2f);
    if (t >= 21500 && t < 22500) return healthy(6.33f);  // above 6.30, below 6.35
    if (t >= 22500 && t < 24000) return healthy(6.2f);
    return healthy(7.6f);
  }, 40000);
  CHECK(r3.cut && r3.cut_t == 23000, "hysteresis band: cut=%d at %u", r3.cut, r3.cut_t);
}

static void case_charging_on_dock() {
  std::puts("charging on the dock: pack node held at 8.2 V by the dock, contacts 8.6 V: no cut, charging flag");
  Result r = run([](uint32_t) { return Sample{8.2f, 4.1f, 8.6f, 0.0f}; }, 60000);
  CHECK(!r.cut, "cut at %u", r.cut_t);
  CHECK(r.st.charging, "charging flag not set");
  // backing onto the dock with a nearly empty pack: the dock lifts the node before the 3 s run out
  Result r2 = run([](uint32_t t) {
    return t < 2000 ? Sample{6.25f, 3.12f, 0.0f, 0.0f} : Sample{7.4f, 3.7f, 8.6f, 0.0f};
  }, 30000);
  CHECK(!r2.cut, "dock arrival: cut at %u", r2.cut_t);
  // off the dock again: charging flag clears
  Result r3 = run([](uint32_t t) { return t < 5000 ? Sample{8.2f, 4.1f, 8.6f, 0.0f} : healthy(8.0f); }, 10000);
  CHECK(!r3.cut && !r3.st.charging, "off dock: cut=%d charging=%d", r3.cut, r3.st.charging);
}

static void case_grace() {
  std::puts("flat pack switched on: no cut inside the 3 s grace, cut right after it");
  Result r = run([](uint32_t) { return healthy(6.1f); }, 10000);
  CHECK(r.cut && r.reason == cutoff::PACK_LOW && r.cut_t == 3000, "cut=%d at %u", r.cut, r.cut_t);
}

static void case_button() {
  std::puts("button: power-on press held 3 s does nothing; later 2.5 s hold then release cuts on release");
  Result r = run([](uint32_t t) {
    Sample s = healthy(7.8f);
    if (t < 3000) s.on = 7.8f;                        // the press that switched the robot on, held 3 s
    if (t >= 10000 && t < 12500) s.on = 7.8f;         // shutdown request
    return s;
  }, 20000);
  CHECK(r.cut && r.reason == cutoff::BUTTON && r.cut_t == 12500, "cut=%d reason=%s at %u", r.cut, cutoff::reason_name(r.reason),
        r.cut_t);
  std::puts("button: short presses (a knock, 1.5 s) never cut");
  Result r2 = run([](uint32_t t) {
    Sample s = healthy(7.8f);
    if (t < 300) s.on = 7.8f;
    if (t >= 10000 && t < 10200) s.on = 7.8f;
    if (t >= 15000 && t < 16500) s.on = 7.8f;
    return s;
  }, 20000);
  CHECK(!r2.cut, "cut at %u (%s)", r2.cut_t, cutoff::reason_name(r2.reason));
  std::puts("button: released-state leakage (A3 reading the Pololu ON pin through 10 k) is not a press");
  Result r3 = run([](uint32_t) { Sample s = healthy(7.8f); s.on = 1.2f; return s; }, 20000);
  CHECK(!r3.cut && !r3.st.pressed, "cut=%d pressed=%d", r3.cut, r3.st.pressed);
}

static void case_balance_unplugged() {
  std::puts("balance lead unplugged (middle tap 0 V): no cell cut, pack cut still works");
  Result r = run([](uint32_t) { return Sample{7.6f, 0.0f, 0.0f, 0.0f}; }, 30000);
  CHECK(!r.cut && !r.st.xh_ok, "cut=%d xh_ok=%d", r.cut, r.st.xh_ok);
  Result r2 = run([](uint32_t t) { return Sample{t < 10000 ? 7.6f : 6.2f, 0.0f, 0.0f, 0.0f}; }, 20000);
  CHECK(r2.cut && r2.reason == cutoff::PACK_LOW && r2.cut_t == 13000, "cut=%d at %u", r2.cut, r2.cut_t);
}

static void case_latch() {
  std::puts("cut latches even if the voltage recovers");
  Result r = run([](uint32_t t) { return t < 10000 ? healthy(6.0f) : healthy(8.0f); }, 20000);
  CHECK(r.cut && r.st.cut && r.cut_t == 3000, "cut=%d latched=%d at %u", r.cut, r.st.cut, r.cut_t);
}

int main() {
  case_healthy();
  case_slow_sag();
  case_one_weak_cell();
  case_brief_dip();
  case_charging_on_dock();
  case_grace();
  case_button();
  case_balance_unplugged();
  case_latch();
  std::printf("%d checks, %d failed\n", checks, failures);
  return failures ? 1 : 0;
}
