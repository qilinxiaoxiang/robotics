"""Long right and left spins from spin_induce: turn command, net yaw, hip yaw, per-joint range and tracking."""
import json, math, sys
W = {'R': (1793586967.64, 1793586975.79), 'L': (1793586979.79, 1793586987.91), 'Rhead': (1793586991.92, 1793586999.99)}
rows = []
for l in open(sys.argv[1]):
    if l.startswith('{'):
        try:
            r = json.loads(l)
            if r.get('gb') and r.get('gyro_body'): rows.append(r)
        except ValueError: pass
N = ['r_ank','r_knee','r_hipP','r_hipR','r_hipY','l_ank','l_knee','l_hipP','l_hipR','l_hipY']
def rate(r):
    g, gb = r['gyro_body'], r['gb']; n = math.sqrt(sum(x*x for x in gb)) or 1.0
    return -sum(a*b for a, b in zip(g, gb)) / n
for k, (a, b) in W.items():
    R = [r for r in rows if a <= r['t'] <= b]
    S = [r for r in R if (r.get('cmd') or {}).get('vtheta')]
    y = 0.0; print('---', k, len(R), 'rows;', len(S), 'spin')
    for p, q in zip(R, R[1:]):
        y += rate(q) * (q['t'] - p['t'])
        if int(q['t']) != int(p['t']):
            t = [r.get('turn') for r in R if int(r['t']) == int(p['t']) and r.get('turn') is not None]
            print(f" {q['t']-a:4.1f} yaw {math.degrees(y):+6.1f} turn mean {sum(t)/max(1,len(t)):+.2f} min {min(t or [0]):+.2f} max {max(t or [0]):+.2f} hipY R {q['q'][4]:+.2f} L {q['q'][9]:+.2f} trim {q.get('yaw_trim')}")
    for i, n in enumerate(N):
        v = [r['q'][i] for r in S[50:]]
        print(f"   {n} mean {sum(v)/len(v):+.2f} range {max(v)-min(v):.2f}", end='')
    print()
    print('   tilt gb mean', [round(sum(r['gb'][i] for r in S)/len(S),3) for i in (0,1)], 'cmd sample', S[-1].get('cmd'))
