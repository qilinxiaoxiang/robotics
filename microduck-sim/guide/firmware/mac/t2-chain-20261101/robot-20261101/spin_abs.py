"""Cumulative yaw about gravity through a log slice, printed each second while a spin is commanded."""
import json, math, sys
rows = []
for l in open(sys.argv[1]):
    if l.startswith('{'):
        try:
            r = json.loads(l)
            if r.get('gb') and r.get('gyro_body'): rows.append(r)
        except ValueError: pass
def rate(r):
    g, gb = r['gyro_body'], r['gb']; n = math.sqrt(sum(x*x for x in gb)) or 1.0
    return -sum(a*b for a, b in zip(g, gb)) / n
y = 0.0; t0 = rows[0]['t']
for p, q in zip(rows, rows[1:]):
    y += rate(q) * min(q['t'] - p['t'], 0.1)
    if int(q['t']) != int(p['t']):
        print(f"{q['t']-t0:5.0f} yaw {math.degrees(y):+7.1f} vth {(q.get('cmd') or {}).get('vtheta')} turn {q.get('turn')}")
