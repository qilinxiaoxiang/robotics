"""Replay the phase1 runtime current screens (core.py 203-216) on the 33 adopted walking traces, current proxy |tau|/kt sampled every 0.1 s."""
import json, glob, numpy as np
KT = 0.36601349688984386
SIM = '/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/phase1/simulation/'
files = [f for f in sorted(glob.glob(SIM + 'phase1-candidate-old*-*.json')) if not f.endswith('.config.json')]
ACT = ['left_hip_yaw','left_hip_roll','left_hip_pitch','left_knee','left_ankle','neck_pitch','head_pitch','head_yaw','head_roll',
       'right_hip_yaw','right_hip_roll','right_hip_pitch','right_knee','right_ankle']
M2ID = {"right_hip_yaw":5,"right_hip_roll":4,"right_hip_pitch":3,"right_knee":2,"right_ankle":1,"left_hip_yaw":10,"left_hip_roll":9,
        "left_hip_pitch":8,"left_knee":7,"left_ankle":6,"neck_pitch":12,"head_pitch":11,"head_yaw":13,"head_roll":14}
GROUPS = ((1,2),(3,4),(5,10),(6,7),(8,9),(11,12),(13,14))
out = []
for f in files:
    d = json.load(open(f)); rows = d['rows']
    t = np.array([r['time'] for r in rows]); I = np.abs(np.array([r['torques_nm'] for r in rows])) / KT
    byid = {M2ID[a]: I[:, k] for k, a in enumerate(ACT)}
    dt = float(np.median(np.diff(t))); step = max(1, int(round(0.1 / dt)))
    rec = {'name': f.split('/')[-1], 'dt': dt}
    for off in range(step):
        idx = np.arange(off, len(t), step)
        tot = I[idx].sum(1); grp = np.max([byid[a][idx] + byid[b][idx] for a, b in GROUPS], axis=0); one = I[idx].max(1)
        for k, (arr, lim) in {'total5.0': (tot, 5.0), 'group2.25': (grp, 2.25), 'single1.3': (one, 1.3)}.items():
            hit = np.nonzero(arr > lim)[0]
            rec.setdefault(k, []).append(float(t[idx][hit[0]]) if len(hit) else None)
    for k in ('total5.0', 'group2.25', 'single1.3'):
        v = rec[k]; rec[k] = {'phasesTripping': sum(x is not None for x in v), 'of': len(v), 'earliestT': min([x for x in v if x is not None], default=None)}
    out.append(rec)
summ = {k: {'tracesTrippingAnyPhase': sum(r[k]['phasesTripping'] > 0 for r in out), 'tracesTrippingAllPhases': sum(r[k]['phasesTripping'] == r[k]['of'] for r in out)} for k in ('total5.0', 'group2.25', 'single1.3')}
json.dump({'files': len(out), 'summary': summ, 'per': out}, open('screen-trips.json', 'w'), indent=1)
print(json.dumps(summ))
