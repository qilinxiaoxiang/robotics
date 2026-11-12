#!/usr/bin/env python3
"""Cycle model of the two I2S PIO programs against models of the INMP441 and the MAX98357A.

What is under test is the built artefact, not a re-typed copy:
  - the opcodes are read from the headers pioasm generated (build/i2s_mic.pio.h, build/i2s_spk.pio.h);
  - the sample conversion and the touch line format are the firmware's C code (src/audio_convert.h,
    src/touch_format.c), compiled for the host through tools/host_shim.c and called with ctypes.
The PIO interpreter below is hand-written (plain Python, no packages) and covers only the instructions these
programs use; anything else raises. It follows the RP2040 datasheet's rules for side-set, autopush, autopull and
the two-flip-flop input synchroniser. It is a model: it shows the logic and the timing budget, not the silicon.

Datasheet figures used (read 2026-11-12):
  INMP441 DS-INMP441-00 Rev 1.1: SCK 0.5 to 3.2 MHz, period >= 312 ns, high and low >= 50 ns, WS setup >= 0 ns and
    hold >= 20 ns around the SCK rising edge, 64 SCK per stereo frame, 24-bit two's complement MSB first, MSB one SCK
    after the WS edge, output tri-stated outside its slot. No SD output delay is specified, so the test sweeps it.
  MAX98357A 19-6779 Rev 7: I2S, data clocked on the BCLK rising edge, BCLK = 32/48/64 x LRCLK, BCLK high and low
    >= 15 ns, DIN and LRCLK setup and hold >= 10 ns to the BCLK rising edge, left channel while LRCLK is low.

    python3 tools/test_pio.py --build build [--json build/pio-check.json]
"""
import argparse
import bisect
import ctypes
import json
import os
import random
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CLK_SYS_HZ = 61_440_000          # audio.h AUDIO_SYS_CLOCK_HZ
PIO_CLKDIV = 10                  # audio.h AUDIO_PIO_CLKDIV
T_SYS = 1e9 / CLK_SYS_HZ         # ns
T_PIO = T_SYS * PIO_CLKDIV       # ns per PIO cycle
T_OUT = 5.0                      # ns, assumed pad output delay (same for clock and data pins)
SYNC = 2 * T_SYS                 # ns, input synchroniser: IN sees the pin as it was two clk_sys cycles earlier
FIFO_DEPTH = 8                   # joined FIFO


# ---------------------------------------------------------------- program loading

def load_program(build_dir, name):
    text = open(os.path.join(build_dir, f"{name}.pio.h")).read()
    body = re.search(rf"{name}_program_instructions\[\]\s*=\s*\{{(.*?)\}};", text, re.S).group(1)
    opcodes = [int(m, 16) for m in re.findall(r"0x([0-9a-fA-F]{4})", body)]
    get = lambda key: int(re.search(rf"#define {name}_{key}\s+(\d+)", text).group(1))
    return {"name": name, "opcodes": opcodes, "wrap_target": get("wrap_target"), "wrap": get("wrap"),
            "entry": get("offset_entry")}


def audio_h(key):
    text = open(os.path.join(HERE, "src", "audio.h")).read()
    return int(re.search(rf"#define {key}\s+(\d+)", text).group(1))


# ---------------------------------------------------------------- PIO state machine model

