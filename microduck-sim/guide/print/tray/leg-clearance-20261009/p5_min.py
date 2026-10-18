"""Reduced sweep set (machine load ~87 on 10 cores): 1 mm EDT fields from p5_field, leg samples thinned to one per 1.2 mm voxel.
Left: yaw {0,-0.1,-0.2,-0.3,walk min -0.336, MJCF min -0.436} x roll {walk min, home, walk max} x knee straight, ankle home.
Then knee walk extremes and ankle walk extremes at the governing yaw/roll, and mirrored right-leg checks. Prints each sweep."""
import sys, json, time, numpy as np; sys.path.insert(0, '.')
import p5_field as P
for s in P.PTS:
    Pl, lab = P.PTS[s]; newP = []; newlab = []; off = 0
    for b, p in Pl:
        l = lab[off:off + len(p)]; off += len(p)
        _, i = np.unique(np.round(p / 1.2).astype(np.int64), axis=0, return_index=True); newP.append((b, p[i])); newlab.append(l[i])
    P.PTS[s] = (newP, np.concatenate(newlab))
print('npts', {s: len(P.PTS[s][1]) for s in P.PTS}, flush=True)
W = P.W; H = P.HOME; res = []
def run(side, yaw, roll, knee, ankle, tag):
    y, r, pj, kj, aj = P.L.SIDE[side]['joints']; lim = P.rng(pj)[1] if side == 'left' else P.rng(pj)[0]
    t = time.time(); first, start = P.sweep(side, {y: yaw, r: roll, kj: knee, aj: ankle}, H[pj], lim)
    row = dict(side=side, tag=tag, yaw=round(yaw, 3), roll=round(roll, 3), knee=round(knee, 4), ankle=round(ankle, 3), first=first, startMm=start); res.append(row)
    print(json.dumps(row), round(time.time() - t, 1), 's', flush=True); json.dump(res, open('p5-min.json', 'w'), indent=1)
for yaw in (0.0, -0.1, -0.2, -0.3, W['left_hip_yaw']['min'], P.rng('left_hip_yaw')[0]):
    for roll in (W['left_hip_roll']['min'], H['left_hip_roll'], W['left_hip_roll']['max']):
        run('left', yaw, roll, 0.0, H['left_ankle'], 'kneeStraight')
