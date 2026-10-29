"""Goal and measured ticks of the leg servos every EVERY ticks after the brain enters the open-loop stand from walk mode,
with the body tilt. Mac mini.

  python stand_goals.py TICKS.jsonl [SECONDS] [EVERY]
"""
import json
import math
import sys

rows = [json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")]
span = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
every = int(sys.argv[3]) if len(sys.argv) > 3 else 5
i = next(k for k, r in enumerate(rows) if k and r.get("mode") == "stand" and rows[k - 1].get("mode") == "walk")
t0 = rows[i]["t"]
print("ids 1-10 (legs): goal/measured ticks")
for r in rows[i - 1::every]:
    if r["t"] - t0 > span:
        break
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, -r["gb"][2]))))
    g = r.get("goal_tick") or {}
    cells = " ".join(f"{g.get(str(n), '-')}/{r['pos_tick'][n - 1]}" for n in range(1, 11))
    print(f"{r['t']:6.2f} {r['mode']:5s} kp {r.get('kp')} tilt {tilt:5.1f} gy {r['gyro_body'][1]:+.2f} | {cells}")