class StateMachine:
    """One state machine with 2 side-set pins (no enable bit), shift left, autopush/autopull at 32 bits."""

    def __init__(self, prog):
        self.p = prog
        self.pc = prog["entry"]
        self.x = 0
        self.isr = self.isr_count = 0
        self.osr, self.osr_count = 0, 32          # empty
        self.rx, self.tx = [], []
        self.side = 0                             # 2 bits
        self.out_pin = 0
        self.push_pending = False                 # an IN that has shifted and waits for room in the RX FIFO
        self.stalled_cycles = 0

    def step(self, read_pins):
        """Run one PIO cycle. read_pins() gives the synchronised input pin value (2 bits). Returns True if stalled."""
        ins = self.p["opcodes"][self.pc]
        op, field, arg = ins >> 13, (ins >> 8) & 0x1F, ins & 0xFF
        if field & 0x7:
            raise NotImplementedError("delay cycles are not used by these programs")
        self.side = field >> 3                    # side-set applies even when the instruction stalls
        next_pc = self.p["wrap_target"] if self.pc == self.p["wrap"] else self.pc + 1
        stalled = False

        if op == 0:                               # JMP
            cond, addr = arg >> 5, arg & 0x1F
            if cond == 0:
                next_pc = addr
            elif cond == 2:                       # x--: jump if x was non-zero, decrement either way
                if self.x != 0:
                    next_pc = addr
                self.x = (self.x - 1) & 0xFFFFFFFF
            else:
                raise NotImplementedError(f"jmp condition {cond}")
        elif op == 2:                             # IN
            src, n = arg >> 5, (arg & 0x1F) or 32
            if not self.push_pending:
                if src == 0:
                    val = read_pins() & ((1 << n) - 1)
                elif src == 3:
                    val = 0
                else:
                    raise NotImplementedError(f"in source {src}")
                self.isr = ((self.isr << n) | val) & 0xFFFFFFFF
                self.isr_count = min(32, self.isr_count + n)
            if self.isr_count >= 32:
                if len(self.rx) >= FIFO_DEPTH:
                    self.push_pending = stalled = True
                else:
                    self.rx.append(self.isr)
                    self.isr = self.isr_count = 0
                    self.push_pending = False
        elif op == 3:                             # OUT
            dest, n = arg >> 5, (arg & 0x1F) or 32
            if dest != 0:
                raise NotImplementedError(f"out destination {dest}")
            if self.osr_count >= 32:              # empty: stall; the refill below may load it for the retry
                stalled = True
            else:
                self.out_pin = (self.osr >> (32 - n)) & ((1 << n) - 1)
                self.osr = (self.osr << n) & 0xFFFFFFFF
                self.osr_count += n
        elif op == 5:                             # MOV: only "mov y, y" (nop)
            if arg != 0b01000010:
                raise NotImplementedError(f"mov {arg:#04x}")
        elif op == 7:                             # SET
            dest, data = arg >> 5, arg & 0x1F
            if dest != 1:
                raise NotImplementedError(f"set destination {dest}")
            self.x = data
        else:
            raise NotImplementedError(f"opcode {ins:#06x}")

        if self.osr_count >= 32 and self.tx:      # autopull refill
            self.osr, self.osr_count = self.tx.pop(0), 0
        if stalled:
            self.stalled_cycles += 1
        else:
            self.pc = next_pc
        return stalled


class Wire:
    """A signal as a list of (time, level) changes."""

    def __init__(self, level=0):
        self.t, self.v = [-1e18], [level]

    def set(self, t, level):
        if level != self.v[-1]:
            if t < self.t[-1]:
                raise AssertionError("signal changes out of order")
            self.t.append(t)
            self.v.append(level)

    def at(self, t):
        return self.v[bisect.bisect_right(self.t, t) - 1]

    def last_change(self, t):
        return self.t[bisect.bisect_right(self.t, t) - 1]

    def next_change(self, t):
        i = bisect.bisect_right(self.t, t)
        return self.t[i] if i < len(self.t) else 1e18


def edges(wire):
    """(time, 'rise'|'fall') for every change after the initial level."""
    return [(t, "rise" if v else "fall") for t, v in zip(wire.t[1:], wire.v[1:])]


# ---------------------------------------------------------------- device models

class Inmp441:
    """Drives 24 bits, MSB first, in its own slot (WS low = left); starts one SCK after the WS edge; tri-states after
    the 24th bit. A released line keeps its last level here (bus capacitance against a 100 k pull-down)."""

    def __init__(self, channel_ws, samples, sd_delay_ns, line):
        self.ws_mine, self.samples, self.delay, self.line = channel_ws, samples, sd_delay_ns, line
        self.last_ws, self.bit, self.index, self.cur = None, None, 0, 0
        self.driving_until = -1e18

    def sck_rise(self, t, ws):
        if ws != self.last_ws:
            self.last_ws = ws
            if ws == self.ws_mine:
                self.bit = 0
                self.cur = self.samples[self.index] & 0xFFFFFF if self.index < len(self.samples) else 0
                self.index += 1
            # the other slot: this microphone was already released after its 24th bit

    def sck_fall(self, t):
        if self.bit is not None:
            if self.bit < 24:
                self.line.set(t + self.delay, (self.cur >> (23 - self.bit)) & 1)
                self.bit += 1
            else:
                self.bit = None                   # released


