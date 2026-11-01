#!/usr/bin/env python3
"""Record the duck's own motion noise for the name spotter: the four head-microphone channels while the body turns in
place both ways and the head sweeps, with nobody talking. Round 4 of the spotter mixes these 2 s chunks into its
training background so it still hears "Mochi" while the duck turns or searches (2026-10-31 20:21: calls spoken during
a body turn scored under 0.1).

Run on the A7Z with the brain in walk mode at zero command and namecall stopped (one reader on the card):
  ~/.venvs/duck-policy/bin/python record_motion_noise.py [--out ~/duck-logs/motion_noise_<time>.raw]
Motion: only the robot-tested commands (vtheta +-0.3 rad/s in walk mode, head yaw within +-0.8 rad); the zero
command is written back at the end and on any error. Writes <out>.json with each segment's start and end (s from the
recording start) and kind (still, turn_left, turn_right, head_sweep).
"""
import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import namecall as nc  # noqa: E402

DEFAULT_HEAD = {"neck_pitch": 0.349, "head_pitch": 0.349, "head_yaw": 0.0, "head_roll": 0.0}
PLAN = (("still", 4.0, 0.0, None), ("turn_left", 12.0, 0.3, None), ("still", 3.0, 0.0, None),
        ("turn_right", 12.0, -0.3, None), ("still", 3.0, 0.0, None), ("head_sweep", 8.0, 0.0, 0.8),
        ("turn_left", 8.0, 0.3, 0.8), ("turn_right", 8.0, -0.3, 0.8), ("still", 4.0, 0.0, None))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.expanduser(time.strftime("~/duck-logs/motion_noise_%Y%m%d-%H%M%S.raw")))
    ap.add_argument("--card", default="hw:CARD=sndi2s0,0")
    a = ap.parse_args()
    gate = nc.BrainGate()
    st = gate.state()
    if not st["ok"] or st["mode"] != "walk":
        sys.exit(f"record_motion_noise: refused, brain not in walk at zero command: {st.get('why') or st.get('mode')}")
    w = nc.CmdWriter()
    if not w.claimable():
        sys.exit("record_motion_noise: refused, the control file belongs to another program")
    rec = subprocess.Popen(["arecord", "-q", "-D", a.card, "-c", "4", "-r", "48000", "-f", "S32_LE", "-t", "raw", a.out])
    t0 = time.time()
    segs = []
    try:
        time.sleep(1.0)
        for kind, dur, vth, sweep in PLAN:
            s0 = time.time() - t0
            end = time.time() + dur
            k = 0
            while time.time() < end:
                head = dict(DEFAULT_HEAD)
                if sweep:
                    head["head_yaw"] = sweep if (k // 35) % 2 == 0 else -sweep     # 0.7 s per side
                if not w.write(head, vtheta=vth, for_s=1.0 if vth else None):
                    raise RuntimeError(f"control file taken by another program: {w.taken}")
                k += 1
                time.sleep(0.02)
            segs.append(dict(kind=kind, start_s=round(s0, 2), end_s=round(time.time() - t0, 2), vtheta=vth, head_sweep=sweep))
            print(json.dumps(segs[-1]), flush=True)
    finally:
        w.write(DEFAULT_HEAD)
        time.sleep(1.0)
        rec.terminate()
        rec.wait()
        json.dump(dict(file=a.out, t0=t0, segments=segs), open(a.out + ".json", "w"), indent=1)
        print("wrote", a.out, a.out + ".json")


if __name__ == "__main__":
    main()
