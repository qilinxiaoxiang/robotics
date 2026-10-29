"""Side by side, tick by tick from the rise start: the brain's view in an in-process brain_sim_check tick log and in a
fake_pi seat's walk_brain log (right knee q, dq, body gravity x, gyro y, right-knee action). Mac mini.

  python compare_rise.py INPROC_TICKS.jsonl SEAT_DIR/brain_log.jsonl [N]
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
from walk_brain import NAMES, OBSERVATION_DOF_ORDER  # noqa: E402

RK = NAMES.index("right_knee")
AK = list(OBSERVATION_DOF_ORDER).index("right_knee")


def rise_rows(path):
    rows = [json.loads(l) for l in open(path) if l.startswith("{")]
    i = next(k for k, r in enumerate(rows) if r.get("sit_phase") == "rise")
    return rows[i - 3:]


n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
A, B = rise_rows(sys.argv[1]), rise_rows(sys.argv[2])
print("tick | in-process: q dq gbx gyy act | fake_pi: q dq gbx gyy act")
for k in range(min(n, len(A), len(B))):
    f = lambda r: (f"{r['q'][RK]:+.3f} {r['dq'][RK]:+6.2f} {r['gb'][0]:+.3f} {r['gyro_body'][1]:+5.2f} "
                   f"{(r['action'] or [0] * 14)[AK]:+.3f} {r.get('sit_phase', '-')[:4]}")
    print(f"{k - 3:4d} | {f(A[k])} | {f(B[k])}")
