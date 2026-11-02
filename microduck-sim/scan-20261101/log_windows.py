"""Summarize the brain log around the scan times: mode, still windows, joints, gravity."""
import sys, json, datetime as dt, numpy as np

S = sys.argv[1]
rows = []
for line in open(S + "/brain_slice.jsonl"):
    try:
        r = json.loads(line)
    except Exception:
        continue
    rows.append((r["t"], r.get("mode"), json.dumps(r.get("cmd"))[:90], r["q"], r["gb"], r.get("torque"), r.get("cur_ma"), r.get("servo_v"), r.get("goal_tick"), r.get("pos_tick")))
t = np.array([r[0] for r in rows])
q = np.array([r[3] for r in rows], float)
g = np.array([r[4] for r in rows], float)
loc = lambda x: dt.datetime.fromtimestamp(x).strftime("%H:%M:%S")
print("rows", len(rows), loc(t[0]), loc(t[-1]), "rate", round(len(t) / (t[-1] - t[0]), 1))
# mode segments
prev = None
for i, r in enumerate(rows):
    k = (r[1], r[2])
    if k != prev:
        print(loc(r[0]), r[1], r[2], "torque", r[5], "neck", q[i, 5].round(3), "head", q[i, 6].round(3), "gb", g[i].round(3))
        prev = k
# still segments (> 8 s with joint range < 0.03 rad over legs+neck+head), reported in 5-s blocks
print("--- 10 s blocks")
dtb = 10.0
for b in np.arange(t[0], t[-1], dtb):
    m = (t >= b) & (t < b + dtb)
    if m.sum() < 5:
        continue
    print(loc(b), "n", m.sum(), "range max", np.ptp(q[m], axis=0).max().round(3), "neck", q[m, 5].mean().round(3), "head", q[m, 6].mean().round(3), "gb", g[m].mean(0).round(3), rows[int(np.where(m)[0][0])][1])
np.savez(S + "/log.npz", t=t, q=q, g=g)
