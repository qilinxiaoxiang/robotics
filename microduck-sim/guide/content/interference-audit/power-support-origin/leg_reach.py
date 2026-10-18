"""Leg reach toward the integrated power support over the phase-1 walking frames, a per-joint walking-envelope grid,
or (for the two hip bodies, which move only with hip yaw and roll) a yaw x roll grid.

Usage: leg_reach.py <left|right> <frames|envelope|hipgrid> [support_stl] [start end]
Stage 1 (all poses): pitch-chain leg parts (thigh/knee, shin, ankle/foot; hip bodies only in hipgrid) as surface samples
  (0.5 mm + vertices), culled by 5 mm clusters, looked up in a 1 mm unsigned distance field of the support surface
  (nearest voxel). Field error <= 2.07 mm, sample covering radius rcov, so every pose with a true gap < 2 mm has a
  sampled point below T1 = 2 + 2.07 + rcov.
Stage 2 (flagged poses): exact triangle-triangle gap (manifold3d min_gap) per flagged part to the support, to the
  added material only, and (frames/envelope) to the OpenRB tray and board.
Stage 3 (exact gap < 3 mm): exact gap per support region; nearest support point for poses < 2 mm.
"""
import itertools
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pso_lib as L

side, mode = sys.argv[1], sys.argv[2]
support_path = Path(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != '-' else L.CB / 'power-support-integrated-body.stl'
rng_ = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else None
tag = ('' if support_path.name == 'power-support-integrated-body.stl' else '-' + support_path.stem) + (f'-{rng_[0]}-{rng_[1]}' if rng_ else '')
t0 = time.time()
VS = 1.0; FERR = 0.866 + 0.866 + 0.35; MARGIN = 14.0; CL = 5.0

body = L.tm_load(support_path)
orig = L.tm_load(L.CB / 'original-power-support-body.stl')
B = L.mesh_to_m(body); O = L.mesh_to_m(orig); A = B - O
REG = []
rest = B
for name, (lo, hi) in L.REGIONS:
    REG.append((name, B ^ L.box_m(lo, hi))); rest = rest - L.box_m(lo, hi)
REG.append(('original_frame_kept', rest ^ O)); REG.append(('battery_bay_and_other_added', rest - O))
USE_TB = mode != 'hipgrid'
TGT = {'tray': L.solid('openrb_tray'), 'board': L.solid('openrb_board')} if USE_TB else {}
TGM = {k: L.to_m(*v) for k, v in TGT.items()}


def field(mesh, spacing=0.15):
    lo = mesh.bounds[0] - MARGIN; hi = mesh.bounds[1] + MARGIN
    sh = np.ceil((hi - lo) / VS).astype(int) + 1
    g = np.ones(sh, bool)
    n = int(mesh.area / spacing ** 2)
    for c in range(0, n, 400000):
        p, _ = trimesh.sample.sample_surface(mesh, min(400000, n - c), seed=3 + c)
        idx = np.round((p - lo) / VS).astype(int); g[idx[:, 0], idx[:, 1], idx[:, 2]] = False
    idx = np.round((mesh.vertices - lo) / VS).astype(int); g[idx[:, 0], idx[:, 1], idx[:, 2]] = False
    return lo, sh, ndimage.distance_transform_edt(g, sampling=VS).astype(np.float32)


FIELDS = {'support': field(body)}
for k, (v, f) in TGT.items():
    FIELDS[k] = field(trimesh.Trimesh(v, f, process=False))


def lookup(fld, X):
    lo, sh, F = fld
    idx = np.round((X - lo) / VS).astype(int)
    ok = np.all((idx >= 0) & (idx < sh), 1)
    d = np.full(len(X), 99.0, np.float32)
    d[ok] = F[idx[ok, 0], idx[ok, 1], idx[ok, 2]]
    return d


fk = L.FK()
cfg = L.SIDE[side]
J = cfg['joints']
bodies = list(cfg['parts'])
use_bodies = bodies[:2] if mode == 'hipgrid' else bodies[2:]
PARTS = []
cover = {}
for b in use_bodies:
    for k in cfg['parts'][b]:
        v, f = L.solid(k)
        m = trimesh.Trimesh(v, f, process=False)
        n = max(400, int(m.area / 0.25))
        p, _ = trimesh.sample.sample_surface(m, n, seed=1)
        P = np.vstack([p, v])
        dense, _ = trimesh.sample.sample_surface(m, min(400000, n * 12), seed=7)
        cover[k] = float(cKDTree(P).query(dense)[0].max())
        key = np.floor(P / CL).astype(np.int64)
        _, inv = np.unique(key, axis=0, return_inverse=True)
        inv = inv.ravel(); order = np.argsort(inv, kind='stable'); P = P[order]; inv = inv[order]
        starts = np.r_[0, np.flatnonzero(np.diff(inv)) + 1, len(inv)]
        C = np.array([(P[s:e].min(0) + P[s:e].max(0)) / 2 for s, e in zip(starts[:-1], starts[1:])])
        Rr = np.array([np.linalg.norm(P[s:e] - C[i], axis=1).max() for i, (s, e) in enumerate(zip(starts[:-1], starts[1:]))])
        PARTS.append(dict(key=k, body=b, P=P, starts=starts, C=C, R=Rr, man=L.to_m(v, f)))
RCOV = max(cover.values())
T1 = 2.0 + FERR + RCOV
iT0 = {b: np.linalg.inv(fk.T0[b]) for b in use_bodies}
print('setup', round(time.time() - t0, 1), 's; rcov', round(RCOV, 3), 'T1', round(T1, 3), flush=True)

# poses
if mode == 'frames':
    Q = np.load(L.SCRATCH / 'walk_qpos.npy')
    idxs = range(len(Q)) if rng_ is None else range(rng_[0], min(rng_[1], len(Q)))
    poses = [{j: float(Q[i, fk.qadr[j]]) for j in J} for i in idxs]
    frame_ids = np.array(list(idxs))
else:
    st = json.loads((Path(__file__).with_name('walk-frames.json')).read_text())['stats_adopted']
    if mode == 'envelope':
        grids = [np.linspace(st[J[0]]['min'], st[J[0]]['max'], 7), np.linspace(st[J[1]]['min'], st[J[1]]['max'], 7),
                 np.linspace(st[J[2]]['min'], st[J[2]]['max'], 9), np.linspace(st[J[3]]['min'], st[J[3]]['max'], 7),
                 np.linspace(st[J[4]]['min'], st[J[4]]['max'], 5)]
    else:
        grids = [np.arange(st[J[0]]['min'] - 0.0025, st[J[0]]['max'] + 0.005, 0.005),
                 np.arange(st[J[1]]['min'] - 0.0025, st[J[1]]['max'] + 0.005, 0.005), [0.0], [0.0], [0.0]]
    poses = [dict(zip(J, map(float, c))) for c in itertools.product(*grids)]
    frame_ids = np.arange(len(poses))
if os.environ.get('LIMIT'):
    poses = poses[:int(os.environ['LIMIT'])]; frame_ids = frame_ids[:len(poses)]
N = len(poses)
M_, D_ = fk.M, fk.D
tb = M_.body('trunk_base').id
bid = {b: M_.body(b).id for b in use_bodies}


def part_T(q):
    D_.qpos[:] = M_.qpos0
    for j, v in q.items():
        D_.qpos[fk.qadr[j]] = v
    fk.mj.mj_kinematics(M_, D_)
    R0 = D_.xmat[tb].reshape(3, 3); p0 = D_.xpos[tb]; out = {}
    for b, i in bid.items():
        T = np.eye(4); T[:3, :3] = R0.T @ D_.xmat[i].reshape(3, 3); T[:3, 3] = R0.T @ (D_.xpos[i] - p0) * 1000.0
        out[b] = T @ iT0[b]
    return out


# stage 1
coarse = np.full((N, 3), 99.0, np.float32)
cpart = {}; cpart_tb = {}
for i, q in enumerate(poses):
    PT = part_T(q)
    best = [99.0, 99.0, 99.0]
    for pr in PARTS:
        M = PT[pr['body']]; Rm = M[:3, :3]; tv = M[:3, 3]
        Cw = pr['C'] @ Rm.T + tv
        fs = lookup(FIELDS['support'], Cw) - pr['R']
        if USE_TB:
            ft = np.minimum(lookup(FIELDS['tray'], Cw), lookup(FIELDS['board'], Cw)) - pr['R']
            live = np.flatnonzero((fs < T1) | (ft < T1))
        else:
            live = np.flatnonzero(fs < T1)
        if not len(live):
            continue
        st_ = pr['starts']
        sel = np.concatenate([np.arange(st_[c], st_[c + 1]) for c in live])
        X = pr['P'][sel] @ Rm.T + tv
        ds = float(lookup(FIELDS['support'], X).min()); best[0] = min(best[0], ds)
        if ds < T1:
            cpart.setdefault(i, []).append(pr['key'])
        if USE_TB:
            dt = float(lookup(FIELDS['tray'], X).min()); db = float(lookup(FIELDS['board'], X).min())
            best[1] = min(best[1], dt); best[2] = min(best[2], db)
            if min(dt, db) < T1:
                cpart_tb.setdefault(i, []).append(pr['key'])
    coarse[i] = best
    if i % 25000 == 0:
        print('stage1', i, N, round(time.time() - t0, 1), 's', flush=True)
flag = sorted(set(cpart) | set(cpart_tb))
print('stage1 done', round(time.time() - t0, 1), 's; flagged', len(cpart), 'tray/board', len(cpart_tb), flush=True)

# stage 2
exact = np.full(N, 99.0); exact_added = np.full(N, 99.0); exact_tb = np.full((N, 2), 99.0); epart = {}
PM = {pr['key']: (pr['body'], pr['man']) for pr in PARTS}
for n_, i in enumerate(flag):
    PT = part_T(poses[i])
    ns = set(cpart.get(i, [])); nt = set(cpart_tb.get(i, []))
    for k in ns | nt:
        b, m = PM[k]
        mt = m.transform(np.asarray(PT[b][:3, :4]))
        if k in ns:
            g = mt.min_gap(B, 6.0)
            if g < exact[i]:
                exact[i] = g; epart[i] = k
            exact_added[i] = min(exact_added[i], mt.min_gap(A, 6.0))
        if k in nt:
            exact_tb[i, 0] = min(exact_tb[i, 0], mt.min_gap(TGM['tray'], 6.0))
            exact_tb[i, 1] = min(exact_tb[i, 1], mt.min_gap(TGM['board'], 6.0))
    if n_ % 5000 == 0:
        print('stage2', n_, len(flag), round(time.time() - t0, 1), 's', flush=True)
print('stage2 done', round(time.time() - t0, 1), 's', flush=True)

# stage 3
near = np.flatnonzero(exact < 3.0)
reg_gap = {}; overlap = {}
pts = []
for n_, i in enumerate(near):
    PT = part_T(poses[i]); rg = {}
    for k in cpart.get(int(i), []):
        b, m = PM[k]
        mt = m.transform(np.asarray(PT[b][:3, :4]))
        for name, R in REG:
            if R.is_empty():
                continue
            g = mt.min_gap(R, 3.5)
            if g < 3.5 and (name not in rg or g < rg[name][0]):
                rg[name] = (round(g, 4), k)
        if exact[i] == 0.0:
            ov = (mt ^ B).volume()
            if ov > overlap.get(int(i), (0, None))[0]:
                overlap[int(i)] = (round(ov, 4), k)
    reg_gap[int(i)] = rg
    if exact[i] < 2.0:
        k = epart[int(i)]; b, _ = PM[k]
        pr = next(p for p in PARTS if p['key'] == k)
        M = PT[b]; X = pr['P'] @ M[:3, :3].T + M[:3, 3]
        d = lookup(FIELDS['support'], X); X = X[np.argsort(d)[:200]]
        cp, dd, _ = trimesh.proximity.closest_point(body, X)
        j = int(np.argmin(dd))
        pts.append([int(i), *cp[j].tolist(), *X[j].tolist(), float(dd[j])])
    if n_ % 2000 == 0:
        print('stage3', n_, len(near), round(time.time() - t0, 1), 's', flush=True)
print('stage3 done', len(near), round(time.time() - t0, 1), 's', flush=True)

res = dict(side=side, mode=mode, support=str(support_path), range=rng_, poses=N, T1=T1, FERR=FERR, legCoverRadiusMm=cover,
           flaggedSupport=len(cpart), flaggedTrayBoard=len(cpart_tb), elapsed_s=round(time.time() - t0, 1),
           exactMinSupport=float(exact.min()), exactMinAdded=float(exact_added.min()),
           exactMinTray=float(exact_tb[:, 0].min()), exactMinBoard=float(exact_tb[:, 1].min()),
           regionGap={str(int(frame_ids[k])): v for k, v in reg_gap.items()},
           overlap={str(int(frame_ids[k])): v for k, v in overlap.items()},
           exactPart={str(int(frame_ids[k])): v for k, v in epart.items() if exact[k] < 3.0})
if mode != 'frames':
    res['grid'] = {j: [round(float(x), 4) for x in g] for j, g in zip(J, grids)}
L.jdump(res, L.SCRATCH / f'reach-{side}-{mode}{tag}.json')
np.savez(L.SCRATCH / f'reach-{side}-{mode}{tag}.npz', frame_ids=frame_ids, coarse=coarse, exact=exact, exact_added=exact_added,
         exact_tb=exact_tb, pts=np.array(pts).reshape(-1, 8), poses=np.array([[p[j] for j in J] for p in poses]))
print('DONE', json.dumps({k: v for k, v in res.items() if k not in ('regionGap', 'exactPart', 'legCoverRadiusMm', 'overlap')}), flush=True)
