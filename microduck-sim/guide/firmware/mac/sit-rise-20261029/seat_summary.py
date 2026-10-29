"""Per-label summary of the fake_pi runner-path seats in results/fakepi_seats.jsonl: runs, falls, stand-ups the brain
called up ("sit: up after"), give-ups ("sit: RISE FAILED") and the final body gravity of each seat's brain.out.
Mac mini.

  python seat_summary.py [~/sims/sit-rise-20261029]
"""
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEATS = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/sims/sit-rise-20261029")

rows = [json.loads(l) for l in open(os.path.join(HERE, "results", "fakepi_seats.jsonl"))]
by = collections.OrderedDict()
for r in rows:
    by.setdefault(r["label"], []).append(r)
for label, rs in by.items():
    falls = sum(bool(r.get("fell")) for r in rs)
    up = fail = 0
    ends = []
    for d in sorted(glob.glob(os.path.join(SEATS, f"seat-{label}-*"))):
        out = open(os.path.join(d, "brain.out")).read().splitlines() if os.path.exists(os.path.join(d, "brain.out")) else []
        up += sum("sit: up after" in l for l in out)
        fail += sum("RISE FAILED" in l for l in out)
        last = [l for l in out if "body g [" in l]
        ends.append(last[-1].split()[0] + " g" + last[-1].split("body g")[1] if last else "no log")
    print(f"{label}: {len(rs)} runs, {falls} fell, brain 'up' {up}, 'RISE FAILED' {fail}, "
          f"compensation {rs[0].get('compensation')}, to_stand {rs[0].get('to_stand')}")
    for e in ends:
        print("   end", e)
