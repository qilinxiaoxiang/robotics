"""Per in-place spin: heading gained when the command stops against what is left once standing still again, and the hip yaws."""
import json, math, sys
rows = []
for f in sys.argv[1:]:
    for l in open(f):
        if l.startswith('{'):
            try:
                r = json.loads(l)
                if r.get('gb') and r.get('gyro_body'): rows.append(r)
            except ValueError: pass
rows.sort(key=lambda r: r['t'])
def rate(r):
    g, gb = r['gyro_body'], r['gb']; n = math.sqrt(sum(x*x for x in gb)) or 1.0
    return -sum(a*b for a, b in zip(g, gb)) / n
Y = [0.0]
for p, q in zip(rows, rows[1:]):
    Y.append(Y[-1] + rate(q) * min(q['t']-p['t'], 0.1))
i = 0
while i < len(rows):
    c = rows[i].get('cmd') or {}
    if c.get('vx') == 0 and abs(c.get('vtheta') or 0) > 0.05:
        j = i
        while j+1 < len(rows) and (rows[j+1].get('cmd') or {}).get('vtheta') and rows[j+1]['t']-rows[j]['t'] < 0.2: j += 1
        k = j
        while k+1 < len(rows) and rows[k+1]['t'] < rows[j]['t'] + 2.0: k += 1
        peak = min(Y[i:k+1]) if c['vtheta'] < 0 else max(Y[i:k+1])
        print(f"t {rows[i]['t']%1000:7.1f} dur {rows[j]['t']-rows[i]['t']:4.1f} vth {c['vtheta']:+.1f} at stop {math.degrees(Y[j]-Y[i]):+6.1f} peak {math.degrees(peak-Y[i]):+6.1f} settled {math.degrees(Y[k]-Y[i]):+6.1f} deg; hipY at stop R {rows[j]['q'][4]:+.2f} L {rows[j]['q'][9]:+.2f}")
        i = k
    i += 1
