"""All adopted walking qpos frames (every 25th of 147000) on both legs: min clearance to tray/board and to installed torso parts."""
import json, numpy as np, sys; sys.path.insert(0, '.')
SIM = '/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/phase1/simulation/'
N = ["left_hip_yaw", "left_hip_roll", "left_hip_pitch", "left_knee", "left_ankle", "neck_pitch", "head_pitch", "head_yaw", "head_roll", "right_hip_yaw", "right_hip_roll", "right_hip_pitch", "right_knee", "right_ankle"]
QP = []
for f, n, flag, *_ in json.load(open('walk_q_sources.json')):
    if flag or 'blend' in f: continue
    d = json.load(open(SIM + f)); fr = next(v for v in d.values() if isinstance(v, list) and v and isinstance(v[0], dict) and 'qpos' in v[0]); QP.append(np.array([x['qpos'][7:] for x in fr]))
qp = np.vstack(QP); np.save('p5_adopted_qpos.npy', qp); print('frames', len(qp), flush=True)
import p5_field as P
for s in P.PTS:
    Pl, lab = P.PTS[s]; newP = []; newlab = []; off = 0
    for b, p in Pl:
        l = lab[off:off + len(p)]; off += len(p); _, i = np.unique(np.round(p / 1.2).astype(np.int64), axis=0, return_index=True); newP.append((b, p[i])); newlab.append(l[i])
    P.PTS[s] = (newP, np.concatenate(newlab))
inst = ['power_support', 'shell_torso_base', 'other_torso']; out = {}
for side in ('left', 'right'):
    J = P.L.SIDE[side]['joints']; best = {}; 
    for k in range(0, len(qp), 25):
        q = {j: float(qp[k, N.index(j)]) for j in J}; r, _ = P.evaluate(side, q)
        for key, val in (('trayOrBoard', min(r['tray'][0], r['board'][0])), ('installed', min(r[x][0] for x in inst)), ('upstreamBay', r['upstream_battery_bay'][0])):
            if key not in best or val < best[key][0]: best[key] = (round(val, 2), int(k), {j: round(v, 3) for j, v in q.items()}, r['tray'][1] if key == 'trayOrBoard' else None)
    out[side] = best; print(side, best, flush=True)
json.dump(out, open('p5-frames-all.json', 'w'), indent=1)
