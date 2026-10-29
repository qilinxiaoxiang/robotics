"""Every joint, the body gravity, gyro and sample ages of the in-process and the fake_pi brain at the last seated tick
and 20 ticks into the rise. Mac mini.

  python compare_seat.py INPROC_TICKS.jsonl SEAT_DIR/brain_log.jsonl
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
from walk_brain import NAMES  # noqa: E402


def at(path):
    rows = [json.loads(l) for l in open(path) if l.startswith("{")]
    i = next(k for k, r in enumerate(rows) if r.get("sit_phase") == "rise")
    return rows[i - 1], rows[i + 20]


(a, a20), (b, b20) = at(sys.argv[1]), at(sys.argv[2])
print("joint            seat: in-proc fake_pi | rise+20: in-proc fake_pi")
for k, n in enumerate(NAMES):
    print(f"{n:16s} {a['q'][k]:+.3f} {b['q'][k]:+.3f} | {a20['q'][k]:+.3f} {b20['q'][k]:+.3f}")
for key in ("gb", "gyro_body", "head_cmd", "age_used", "imu_age", "applied_age", "policy"):
    print(key, a.get(key), "|", b.get(key))
print("in-proc keys", sorted(a))
print("fake_pi keys", sorted(b))
