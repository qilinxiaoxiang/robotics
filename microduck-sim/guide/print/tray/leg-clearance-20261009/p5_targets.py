"""Commanded target_angles vs qpos ranges over the same 98 walking traces used for walk-stats-adopted.json."""
import json, numpy as np, os
SIM = '/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/phase1/simulation/'
src = json.load(open('walk_q_sources.json')); J = ['left_hip_yaw', 'left_hip_roll', 'left_hip_pitch', 'left_knee', 'left_ankle', 'right_hip_yaw', 'right_hip_roll', 'right_hip_pitch', 'right_knee', 'right_ankle']
T = {j: [] for j in J}; Q = {j: [] for j in J}; n = 0; keys = None
for row in src:
    f = SIM + row[0]
    if not os.path.exists(f): continue
    d = json.load(open(f)); cases = d['cases'] if 'cases' in d else [d]
    for c in cases:
        fr = c.get('frames') or c.get('trace') or c.get('history')
        if fr is None:
            fr = next((v for v in c.values() if isinstance(v, list) and v and isinstance(v[0], dict) and 'target_angles' in v[0]), None)
        if fr is None: continue
        n += 1
        for x in fr:
            ta, qp = x['target_angles'], x['qpos']
            if keys is None: keys = (type(ta).__name__, list(ta)[:3] if isinstance(ta, dict) else len(ta), type(qp).__name__, list(qp)[:3] if isinstance(qp, dict) else len(qp))
            for j in J:
                if isinstance(ta, dict): T[j].append(ta[j])
                if isinstance(qp, dict) and j in qp: Q[j].append(qp[j])
print('traces', n, 'format', keys)
out = {j: dict(target=[round(float(np.min(T[j])), 3), round(float(np.max(T[j])), 3)] if T[j] else None, qpos=[round(float(np.min(Q[j])), 3), round(float(np.max(Q[j])), 3)] if Q[j] else None, frames=len(T[j])) for j in J}
for j in J: print(j, out[j])
json.dump(dict(traces=n, stats=out), open('p5-walk-targets.json', 'w'), indent=1)
