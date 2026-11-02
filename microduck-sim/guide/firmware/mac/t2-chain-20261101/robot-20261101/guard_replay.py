"""Replay approach.turn_check's fitted slope on robot spins: run 4 (a real turn, the old check tripped) and the induced stall."""
import json, math, sys, types
sys.modules['onnxruntime'] = types.ModuleType('onnxruntime')
sys.path.insert(0, '.')
from walk_brain import body_quat, yaw_of
def yaws(path, a, b):
    out = []
    for l in open(path):
        if l.startswith('{'):
            try: r = json.loads(l)
            except ValueError: continue
            if a <= r['t'] <= b and r.get('quat'):
                y = yaw_of(body_quat(r['quat']))
                out.append((r['t'], y if not out else out[-1][1] + math.atan2(math.sin(y - out[-1][1]), math.cos(y - out[-1][1]))))
    return out
def slope(pts):
    mt, my = sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts)
    return sum((p[0]-mt)*(p[1]-my) for p in pts)/sum((p[0]-mt)**2 for p in pts)
D = 't2-chain-20261101/robot-20261101/'
C = {'run 4, real turn': (D+'brain_run4.jsonl', 1793587576.9, 1793587580.2),
     'induced, 3rd right (free until stall)': (D+'brain_spin_position.jsonl', None, None),}
Y = yaws(C['run 4, real turn'][0], 1793587576.9, 1793587580.2)
print('run 4 span', round(Y[-1][0]-Y[0][0],2), 's, net', round(math.degrees(Y[-1][1]-Y[0][1]),1), 'deg, slope over all', round(math.degrees(slope(Y)),1), 'deg/s')
t0 = None
for l in open(D+'brain_spin_position.jsonl'):
    if l.startswith('{'):
        t0 = json.loads(l)['t']; break
for name, a, b in (('stall, last right spin', t0+43.5, t0+49), ('free right spin', t0+21, t0+27), ('second right spin', t0+32, t0+38)):
    Y = yaws(D+'brain_spin_position.jsonl', a, b)
    worst = []
    i = 0
    for j in range(len(Y)):
        while Y[i][0] < Y[j][0]-3.0: i += 1
        if Y[j][0]-Y[0][0] >= 3.0: worst.append(math.degrees(slope(Y[i:j+1])))
    print(name, 'slope over 3 s: min', round(min(worst),1), 'max', round(max(worst),1), 'last', round(worst[-1],1))
