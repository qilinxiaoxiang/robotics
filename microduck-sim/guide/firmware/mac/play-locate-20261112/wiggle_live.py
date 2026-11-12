#!/usr/bin/env python3
"""Live wiggle test: does a part move while its servo's encoder stays still? (play-locate 2026-11-12)

Run in the Mac's Terminal panel while the brain runs on the A7Z with torque on (stand mode, from the app). Hold the
duck, then push one part by hand (the left foot's toe up and down, then the right foot, then the head forward/back
and side to side). The screen updates about 10 times a second with each joint's encoder (ticks from where it was when
you started), its goal, and the trunk tilt from the IMU:

  - the part moves but its row stays within +-1 tick: the play is past the servo (horn, screws, bracket, the arcs
    between the yellow base and the black neck, the foot sleeve);
  - the row moves with your push and springs back: the servo itself gives (gear play or its soft position loop).

Reading only: it tails the brain's own log over ssh (nothing is parsed on the A7Z, nothing is sent to the servos, the
brain is not restarted). Ctrl-C ends it and prints, per joint, how far its encoder moved; every sample is saved to
~/duck-walks/wiggle-<time>.jsonl on this Mac.

  python3 wiggle_live.py                 # the newest brain log on the A7Z
  python3 wiggle_live.py --log /home/radxa/duck-logs/duck_wired_log_app1112-002642.jsonl
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time

NAMES = ["right_ankle", "right_knee", "right_hip_pitch", "right_hip_roll", "right_hip_yaw", "left_ankle", "left_knee",
         "left_hip_pitch", "left_hip_roll", "left_hip_yaw", "head_pitch", "neck_pitch", "head_yaw", "head_roll"]
IDS = list(range(1, 15))  # pos_tick is in servo-ID order; goal_tick is {servo ID: tick}
SHOW = ["left_ankle", "right_ankle", "left_knee", "right_knee", "left_hip_pitch", "right_hip_pitch",
        "neck_pitch", "head_pitch", "head_yaw", "head_roll"]
TICK_DEG = 360 / 4096


def newest_log():
    out = subprocess.run(["ssh", "-o", "ConnectTimeout=8", "a7z", "ls -t /home/radxa/duck-logs/duck_wired_log_*.jsonl"],
                         capture_output=True, text=True, timeout=20).stdout.split()
    if not out:
        sys.exit("no brain log on the A7Z (is it on the network?)")
    return out[0]


def tilt(gb):
    return math.degrees(math.atan2(gb[0], -gb[2])), math.degrees(math.atan2(-gb[1], -gb[2]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=None)
    a = ap.parse_args()
    log = a.log or newest_log()
    save = os.path.expanduser(time.strftime("~/duck-walks/wiggle-%Y%m%d-%H%M%S.jsonl"))
    os.makedirs(os.path.dirname(save), exist_ok=True)
    p = subprocess.Popen(["ssh", "-o", "ConnectTimeout=8", "a7z", f"tail -n 0 -F {log}"], stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True, bufsize=1)
    ref, lo, hi, last_draw = None, {}, {}, 0.0
    f = open(save, "w")
    print(f"reading {log} (Ctrl-C to stop) ...", flush=True)
    try:
        for line in p.stdout:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            pos = r.get("pos_tick")
            if not pos or None in pos:
                continue
            cur = dict(zip(NAMES, pos))
            goal = {n: (r.get("goal_tick") or {}).get(str(i)) for i, n in zip(IDS, NAMES)}
            if ref is None:
                ref = dict(cur)
            for n in NAMES:
                d = cur[n] - ref[n]
                lo[n], hi[n] = min(lo.get(n, d), d), max(hi.get(n, d), d)
            f.write(json.dumps(dict(t=r["t"], mode=r.get("mode"), torque=r.get("torque"), pos=cur, goal=goal,
                                    gb=r.get("gb"))) + "\n")
            now = time.time()
            if now - last_draw < 0.1:
                continue
            last_draw = now
            out = ["\033[H\033[J"]
            if not r.get("torque"):
                out.append("!! TORQUE OFF (mode %s): the joints follow your hand; turn on stand in the app first\n\n" % r.get("mode"))
            else:
                out.append(f"mode {r.get('mode')}, torque on.  Push one part, watch its row.\n\n")
            gb = r.get("gb")
            if gb and r.get("imu_valid"):
                pt, rl = tilt(gb)
                out.append(f"trunk pitch {pt:+6.1f} deg   roll {rl:+6.1f} deg\n\n")
            out.append("joint              now (ticks from start)   deg     goal-pos   moved range (deg)\n")
            for n in SHOW:
                d = cur[n] - ref[n]
                g = goal[n]
                gp = "" if g is None else f"{g - cur[n]:+5d}"
                bar = ("#" * min(30, abs(d))) if d else "|"
                out.append(f"{n:18s} {d:+6d} {bar:30s} {d * TICK_DEG:+6.2f}   {gp:>6s}     "
                           f"{lo[n] * TICK_DEG:+.2f} .. {hi[n] * TICK_DEG:+.2f}\n")
            out.append("\n(1 tick = 0.088 deg; +-1 tick is encoder noise)\n")
            sys.stdout.write("".join(out))
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        p.terminate()
        f.close()
    print("\nencoder range per joint while you pushed (deg):")
    for n in SHOW:
        if n in lo:
            print(f"  {n:18s} {lo[n] * TICK_DEG:+.2f} .. {hi[n] * TICK_DEG:+.2f}  ({(hi[n] - lo[n])} ticks)")
    print(f"samples saved to {save}")


if __name__ == "__main__":
    main()
