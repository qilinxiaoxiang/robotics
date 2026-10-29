"""Joint angles and body gravity at the first tick of the open-loop stand ({"mode": "stand"}) entered from walk mode in
two or more brain_sim_check tick logs, and the tilt 1 s and 2 s later. Mac mini.

  python stand_entry.py TICKS_A.jsonl TICKS_B.jsonl ...
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
from walk_brain import NAMES  # noqa: E402


def tilt(r):
    return math.degrees(math.acos(max(-1.0, min(1.0, -r["gb"][2]))))


cols = []
for path in sys.argv[1:]:
    rows = [json.loads(l) for l in open(path) if l.startswith("{")]
    i = next(k for k, r in enumerate(rows) if k and r.get("mode") == "stand" and rows[k - 1].get("mode") == "walk")
    r = rows[i]
    later = [rows[min(len(rows) - 1, i + n)] for n in (25, 50, 100)]
    cols.append((os.path.basename(path), r, later))
print("joint          " + "  ".join(f"{c[0][:18]:>18s}" for c in cols))
for k, n in enumerate(NAMES):
    print(f"{n:15s}" + "  ".join(f"{c[1]['q'][k]:+18.3f}" for c in cols))
for key in ("gb", "gyro_body", "t"):
    print(f"{key:15s}" + "  ".join(f"{str([round(x, 3) for x in c[1][key]] if isinstance(c[1][key], list) else round(c[1][key], 2)):>18s}"
                                   for c in cols))
for j, s in enumerate(("+0.5 s", "+1 s", "+2 s")):
    print(f"tilt {s:9s} " + "  ".join(f"{tilt(c[2][j]):18.1f}" for c in cols))
print("keys", sorted(cols[0][1]))
