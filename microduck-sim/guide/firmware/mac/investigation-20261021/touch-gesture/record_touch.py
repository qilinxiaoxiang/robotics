"""Record the five head pads at 50 Hz on the A7Z and label touches live (draft, 2026-10-21; proposed home
microduck-sim/guide/extension-20261015-touch/gesture/record_touch.py).

    python3 record_touch.py --out ~/duck-logs/touch_<session>.jsonl [--performer shawn]

Live view first (one bar per pad, the same drawing as touch_live_a7z.py), then labels by key while recording:
  s = stroke, p = pat (relaxed), a = pat (angry), c = carry grip (M+L1+R1 held), n = no-touch segment
  key once at the start of a touch, space at its end; q quits.
Every block is one row {"t": unix s, "seq", "v": [L1, R1, L2, R2, M]}; a label row {"t", "label", "event": "start"|"end",
"performer"} is written at each key. The brain's tick log (acc, gyro_body, q, action) is joined offline by `t`
(features.py), so this script never touches the servo bus or the IMU.
Reads /dev/i2c-N of TWI0 (zz-duck-twi0-touch.dtbo) like touch_live_a7z.py; it refuses to run without that bus
(bit-banged reads cost tens of ms and would skew the timing).
"""
import argparse
import fcntl
import glob
import json
import os
import select
import struct
import sys
import termios
import time
import tty

PADS = ['L1', 'R1', 'L2', 'R2', 'M']
FULL, ADDR, PERIOD, SATURATED = 2000, 0x2A, 0.02, 0x3FFFFF
KEYS = {'s': 'stroke', 'p': 'pat_relaxed', 'a': 'pat_angry', 'c': 'carry_grip', 'n': 'none'}


def kernel_bus():
    for n in glob.glob('/sys/bus/i2c/devices/i2c-*/of_node'):
        if os.path.realpath(n).endswith('/twi@2510000'):
            return '/dev/' + n.split('/')[-2]
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--performer', default='shawn')
    args = ap.parse_args()
    dev = kernel_bus()
    if not dev:
        sys.exit('no TWI0 kernel bus on pins 29/31: install zz-duck-twi0-touch.dtbo first (CURRENT-STATE a7z_touch_bus)')
    bus = os.open(dev, os.O_RDWR)
    fcntl.ioctl(bus, 0x0703, ADDR)
    out = open(args.out, 'a')
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    start_v, last_seq, ok, bad, active = None, None, 0, 0, None
    print('\033[2J')
    try:
        next_t = time.monotonic()
        while True:
            try:
                b = struct.unpack('<6I', os.read(bus, 24))
            except OSError:
                b = None
            now = time.time()
            if b is None or max(b[1:]) > SATURATED or (last_seq is not None and not 0 < b[0] - last_seq < 500):
                bad += 1
                last_seq = None if b is None else last_seq
            else:
                last_seq, v = b[0], list(b[1:])
                ok += 1
                start_v = start_v or v
                out.write(json.dumps({'t': round(now, 3), 'seq': b[0], 'v': v}, separators=(',', ':')) + '\n')
                lines = ['\033[H按铜箔看条；键 s=stroke p=pat a=angry c=carry n=none 开始，空格结束，q 退出\033[K', '\033[K']
                for name, cur, s0 in zip(PADS, v, start_v):
                    d = cur - s0
                    n = max(0, min(40, round(40 * d / FULL)))
                    lines.append(f'{name:>2}  {cur:7d}  {d:+6d}  {"█" * n}\033[K')
                lines.append(f'\033[K\n标签：{active or "（无）"}   读到 {ok} 丢 {bad}\033[J')
                print('\n'.join(lines), flush=True)
            if select.select([fd], [], [], 0)[0]:
                k = sys.stdin.read(1)
                if k == 'q':
                    break
                if k in KEYS and active is None:
                    active = KEYS[k]
                    out.write(json.dumps({'t': round(now, 3), 'label': active, 'event': 'start', 'performer': args.performer}) + '\n')
                elif k == ' ' and active is not None:
                    out.write(json.dumps({'t': round(now, 3), 'label': active, 'event': 'end', 'performer': args.performer}) + '\n')
                    active = None
                out.flush()
            next_t += PERIOD
            time.sleep(max(0.0, next_t - time.monotonic()))
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        out.close()
        print()


if __name__ == '__main__':
    main()