class Max98357a:
    """Reads LRC and DIN on each BCLK rising edge. A slot's first data bit is the edge after the one where LRC was
    seen to change; the 32nd bit is read on the edge that sees the next LRC change."""

    def __init__(self):
        self.last_lrc, self.word, self.count, self.channel = None, 0, 0, None
        self.frames, self.cur = [], {}
        self.bad_lengths = 0

    def bclk_rise(self, lrc, din):
        if self.channel is not None:
            self.word = ((self.word << 1) | din) & 0xFFFFFFFF
            self.count += 1
        if lrc != self.last_lrc:
            if self.channel is not None:
                if self.count != 32:
                    self.bad_lengths += 1
                self.cur[self.channel] = self.word
                if self.channel == 1:
                    if 0 in self.cur:
                        self.frames.append((self.cur[0], self.cur[1]))
                    self.cur = {}
            self.last_lrc, self.channel, self.word, self.count = lrc, lrc, 0, 0


# ---------------------------------------------------------------- firmware C code on the host

def load_shim(build_dir):
    lib = os.path.join(build_dir, "host_shim.so")
    cmd = [os.environ.get("CC", "cc"), "-shared", "-fPIC", "-O1", "-Wall", "-Wextra", "-Werror",
           "-I", os.path.join(HERE, "src"), "-o", lib,
           os.path.join(HERE, "tools", "host_shim.c"), os.path.join(HERE, "src", "touch_format.c")]
    subprocess.run(cmd, check=True)
    return ctypes.CDLL(lib)


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def s24(v):
    v &= 0xFFFFFF
    return v - 0x1000000 if v & 0x800000 else v


# ---------------------------------------------------------------- microphone run

def run_mic(prog, shim, frames, sd_delay_ns, stall_at_cycle=None, stall_cycles=0, seed=1, entry=None):
    rng = random.Random(seed)
    left = [rng.getrandbits(24) for _ in range(frames + 2)]
    right = [rng.getrandbits(24) for _ in range(frames + 2)]
    back = [rng.getrandbits(24) for _ in range(frames + 2)]
    # a few fixed patterns that expose bit-order and sign mistakes
    for i, v in enumerate((0x800000, 0x7FFFFF, 0x000001, 0xFFFFFF, 0xA5A5A5, 0x123456)):
        left[i + 1], right[i + 1], back[i + 1] = v, v ^ 0xFFFFFF, (v * 3) & 0xFFFFFF

    sck, ws, sd_ears, sd_back = Wire(0), Wire(0), Wire(0), Wire(0)
    mics = [Inmp441(0, left, sd_delay_ns, sd_ears), Inmp441(1, right, sd_delay_ns, sd_ears),
            Inmp441(0, back, sd_delay_ns, sd_back)]
    sm = StateMachine(prog)
    if entry is not None:
        sm.pc, sm.x = entry, 30
    words, cycle = [], 0
    while len(words) < frames * 4:
        t = cycle * T_PIO
        read = lambda: sd_ears.at(t - SYNC) | (sd_back.at(t - SYNC) << 1)
        prev_sck = sck.v[-1]
        sm.step(read)
        t_edge = t + T_OUT
        new_sck, new_ws = sm.side & 1, sm.side >> 1
        ws.set(t_edge, new_ws)
        sck.set(t_edge, new_sck)
        if new_sck != prev_sck:
            for m in mics:
                if new_sck:
                    m.sck_rise(t_edge, ws.at(t_edge))
                else:
                    m.sck_fall(t_edge)
        draining = not (stall_at_cycle is not None and stall_at_cycle <= cycle < stall_at_cycle + stall_cycles)
        if draining:
            words.extend(sm.rx)
            sm.rx.clear()
        cycle += 1
        if cycle > frames * 128 * 4 + stall_cycles + 10000:
            raise AssertionError("microphone program does not produce words")

    out = (ctypes.c_int16 * 4)()
    decoded, decoded_gain8 = [], []
    for f in range(frames):
        w = (ctypes.c_uint32 * 4)(*words[4 * f:4 * f + 4])
        shim.shim_mic_frame_to_usb(w, out, 0)
        decoded.append(tuple(out))
        shim.shim_mic_frame_to_usb(w, out, 8)
        decoded_gain8.append(tuple(out))
    sat = lambda v: max(-32768, min(32767, v))
    want = [(s16(left[f] >> 8), s16(right[f] >> 8), s16(back[f] >> 8), 0) for f in range(frames)]
    want_gain8 = [(sat(s24(left[f])), sat(s24(right[f])), sat(s24(back[f])), 0) for f in range(frames)]
    return {"sck": sck, "ws": ws, "decoded": decoded, "want": want, "decoded_gain8": decoded_gain8,
            "want_gain8": want_gain8, "stalled_cycles": sm.stalled_cycles, "cycles": cycle}


