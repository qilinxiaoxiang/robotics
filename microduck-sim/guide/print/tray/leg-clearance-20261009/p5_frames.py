"""Adopted walking traces (105 sources minus fall-flagged and blend runs): commanded target_angles vs qpos ranges, then
pose-wise clearance of every frame whose hip pitch is backward of 0 (left > 0, right < 0), for qpos and for target poses."""
import json, numpy as np, sys; sys.path.insert(0, '.')
SIM = '/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/phase1/simulation/'
N = ["left_hip_yaw", "left_hip_roll", "left_hip_pitch", "left_knee", "left_ankle", "neck_pitch", "head_pitch", "head_yaw", "head_roll", "right_hip_yaw", "right_hip_roll", "right_hip_pitch", "right_knee", "right_ankle"]
src = json.load(open('walk_q_sources.json')); TA = {True: [], False: []}; QP = {True: [], False: []}
for f, n, flag, *_ in src:
    adopted = (not flag) and 'blend' not in f
    d = json.load(open(SIM + f)); fr = next(v for v in d.values() if isinstance(v, list) and v and isinstance(v[0], dict) and 'target_angles' in v[0])
    TA[adopted].append(np.array([x['target_angles'] for x in fr])); QP[adopted].append(np.array([x['qpos'][7:] for x in fr]))
ta = np.vstack(TA[True]); qp = np.vstack(QP[True]); print('adopted traces', len(TA[True]), 'frames', len(ta), 'excluded traces', len(TA[False]))
print('order check mean|target-qpos| per joint', np.round(np.abs(ta - qp).mean(0), 3).tolist())
st = {}
for i, j in enumerate(N):
    st[j] = dict(targetMin=round(float(ta[:, i].min()), 3), targetMax=round(float(ta[:, i].max()), 3), qposMin=round(float(qp[:, i].min()), 3), qposMax=round(float(qp[:, i].max()), 3),
                 targetP995abs=round(float(np.percentile(ta[:, i], 99.5)), 3), targetP005=round(float(np.percentile(ta[:, i], 0.5)), 3))
    if 'hip' in j or 'knee' in j or 'ankle' in j: print(j, st[j])
import p5_field as P
for s in P.PTS:
    Pl, lab = P.PTS[s]; newP = []; newlab = []; off = 0
    for b, p in Pl:
        l = lab[off:off + len(p)]; off += len(p); _, i = np.unique(np.round(p / 1.2).astype(np.int64), axis=0, return_index=True); newP.append((b, p[i])); newlab.append(l[i])
    P.PTS[s] = (newP, np.concatenate(newlab))
inst = ['power_support', 'shell_torso_base', 'other_torso']; res = {}
for label, A in (('qpos', qp), ('target', ta)):
    for side, pi, sg in (('left', 2, 1.0), ('right', 11, -1.0)):
        idx = np.where(sg * A[:, pi] > 0.0)[0]; J = P.L.SIDE[side]['joints']; best = None; newbest = None; n = 0
        for k in idx[::max(1, len(idx) // 3000)]:
            q = {j: float(A[k, N.index(j)]) for j in J}; r, _ = P.evaluate(side, q); n += 1
            tb = min(r['tray'][0], r['board'][0]); ins = min(r[x][0] for x in inst)
            if best is None or tb < best[0]: best = (round(tb, 2), int(k), {j: round(v, 3) for j, v in q.items()}, r['tray'][1], round(ins, 2))
        res[f'{label}/{side}'] = dict(framesBackwardOfZero=int(len(idx)), evaluated=n, minTrayBoardMm=best)
        print(label, side, res[f'{label}/{side}'], flush=True)
json.dump(dict(stats=st, frames=res, adoptedTraces=len(TA[True]), adoptedFrames=int(len(ta))), open('p5-frames.json', 'w'), indent=1)
