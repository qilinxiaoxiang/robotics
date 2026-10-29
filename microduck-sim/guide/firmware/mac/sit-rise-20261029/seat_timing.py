"""Timing of one fakepi_seat.py seat: fake_pi physics loops per wall second (each loop = 20 ms of sim time) and the
brain's ticks, around the rise. Prints a few lines; Mac mini.

  python seat_timing.py SEAT_DIR
"""
import json
import os
import sys

d = sys.argv[1]
tr = [json.loads(l) for l in open(os.path.join(d, "trace.jsonl"))]
rows = [json.loads(l) for l in open(os.path.join(d, "brain_log.jsonl")) if l.startswith("{")]
print("brain row keys:", sorted(rows[0].keys()))
t0w = os.path.getmtime(os.path.join(d, "trace.jsonl")) - tr[-1]["t"]
rise = next(r["t"] for r in rows if r.get("sit_phase") == "rise")
for name, lo, hi in (("standing", rise - 12.0, rise - 9.0), ("seated", rise - 3.0, rise), ("rise", rise, rise + 2.0)):
    loops = [r for r in tr if lo <= r["t"] + t0w < hi]
    ticks = [r for r in rows if lo <= r["t"] < hi]
    gaps = [b["t"] - a["t"] for a, b in zip(loops, loops[1:])]
    print(f"{name}: physics loops {len(loops) / (hi - lo):.1f}/s (sim {len(loops) * 0.02 / (hi - lo):.2f} x real), "
          f"max loop gap {max(gaps) * 1000:.0f} ms; brain ticks {len(ticks) / (hi - lo):.1f}/s, "
          f"loop_ms {sorted(r.get('loop_ms', 0) for r in ticks)[len(ticks) // 2] if ticks else None}, "
          f"applied_age median {sorted(r.get('applied_age') or 0 for r in ticks)[len(ticks) // 2] * 1000:.0f} ms")