def clock_facts(clk, ws):
    """Periods, duty and frame structure of a bit clock and its word select, from the simulated edges."""
    ce = edges(clk)
    rises = [t for t, k in ce if k == "rise"]
    falls = [t for t, k in ce if k == "fall"]
    periods = [b - a for a, b in zip(rises, rises[1:])]
    highs = [f - r for r in rises for f in [next((x for x in falls if x > r), None)] if f is not None]
    lows = [r - f for f in falls for r in [next((x for x in rises if x > f), None)] if r is not None]
    we = edges(ws)
    ws_falls = [t for t, k in we if k == "fall"]
    per_frame = [sum(1 for r in rises if a <= r < b) for a, b in zip(ws_falls, ws_falls[1:])]
    ws_rises = [t for t, k in we if k == "rise"]
    low_half = [sum(1 for r in rises if a <= r < b) for a in ws_falls for b in [next((x for x in ws_rises if x > a), None)]
                if b is not None]
    # WS edge position against the clock: time since the previous rising edge (hold) and to the next one (setup)
    hold = min(t - max(r for r in rises if r <= t) for t, _ in we if any(r <= t for r in rises))
    setup = min(min(r for r in rises if r > t) - t for t, _ in we if any(r > t for r in rises))
    return {"period_ns": (min(periods), max(periods)), "high_ns": min(highs), "low_ns": min(lows),
            "bit_clock_hz": 1e9 / (sum(periods) / len(periods)), "clocks_per_frame": sorted(set(per_frame)),
            "clocks_in_left_half": sorted(set(low_half)),
            "frame_hz": 1e9 / ((ws_falls[-1] - ws_falls[0]) / (len(ws_falls) - 1)),
            "ws_setup_ns": setup, "ws_hold_ns": hold}


# ---------------------------------------------------------------- speaker run

def run_spk(prog, shim, frames, seed=2):
    rng = random.Random(seed)
    pcm = [(s16(rng.getrandbits(16)), s16(rng.getrandbits(16))) for _ in range(frames + 4)]
    for i, v in enumerate((-32768, 32767, 1, -1, 0x1234, 0x5A5A)):
        pcm[i + 1] = (s16(v), s16(~v))
    feed = []
    w = (ctypes.c_uint32 * 2)()
    for l, r in pcm:
        shim.shim_usb_frame_to_spk((ctypes.c_int16 * 2)(l, r), w)
        feed.extend(w)

    bclk, lrc, din = Wire(0), Wire(0), Wire(0)
    sm = StateMachine(prog)
    setup_min = hold_min = 1e18
    rises = []
    for cycle in range((frames + 1) * 64 * 2 + 8):
        while len(sm.tx) < FIFO_DEPTH and feed:          # the DMA keeps the TX FIFO full
            sm.tx.append(feed.pop(0))
        t = cycle * T_PIO
        prev = bclk.v[-1]
        sm.step(lambda: 0)
        t_edge = t + T_OUT
        lrc.set(t_edge, sm.side >> 1)
        din.set(t_edge, sm.out_pin)
        bclk.set(t_edge, sm.side & 1)
        if (sm.side & 1) and not prev:
            rises.append(t_edge)
    # the amplifier reads at each rising edge; evaluate after the run so the hold time can look forward
    for t_r in rises:
        for sig in (lrc, din):
            setup_min = min(setup_min, t_r - sig.last_change(t_r - 1e-6))
            hold_min = min(hold_min, sig.next_change(t_r - 1e-6) - t_r)
    amp = Max98357a()
    for t_r in rises:
        amp.bclk_rise(lrc.at(t_r - 1e-6), din.at(t_r - 1e-6))
    want = [((l & 0xFFFF) << 16, (r & 0xFFFF) << 16) for l, r in pcm]
    return {"bclk": bclk, "lrc": lrc, "got": amp.frames, "want": want, "setup_ns": setup_min, "hold_ns": hold_min,
            "bad_lengths": amp.bad_lengths, "stalled_cycles": sm.stalled_cycles}


