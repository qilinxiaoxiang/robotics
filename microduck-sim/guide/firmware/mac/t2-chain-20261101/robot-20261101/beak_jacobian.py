"""How much each head joint moves the mouth tip at the real close pose (run 9 pick 2, phase 0.35), m per rad, by finite differences."""
import json, sys, os
sys.path.insert(0, os.getcwd())
from duck_kin import DuckKin
ID = ["right_ankle", "right_knee", "right_hip_pitch", "right_hip_roll", "right_hip_yaw", "left_ankle", "left_knee", "left_hip_pitch",
      "left_hip_roll", "left_hip_yaw", "head_pitch", "neck_pitch", "head_yaw", "head_roll"]
rows = [json.loads(l) for l in open('t2-chain-20261101/robot-20261101/picks/run1_pick.jsonl')]
r = min(rows, key=lambda x: abs((x.get('sp_phase') or 0) - .35)); q = dict(zip(ID, r['q'])); k = DuckKin(); t0 = k.mouth_tip(q, r['gb'])
print('tip', [round(float(x), 4) for x in t0], {n: round(q[n], 2) for n in ID[10:]})
for n in ID[10:]:
    q2 = dict(q); q2[n] += 0.05; t = k.mouth_tip(q2, r['gb'])
    print(n, ['%+.3f' % ((a - b) / 0.05) for a, b in zip(t, t0)])
