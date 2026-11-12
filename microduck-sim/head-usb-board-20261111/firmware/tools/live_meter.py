#!/usr/bin/env python3
"""Live readout of the head USB board's serial port for bench work: microphone level bars and touch pad counts.

Run it before tapping a microphone or touching a pad, so every action shows at once:

    python3 tools/live_meter.py /dev/tty.usbmodemXXXX        (macOS)
    python3 tools/live_meter.py /dev/ttyACM0                 (Linux)

Plain Python (termios), no packages. It asks the board for a status line four times a second ("?") and redraws one
line: peak level of the left ear, right ear and back microphone since the last request, the five pad counts, and the
error counters. The microphone meter needs no audio program running on the host. Ctrl-C to stop.
Untested against hardware as of 2026-11-12; checked against a pseudo-terminal that replays the firmware's line formats.
"""
import math
import os
import select
import struct
import sys
import termios
import time

PADS = ("L1", "R1", "L2", "R2", "M")
TOUCH_SATURATED = 0x3FFFFF  # as in walk_wired.py: a count above this means the 24 bytes are shifted by one


def touch_decode(raw):
    """(seq, L1, R1, L2, R2, M) from the 24 bytes, trying both alignments, as walk_wired.touch_decode does."""
    for block in (raw, raw[1:] + b"\0"):
        b = struct.unpack("<6I", block)
        if max(b[1:]) <= TOUCH_SATURATED:
            return b
    return None


def bar(peak, width=12):
    db = 20 * math.log10(max(peak, 1) / 32768.0)
    filled = max(0, min(width, int(round((db + 72) / 72 * width))))
    return "#" * filled + "." * (width - filled) + f" {db:6.1f} dB"


def open_port(path):
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY)
    attrs = termios.tcgetattr(fd)
    attrs[0] = attrs[1] = attrs[3] = 0                      # raw: no input, output or line processing
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[6][termios.VMIN], attrs[6][termios.VTIME] = 0, 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    return fd


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    fd = open_port(sys.argv[1])
    buf, status, touch, touch_lines, errors, last_error = b"", {}, None, 0, 0, ""
    next_ask = next_draw = 0.0
    try:
        while True:
            now = time.monotonic()
            if now >= next_ask:
                os.write(fd, b"?\n")
                next_ask = now + 0.25
            if select.select([fd], [], [], 0.05)[0]:
                chunk = os.read(fd, 4096)
                if not chunk:
                    sys.exit("\nport closed")
                buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                line = raw.decode("ascii", "replace").strip()
                if line.startswith("T ") and len(line) == 50:
                    touch_lines += 1
                    try:
                        touch = touch_decode(bytes.fromhex(line[2:]))
                    except ValueError:
                        touch = None
                elif line.startswith("E "):
                    errors += 1
                    last_error = line[2:]
                elif line.startswith("S "):
                    status = dict(kv.split("=", 1) for kv in line[2:].split() if "=" in kv)
                elif line.startswith("#"):
                    last_error = line
            if now >= next_draw:
                next_draw = now + 0.1
                peaks = [int(v) for v in status.get("peak", "0,0,0").split(",")]
                mic = "  ".join(f"{n} {bar(p)}" for n, p in zip(("L", "R", "B"), peaks))
                pads = ("  ".join(f"{n} {v:6d}" for n, v in zip(PADS, touch[1:])) + f"  seq {touch[0]}") if touch else "touch: no block yet"
                tail = (f"  lines {touch_lines} err {errors} {last_error}"
                        f"  underrun {status.get('underrun', '?')} drop {status.get('drop', '?')} repeat {status.get('repeat', '?')}")
                sys.stdout.write("\r\033[K" + mic + " | " + pads + tail)
                sys.stdout.flush()
    except KeyboardInterrupt:
        print()
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