# ---------------------------------------------------------------- checks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default=os.path.join(HERE, "build"))
    ap.add_argument("--json")
    args = ap.parse_args()

    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    check("model constants match src/audio.h", (audio_h("AUDIO_SYS_CLOCK_HZ"), audio_h("AUDIO_PIO_CLKDIV"),
          audio_h("AUDIO_PIO_CYCLES_PER_BIT"), audio_h("AUDIO_BITS_PER_FRAME")) == (CLK_SYS_HZ, PIO_CLKDIV, 2, 64),
          f"clk_sys {CLK_SYS_HZ} Hz, divider {PIO_CLKDIV}")
    vco, pd1, pd2 = audio_h("AUDIO_PLL_VCO_HZ"), audio_h("AUDIO_PLL_POSTDIV1"), audio_h("AUDIO_PLL_POSTDIV2")
    check("PLL settings give clk_sys exactly and are legal for the RP2040 (12 MHz reference, VCO 750 to 1600 MHz, "
          "post dividers 1 to 7)",
          vco % 12_000_000 == 0 and 750e6 <= vco <= 1600e6 and 1 <= pd2 <= pd1 <= 7 and vco // (pd1 * pd2) == CLK_SYS_HZ
          and vco % (pd1 * pd2) == 0 and 16 <= vco // 12_000_000 <= 320,
          f"VCO {vco} Hz = 12 MHz x {vco // 12_000_000}, / {pd1} / {pd2} = {vco / (pd1 * pd2):.0f} Hz")

    shim = load_shim(args.build)
    mic, spk = load_program(args.build, "i2s_mic"), load_program(args.build, "i2s_spk")
    check("both programs fit one PIO block (32 instructions)", len(mic["opcodes"]) + len(spk["opcodes"]) <= 32,
          f"{len(mic['opcodes'])} + {len(spk['opcodes'])} instructions")

    # ---- microphones ----
    FRAMES = 40
    base = run_mic(mic, shim, FRAMES, sd_delay_ns=30.0)
    cf = clock_facts(base["sck"], base["ws"])
    check("mic: SCK is 3.072 MHz (64 x 48 kHz) and inside 0.5 to 3.2 MHz", abs(cf["bit_clock_hz"] - 3_072_000) < 1,
          f"{cf['bit_clock_hz']:.1f} Hz")
    check("mic: SCK period >= 312 ns, every period equal", cf["period_ns"][0] >= 312 and cf["period_ns"][1] - cf["period_ns"][0] < 1e-6,
          f"{cf['period_ns'][0]:.2f} ns")
    check("mic: SCK high >= 50 ns and low >= 50 ns", cf["high_ns"] >= 50 and cf["low_ns"] >= 50,
          f"high {cf['high_ns']:.2f} ns, low {cf['low_ns']:.2f} ns")
    check("mic: 64 SCK per frame, 32 in each half", cf["clocks_per_frame"] == [64] and cf["clocks_in_left_half"] == [32],
          f"per frame {cf['clocks_per_frame']}, left half {cf['clocks_in_left_half']}")
    check("mic: WS is 48 kHz", abs(cf["frame_hz"] - 48000) < 0.01, f"{cf['frame_hz']:.3f} Hz")
    check("mic: WS setup >= 0 ns and hold >= 20 ns around the SCK rising edge", cf["ws_setup_ns"] >= 0 and cf["ws_hold_ns"] >= 20,
          f"setup {cf['ws_setup_ns']:.1f} ns, hold {cf['ws_hold_ns']:.1f} ns")
    check("mic: every frame decodes to the top 16 bits of each microphone's 24-bit sample, ch3 = 0 "
          "(left ear, right ear, back; includes the first frame)", base["decoded"] == base["want"],
          f"{sum(a == b for a, b in zip(base['decoded'], base['want']))} of {FRAMES} frames")
    check("mic: gain shift 8 returns the low bits too (24-bit sample saturated to 16 bits)",
          base["decoded_gain8"] == base["want_gain8"],
          f"{sum(a == b for a, b in zip(base['decoded_gain8'], base['want_gain8']))} of {FRAMES} frames")
    check("mic: no stall while the FIFO is drained", base["stalled_cycles"] == 0, f"{base['stalled_cycles']} stalled cycles")

    passing = []
    for d in range(0, 331, 5):
        r = run_mic(mic, shim, 12, sd_delay_ns=float(d), seed=100 + d)
        if r["decoded"] == r["want"]:
            passing.append(d)
    contiguous = passing == list(range(0, passing[-1] + 1, 5)) if passing else False
    check("mic: decodes for every SD output delay from 0 to at least 250 ns after the SCK falling edge",
          contiguous and passing[-1] >= 250, f"passes 0 to {passing[-1] if passing else None} ns (5 ns steps); "
          f"model: sample point {2 * T_PIO - SYNC - T_OUT:.1f} ns after the edge that launched the bit")

    stall = run_mic(mic, shim, FRAMES, sd_delay_ns=30.0, stall_at_cycle=1000, stall_cycles=700)
    check("mic: a full RX FIFO pauses the clocks and no word is lost or shifted afterwards",
          stall["stalled_cycles"] > 0 and stall["decoded"] == stall["want"],
          f"{stall['stalled_cycles']} stalled cycles, {sum(a == b for a, b in zip(stall['decoded'], stall['want']))} of {FRAMES} frames")

    # Controls: the same run must fail when the word alignment or the sample point is wrong, or the test proves nothing.
    skewed = run_mic(mic, shim, FRAMES, sd_delay_ns=30.0, entry=mic["wrap_target"])
    check("control: started without the entry code (words one bit early) the same data does NOT decode",
          skewed["decoded"] != skewed["want"],
          f"{sum(a == b for a, b in zip(skewed['decoded'], skewed['want']))} of {FRAMES} frames match")
    late = run_mic(mic, shim, 12, sd_delay_ns=2 * T_PIO, seed=7)
    check("control: an SD delay of a whole SCK period does NOT decode", late["decoded"] != late["want"],
          f"{sum(a == b for a, b in zip(late['decoded'], late['want']))} of 12 frames match")

    # ---- amplifier ----
    s = run_spk(spk, shim, FRAMES)
    sf = clock_facts(s["bclk"], s["lrc"])
    check("spk: BCLK is 3.072 MHz = 64 x LRC, LRC 48 kHz", abs(sf["bit_clock_hz"] - 3_072_000) < 1 and sf["clocks_per_frame"] == [64]
          and sf["clocks_in_left_half"] == [32] and abs(sf["frame_hz"] - 48000) < 0.01,
          f"{sf['bit_clock_hz']:.1f} Hz, {sf['clocks_per_frame']} per frame, LRC {sf['frame_hz']:.3f} Hz")
    check("spk: BCLK high >= 15 ns and low >= 15 ns, every period equal", sf["high_ns"] >= 15 and sf["low_ns"] >= 15
          and sf["period_ns"][1] - sf["period_ns"][0] < 1e-6, f"high {sf['high_ns']:.2f} ns, low {sf['low_ns']:.2f} ns")
    check("spk: DIN and LRC setup >= 10 ns and hold >= 10 ns to the BCLK rising edge", s["setup_ns"] >= 10 and s["hold_ns"] >= 10,
          f"setup {s['setup_ns']:.1f} ns, hold {s['hold_ns']:.1f} ns")
    check("spk: every slot is 32 bits long", s["bad_lengths"] == 0, f"{s['bad_lengths']} slots of another length")
    first = next((i for i in range(len(s["want"])) if s["want"][i:i + len(s["got"])] == s["got"]), None)
    check("spk: the amplifier model reads each 16-bit sample MSB first, one BCLK after the LRC edge, left while LRC is "
          "low, zeros in the low 16 bits", first is not None and first <= 1,
          f"{len(s['got'])} frames read; they match the frames sent starting at frame {first}")
    check("spk: no stall while the FIFO is kept fed", s["stalled_cycles"] == 0, f"{s['stalled_cycles']} stalled cycles")

    # ---- touch line format ----
    block = bytes(range(0x10, 0x10 + 24))
    out = ctypes.create_string_buffer(64)
    shim.shim_touch_format_block(block, out)
    line = out.value.decode()
    check("touch: line is 'T ' + 48 hex digits and bytes.fromhex(line[2:]) returns the 24 bytes read",
          re.fullmatch(r"T [0-9a-f]{48}", line) is not None and bytes.fromhex(line[2:]) == block, line)

    failed = [c for c in checks if not c["ok"]]
    for c in checks:
        print(f"{'PASS' if c['ok'] else 'FAIL'}  {c['check']}: {c['detail']}")
    print(f"pio and conversion model: {len(checks) - len(failed)} of {len(checks)} checks passed")
    if args.json:
        with open(args.json, "w") as f:
            json.dump({"t_pio_ns": T_PIO, "t_sys_ns": T_SYS, "assumed_pad_delay_ns": T_OUT, "mic_clock": cf, "spk_clock": sf,
                       "mic_sd_delay_pass_ns": passing, "checks": checks, "passed": len(checks) - len(failed),
                       "failed": len(failed)}, f, indent=1)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
