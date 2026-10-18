"""Fraction of recorded policy targets outside MJCF joint ranges, per trace and joint."""
import json, re, sys, numpy as np
from pathlib import Path
SIMDIR = Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/phase1/simulation')
XML = Path('/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl/src/mjlab_microduck/robot/microduck/robot_allcollisions.xml')
CAL = Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/phase1/runtime/calibration.template.json')
N = ["left_hip_yaw","left_hip_roll","left_hip_pitch","left_knee","left_ankle","neck_pitch","head_pitch","head_yaw","head_roll",
     "right_hip_yaw","right_hip_roll","right_hip_pitch","right_knee","right_ankle"]
rng = {m.group(1): (float(m.group(2)), float(m.group(3))) for m in re.finditer(r'name="([a-z_]+)" type="hinge" range="([-\d.e]+) ([-\d.e]+)"', XML.read_text())}
cal = json.loads(CAL.read_text())['joint_limits_rad']
assert all(abs(rng[j][0]-cal[j][0])<1e-9 and abs(rng[j][1]-cal[j][1])<1e-9 for j in N), 'calibration template differs from MJCF'
lo = np.array([rng[j][0] for j in N]); hi = np.array([rng[j][1] for j in N])
mode = sys.argv[1]
if mode == 'final':
    cases = ['baseline','voltage475','voltage400','voltage525','floor06','sensor40','action40','push','joint-noise','extra-wire20','extra-wire40']
    files = [SIMDIR/f'phase1-candidate-old{m}-{c}.json' for m in (0,60,120) for c in cases]
else:
    src = json.load(open('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/print-work/tray/walk_q_sources.json'))
    files = [SIMDIR/f for f, n, flag, *_ in src if (not flag) and 'blend' not in f]
allT=[]; allQ=[]; allt=[]; per=[]
for f in files:
    d = json.loads(f.read_text()); rows = d['rows']
    T = np.array([r['target_angles'] for r in rows]); Q = np.array([r['qpos'][7:] for r in rows]); t = np.array([r['time'] for r in rows])
    out = (T < lo) | (T > hi); anyo = out.any(1)
    first = int(np.argmax(anyo)) if anyo.any() else None
    walk = (t > 2.0)
    first_walk = None
    if (anyo & walk).any():
        k = int(np.argmax(anyo & walk)); first_walk = dict(t=float(t[k]), joints=[N[i] for i in np.where(out[k])[0]])
    qout = ((Q < lo) | (Q > hi)).any()
    per.append(dict(file=f.name, frames=len(t), fell=d.get('fell'), frac_any=float(anyo.mean()),
        first_t=None if first is None else float(t[first]), first_joints=None if first is None else [N[i] for i in np.where(out[first])[0]],
        first_walk=first_walk, qpos_out=bool(qout), cmd_start=float(t[np.argmax([np.linalg.norm(r['command'][:2])>0 for r in rows])])))
    allT.append(T); allQ.append(Q); allt.append(t)
T=np.vstack(allT); Q=np.vstack(allQ); t=np.concatenate(allt)
out=(T<lo)|(T>hi)
print('mode',mode,'traces',len(files),'frames',len(T))
print('any joint out of MJCF range: frames %.4f' % out.any(1).mean())
for ph,mask in (('t<=2 stand',t<=2),('2<t<=25 walk',(t>2)&(t<=25)),('t>25 stop',t>25)):
    print(' phase',ph,'frames',int(mask.sum()),'frac any out %.4f'%out[mask].any(1).mean())
for i,j in enumerate(N):
    below=(T[:,i]<lo[i]).mean(); above=(T[:,i]>hi[i]).mean()
    print(f'{j:16s} range [{lo[i]:+.3f},{hi[i]:+.3f}] target [{T[:,i].min():+.3f},{T[:,i].max():+.3f}] qpos [{Q[:,i].min():+.3f},{Q[:,i].max():+.3f}] frac<lo {below:.4f} frac>hi {above:.4f} qpos_out {bool(((Q[:,i]<lo[i])|(Q[:,i]>hi[i])).any())}')
ft=[p['first_t'] for p in per if p['first_t'] is not None]
fw=[p['first_walk']['t'] for p in per if p['first_walk']]
print('traces with any violation', sum(p['first_t'] is not None for p in per), 'of', len(per))
print('first violation time s: min %.2f median %.2f max %.2f' % (min(ft), float(np.median(ft)), max(ft)))
print('first violation after walk cmd (t>2): min %.2f median %.2f max %.2f' % (min(fw), float(np.median(fw)), max(fw)))
from collections import Counter
print('first-violation joints', Counter(tuple(p['first_joints']) for p in per if p['first_joints']).most_common(8))
print('first walk-phase violation joints', Counter(tuple(p['first_walk']['joints']) for p in per if p['first_walk']).most_common(8))
print('any qpos outside range', any(p['qpos_out'] for p in per), 'fell', sum(bool(p['fell']) for p in per))
json.dump(dict(per=per), open(f'/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/walk-limits/limits-{mode}.json','w'), indent=1)
for p in per[:12]: print(p['file'], 'frac %.3f'%p['frac_any'], 'first', p['first_t'], p['first_joints'], 'walk-first', p['first_walk'])
