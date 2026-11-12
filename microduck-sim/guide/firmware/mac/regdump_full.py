"""Read the whole control table (addresses 0-146) of every leg and head servo, read-only, and print it as JSON.
Run only while walk_wired.py is stopped (it owns the port); torque stays as it is, nothing is written.

  on the A7Z: ~/.venvs/duck-policy/bin/python regdump_full.py --port /dev/ttyAS2 --baud 500000 > regs.json
"""
import argparse
import json
import time

from walk_wired import IDS, NAMES, Link

ap = argparse.ArgumentParser()
ap.add_argument("--port", required=True)
ap.add_argument("--baud", type=int, default=1_000_000)
a = ap.parse_args()
link = Link(a.port, a.baud)
time.sleep(0.3)
table = {i: {} for i in IDS}
for start in range(0, 147, 21):  # seven 21-byte blocks
    got = {}
    for _ in range(5):
        got.update(link.sync_read(start, 21, [i for i in IDS if i not in got], timeout=0.05, allow_alert=True))
        if len(got) == len(IDS):
            break
    for i, b in got.items():
        for k, v in enumerate(b):
            table[i][start + k] = v
print(json.dumps({"t": time.time(), "names": dict(zip(map(str, IDS), NAMES)),
                  "table": {str(i): [table[i].get(k) for k in range(147)] for i in IDS}}))
