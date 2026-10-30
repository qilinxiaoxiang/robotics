import json, math, sys, datetime
sys.path.insert(0, '.')
import walk_brain as wb
import numpy as np
rows = [json.loads(l) for l in open(sys.argv[1])]
N = wb.NAMES
print(N)
def tod(t): return datetime.datetime.fromtimestamp(t).strftime('%H:%M:%S')
t0s, t1s = sys.argv[2], sys.argv[3]
sel = [r for r in rows if t0s <= tod(r['t']) <= t1s]
ys = [wb.yaw_of(wb.body_quat(r['quat'])) for r in sel]
uw = np.unwrap(ys)
iy = [N.index(n) for n in N if 'hip_yaw' in n]
ik = [N.index(n) for n in N if 'knee' in n]
for s in range(0, len(sel), 50):
    w = sel[s:s+50]
    if len(w) < 10: break
    dt = w[-1]['t'] - w[0]['t']
    rate = math.degrees(uw[s+len(w)-1] - uw[s]) / dt
    gz = np.mean([r['gyro_body'][2] for r in w])
    a = np.array([r['action'] if r.get('action') and len(r['action'])==14 else [np.nan]*14 for r in w]); q = np.array([r['q'] for r in w])
    print(tod(w[0]['t']), 'vth', w[0]['cmd'].get('vtheta'), 'vx', w[0]['cmd'].get('vx'), f"turn {np.nanmean([r.get('turn',np.nan) for r in w]):+.2f}",
          f"yaw {rate:+6.1f} deg/s gz {math.degrees(gz):+6.1f}",
          'hipyaw act p2p', [round(float(np.nanmax(a[:, i])-np.nanmin(a[:, i])), 3) for i in iy], 'q p2p', [round(float(np.ptp(q[:, i])), 3) for i in iy],
          'knee q p2p', [round(float(np.ptp(q[:, i])), 3) for i in ik], 'policy', w[0].get('policy'))
