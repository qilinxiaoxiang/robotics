"""Yaw about gravity every 0.25 s between two times, against the IMU-quaternion yaw approach's guard actually reads."""
import json, math, sys
sys.path.insert(0, '.')
import types; sys.modules['onnxruntime'] = types.ModuleType('onnxruntime')
from walk_brain import body_quat, yaw_of
a, b = float(sys.argv[2]), float(sys.argv[3])
rows = []
for l in open(sys.argv[1]):
    if l.startswith('{'):
        try:
            r = json.loads(l)
            if a <= r['t'] <= b and r.get('gb') and r.get('gyro_body'): rows.append(r)
        except ValueError: pass
def rate(r):
    g, gb = r['gyro_body'], r['gb']; n = math.sqrt(sum(x*x for x in gb)) or 1.0
    return -sum(p*q for p, q in zip(g, gb)) / n
y = 0.0; y0 = yaw_of(body_quat(rows[0]['quat']))
for p, q in zip(rows, rows[1:]):
    y += rate(q) * min(q['t']-p['t'], 0.1)
    if int(q['t']*4) != int(p['t']*4):
        qy = math.degrees(math.atan2(math.sin(yaw_of(body_quat(q['quat']))-y0), math.cos(yaw_of(body_quat(q['quat']))-y0)))
        print(f"{q['t']-a:5.2f} gyro {math.degrees(y):+7.1f} quat {qy:+7.1f} vth {(q.get('cmd') or {}).get('vtheta')} turn {q.get('turn')} hipY R {q['q'][4]:+.2f} L {q['q'][9]:+.2f} headp {q['q'][10]:+.2f} hipP L {q['q'][7]:+.2f} R {q['q'][2]:+.2f}")
