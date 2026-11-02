"""Worst fitted yaw rate against the command through every in-place spin in the robot logs, per fit window.
A threshold has to sit above all of these (all these spins were commanded the way they went) and below a real reversal."""
import json, math, sys, types
sys.modules['onnxruntime'] = types.ModuleType('onnxruntime')
sys.path.insert(0, '.')
from walk_brain import body_quat, yaw_of
D = 't2-chain-20261101/robot-20261101/'
rows = {}
for f in ('brain_spin_induce', 'brain_spin_position', 'brain_run4', 'brain_run5', 'brain_run6', 'brain_turns_run2_run3'):
    for l in open(D + f + '.jsonl'):
        if l.startswith('{'):
            try: r = json.loads(l)
            except ValueError: continue
            if r.get('quat'): rows[r['t']] = r
R = [rows[t] for t in sorted(rows)]
spins, i = [], 0
while i < len(R):
    c = R[i].get('cmd') or {}
    if c.get('vx') == 0 and abs(c.get('vtheta') or 0) > 0.05:
        j = i
        while j + 1 < len(R) and (R[j+1].get('cmd') or {}).get('vtheta') and R[j+1]['t'] - R[j]['t'] < 0.2: j += 1
        Y = []
        for r in R[i:j+1]:
            y = yaw_of(body_quat(r['quat']))
            Y.append((r['t'], y if not Y else Y[-1][1] + math.atan2(math.sin(y - Y[-1][1]), math.cos(y - Y[-1][1]))))
        spins.append((1 if c['vtheta'] > 0 else -1, Y)); i = j
    i += 1
def slope(p):
    mt, my = sum(a for a, _ in p)/len(p), sum(b for _, b in p)/len(p)
    den = sum((a-mt)**2 for a, _ in p)
    return sum((a-mt)*(b-my) for a, b in p)/den if den else 0.0
print(len(spins), 'spins')
for win in (1.0, 1.5, 2.0, 2.5):
    worst, n = [], 0
    for d, Y in spins:
        w = None; a = 0
        for b in range(len(Y)):
            while Y[a][0] < Y[b][0] - win: a += 1
            if Y[b][0] - Y[0][0] >= win:
                s = -d * math.degrees(slope(Y[a:b+1]))
                w = s if w is None else max(w, s)
        if w is not None: worst.append(w); n += 1
    worst.sort()
    print(f"window {win} s: {n} spins long enough, worst against the command {worst[-1]:+.1f} deg/s, next {worst[-2]:+.1f}, median {worst[len(worst)//2]:+.1f}")
