"""Yaw about gravity (gyro integrated, as turn_test.yaw_rate) across run 3's face states, and approach's own yaw formula."""
import json, math, sys
sys.path.insert(0, '.')
import approach as ap
W = [(1793586537.5, 1793586539.7, -41, -4), (1793586540.8, 1793586542.4, -22, -3), (1793586543.5, 1793586545.2, -28, None)]
rows = []
for l in open(sys.argv[1]):
    if l.startswith('{'):
        try:
            r = json.loads(l)
            if W[0][0] - 1 <= r['t'] <= W[-1][1] + 1 and r.get('gyro') and r.get('gb'): rows.append(r)
        except ValueError: pass
def rate(r):
    g, gb = r['gyro_body'], r['gb']
    n = math.sqrt(sum(x*x for x in gb)) or 1.0
    return -sum(a*b for a, b in zip(g, gb)) / n
print('gyro', rows[0]['gyro'], 'gyro_body', rows[0]['gyro_body'], 'gb', rows[0]['gb'])
for a, b, b0, b1 in W:
    y = 0.0
    R = [r for r in rows if a <= r['t'] <= b]
    for p, q in zip(R, R[1:]):
        y += rate(q) * (q['t'] - p['t'])
    print(f"face {a:.1f}-{b:.1f} ({b-a:.1f} s): yaw about gravity {math.degrees(y):+.1f} deg; bearing reported {b0} -> {b1}")
y = 0.0
for p, q in zip(rows, rows[1:]):
    y += rate(q) * (q['t'] - p['t'])
    if int(q['t']*2) != int(p['t']*2):
        print(round(q['t']-W[0][0],1), 'yaw', round(math.degrees(y),1), 'vth', (q.get('cmd') or {}).get('vtheta'), 'turn', q.get('turn'))
