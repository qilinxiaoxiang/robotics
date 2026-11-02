"""Where the mouth tip really is in the foot frame through each robot pick (DuckKin on the logged joints and gravity), against the ball.
Run from the mac directory with the dyn venv."""
import glob, json, sys, os
sys.path.insert(0, os.getcwd())
from duck_kin import DuckKin
ID = ["right_ankle", "right_knee", "right_hip_pitch", "right_hip_roll", "right_hip_yaw", "left_ankle", "left_knee", "left_hip_pitch",
      "left_hip_roll", "left_hip_yaw", "head_pitch", "neck_pitch", "head_yaw", "head_roll"]
BALL = {"run1": [(0.100, -0.021, "held")], "run2": [(0.122, -0.005, "miss")], "run9": [(0.110, -0.028, "miss"), (0.102, -0.007, "miss")]}
k = DuckKin()
for f in sorted(glob.glob('t2-chain-20261101/robot-20261101/picks/run*_pick.jsonl')):
    name = os.path.basename(f).split('_')[0]; rows = [json.loads(l) for l in open(f)]; eps, cur = [], []
    for r in rows:
        if cur and r['t'] - cur[-1]['t'] > 2: eps.append(cur); cur = []
        cur.append(r)
    eps.append(cur)
    for ep, b in zip(eps, BALL[name]):
        print(name, 'ball x %.3f y %.3f' % b[:2], b[2])
        for ph in (.15, .25, .30, .33, .35, .37, .39, .41):
            r = min(ep, key=lambda x: abs((x.get('sp_phase') or 0) - ph))
            q = dict(zip(ID, r['q']))
            m = k.mouth_tip(q, r['gb'])
            print('  ph %.2f tip x %.3f y %.3f z %.3f | tip-ball dx %+.1f dy %+.1f cm | hp %.2f neck %.2f yaw %.2f ank %.2f %.2f jaw %.1f' % (r['sp_phase'], m[0], m[1], m[2], (m[0] - b[0]) * 100, (m[1] - b[1]) * 100,
                  q['head_pitch'], q['neck_pitch'], q['head_yaw'], q['right_ankle'], q['left_ankle'], r.get('jaw_deg') or 0))
