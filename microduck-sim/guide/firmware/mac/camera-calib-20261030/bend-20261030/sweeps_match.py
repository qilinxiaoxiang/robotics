"""Repair the joint states of sweep2/rows.json and sweep3/rows.json and write rows_matched.json beside each.

In these sweeps the brain-log tail that gpsweep.py read advanced only once per phase: every row of a phase window
carries the state logged at the END of the previous window (t_cap - t_state up to 6.9 s), i.e. the previous hold's
pose. Check: the rows of sweep2's 0.08 window hold neck -1.335 / head -0.074 / tilt 27.1 deg, which sweep2.out
prints as the 0.05 hold, and the pictures of the 0.05 window already show the bow while its rows still hold the
standing state. So the hold pose of window k is the state stored in the rows of window k+1. Windows come from the
cumulative "frames N" counts in sweepN.out. The last window (phase 1.0: rise then standing) has no stored full
state and is left without q.

Within a window the first seconds are the move into the hold; frames are marked static when the mean absolute
picture difference to the previous frame is below DIFF_STATIC, and only the last stretch of static frames is kept
as `use`.

usage: python sweeps_match.py sweep2 sweep3
"""
import json
import os
import re
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DIFF_STATIC = 6.0   # mean |frame - previous| (8-bit, 640x360 gray) below this = no motion


def windows_from_out(path):
    ends = [(float(m.group(1)), int(m.group(2)))
            for m in re.finditer(r"phase ([0-9.]+) held:.*?frames (\d+)", open(path).read())]
    out, a = [], 0
    for phase, b in ends:
        out.append((phase, a, b))
        a = b
    return out


def match(sweep):
    d = os.path.join(HERE, sweep)
    rows = json.load(open(os.path.join(d, "rows.json")))
    windows = windows_from_out(os.path.join(d, f"{sweep}.out"))
    assert windows[-1][2] == len(rows), (windows, len(rows))
    out = []
    prev = None
    diffs = {}
    for r in rows:
        im = cv2.imread(os.path.join(d, f"{r['name']}.png"), cv2.IMREAD_GRAYSCALE).astype(int)
        diffs[r["name"]] = float(np.abs(im - prev).mean()) if prev is not None else 99.0
        prev = im
    for k, (phase, a, b) in enumerate(windows):
        if k + 1 < len(windows):
            src = rows[windows[k + 1][1] + 2]        # third row of the next window (the first rows may straddle the switch)
            q, gb, t_state = src["q"], src["gb"], src["t_state"]
        else:
            q, gb, t_state = None, None, None
        names = [r["name"] for r in rows[a:b]]
        static = [diffs[n] < DIFF_STATIC for n in names]
        use = [False] * len(names)
        i = len(names) - 1
        while i >= 0 and static[i]:
            use[i] = True
            i -= 1
        for n, st, us, r in zip(names, static, use, rows[a:b]):
            out.append(dict(name=n, sweep=sweep, phase=phase, cmd_phase=r["cmd_phase"], t_cap=r["t_cap"], q=q, gb=gb,
                            state_t=t_state, state_source="next window's stored state (previous-hold lag)",
                            diff=round(diffs[n], 2), static=bool(st), use=bool(us and q is not None)))
        print(f"{sweep} phase {phase}: rows {a}-{b-1} ({names[0]}..{names[-1]}), state neck {q and round(q['neck_pitch'],3)} "
              f"head {q and round(q['head_pitch'],3)} gb {gb}, static {sum(static)}, use {sum(use)} "
              f"(from {[n for n, u in zip(names, use) if u][:1]})")
    json.dump(out, open(os.path.join(d, "rows_matched.json"), "w"), indent=0)
    print("wrote", os.path.join(d, "rows_matched.json"))


if __name__ == "__main__":
    for s in sys.argv[1:] or ["sweep2", "sweep3"]:
        match(s)
