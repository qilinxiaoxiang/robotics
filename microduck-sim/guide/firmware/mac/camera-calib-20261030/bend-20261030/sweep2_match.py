"""Repair the joint states of sweep2/rows.json and write sweep2/rows_matched.json.

In sweep2 the brain-log tail that gpsweep.py read advanced only once per phase: every row of a phase window carries
the state logged at the END of the previous window (t_cap - t_state up to 6.9 s), i.e. the previous hold's pose
(check: the rows of the 0.08 window hold neck -1.335 / head -0.074 / tilt 27.1 deg, which sweep2.out prints as the
0.05 hold). So the hold pose of window k is the state stored in the rows of window k+1. Windows come from the
cumulative frame counts in sweep2.out (62, 122, 174, 224, 262, 298, 351). The last window (phase 1.0: rise then
standing) has no stored full state and is left without q.

Within a window the first seconds are the move into the hold; frames are marked static when the mean absolute
picture difference to the previous frame is below a threshold, and only the last stretch of static frames is kept
as `use`.
"""
import json
import os

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
S2 = os.path.join(HERE, "sweep2")
WINDOWS = [(0.05, 0, 62), (0.08, 62, 122), (0.12, 122, 174), (0.18, 174, 224), (0.25, 224, 262), (0.33, 262, 298),
           (1.0, 298, 351)]
DIFF_STATIC = 6.0   # mean |frame - previous| (8-bit, 640x360 gray) below this = no motion


def main():
    rows = json.load(open(os.path.join(S2, "rows.json")))
    out = []
    prev = None
    diffs = {}
    for r in rows:
        im = cv2.imread(os.path.join(S2, f"{r['name']}.png"), cv2.IMREAD_GRAYSCALE)
        diffs[r["name"]] = float(np.abs(im.astype(int) - prev).mean()) if prev is not None else 99.0
        prev = im.astype(int)
    for k, (phase, a, b) in enumerate(WINDOWS):
        if k + 1 < len(WINDOWS):
            src = rows[WINDOWS[k + 1][1] + 1]        # second row of the next window (first row may be the switch)
            q, gb, t_state = src["q"], src["gb"], src["t_state"]
        else:
            q, gb, t_state = None, None, None
        names = [r["name"] for r in rows[a:b]]
        static = [diffs[n] < DIFF_STATIC for n in names]
        # the last run of static frames in the window
        use = [False] * len(names)
        i = len(names) - 1
        while i >= 0 and static[i]:
            use[i] = True
            i -= 1
        for n, st, us, r in zip(names, static, use, rows[a:b]):
            out.append(dict(name=n, phase=phase, cmd_phase=r["cmd_phase"], t_cap=r["t_cap"], q=q, gb=gb,
                            state_t=t_state, state_source="next window's stored state (previous-hold lag)",
                            diff=round(diffs[n], 2), static=bool(st), use=bool(us and q is not None)))
        print(f"phase {phase}: rows {a}-{b-1} ({names[0]}..{names[-1]}), state neck {q and round(q['neck_pitch'],3)} head "
              f"{q and round(q['head_pitch'],3)} gb {gb}, static {sum(static)}, use {sum(use)} "
              f"({[n for n, u in zip(names, use) if u][:1]}..)")
    json.dump(out, open(os.path.join(S2, "rows_matched.json"), "w"), indent=0)
    print("wrote", os.path.join(S2, "rows_matched.json"))


if __name__ == "__main__":
    main()
