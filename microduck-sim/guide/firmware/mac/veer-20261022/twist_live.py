"""Live readout for veer step 3 (twist each foot with torque on): how far each leg joint is pushed off its goal.

  ssh -t a7z 'python3 ~/duck/twist_live.py'     (reads the newest ~/duck-logs/duck_wired_log_*.jsonl; read-only)

One line, refreshed 5 times a second: present minus goal in deg for the ankles, hip rolls and hip yaws, and the
servo current in mA. A joint that moves under finger force while its error stays near 0 is not where the play is:
the play then sits in the printed parts or horn fit, which the encoders cannot see.
"""
import glob
import json
import os
import sys
import time

TICK_DEG = 360 / 4096
JOINTS = (("L_ankle", 6), ("L_hroll", 9), ("L_hyaw", 10), ("R_ankle", 1), ("R_hroll", 4), ("R_hyaw", 5))


def main():
    path = max(glob.glob(os.path.expanduser("~/duck-logs/duck_wired_log_*.jsonl")), key=os.path.getmtime)
    print(f"{path}\n" + "  ".join(f"{n:>13s}" for n, _ in JOINTS) + "   (err deg / mA)", flush=True)
    f = open(path)
    f.seek(0, 2)
    last = 0.0
    while True:
        line = f.readline()
        if not line:
            time.sleep(0.02)
            continue
        if time.time() - last < 0.2:
            continue
        try:
            r = json.loads(line)
            pos, goal, cur = r["pos_tick"], r["goal_tick"], r.get("cur_ma") or [0] * 14
        except (ValueError, KeyError, TypeError):
            continue
        last = time.time()
        cells = [f"{(pos[i - 1] - goal[str(i)]) * TICK_DEG:+6.1f}/{cur[i - 1]:+5d}" for _, i in JOINTS]
        sys.stdout.write("\r" + "  ".join(f"{c:>13s}" for c in cells) + f"  {r.get('mode', '?'):7s}")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
