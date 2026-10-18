"""Swept occupancy of the leg surfaces near the lower power-support region over the walking frames (1 mm voxels).

Usage: leg_sweep.py <left|right>
For each frame, pitch-chain leg surface samples (0.5 mm + vertices) inside the box BOX are binned into 1 mm voxels;
counts[v] = number of adopted (non-falling, non-blend) frames whose leg surface touched voxel v; counts_all includes
the excluded runs. Writes SCRATCH/sweep-<side>.npz.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pso_lib as L

side = sys.argv[1]
t0 = time.time()
BOX = np.array([[-75.0, -34.0, -66.0], [5.0, 34.0, -20.0]]); VS = 1.0
SH = np.ceil((BOX[1] - BOX[0]) / VS).astype(int) + 1
fk = L.FK(); cfg = L.SIDE[side]; J = cfg['joints']; bodies = list(cfg['parts'])[2:]
PARTS = []
for b in bodies:
    for k in cfg['parts'][b]:
        v, f = L.solid(k); m = trimesh.Trimesh(v, f, process=False)
        p, _ = trimesh.sample.sample_surface(m, max(400, int(m.area / 0.25)), seed=1)
        P = np.vstack([p, v])
        key = np.floor(P / 5.0).astype(np.int64)
        _, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.ravel()
        o = np.argsort(inv, kind='stable'); P = P[o]; inv = inv[o]
        st = np.r_[0, np.flatnonzero(np.diff(inv)) + 1, len(inv)]
        C = np.array([(P[a:e].min(0) + P[a:e].max(0)) / 2 for a, e in zip(st[:-1], st[1:])])
        R = np.array([np.linalg.norm(P[a:e] - C[n], axis=1).max() for n, (a, e) in enumerate(zip(st[:-1], st[1:]))])
        PARTS.append((b, P, st, C, R))
iT0 = {b: np.linalg.inv(fk.T0[b]) for b in bodies}
M_, D_ = fk.M, fk.D; tb = M_.body('trunk_base').id; bid = {b: M_.body(b).id for b in bodies}
Q = np.load(L.SCRATCH / 'walk_qpos.npy'); trace = np.load(L.SCRATCH / 'walk_trace.npy')
src = L.walking_sources(); adopted_trace = np.array([not s['fell'] and not s['blend'] for s in src])
counts = np.zeros(SH, np.int32); counts_all = np.zeros(SH, np.int32)
for i in range(len(Q)):
    D_.qpos[:] = M_.qpos0
    for j in J:
        D_.qpos[fk.qadr[j]] = Q[i, fk.qadr[j]]
    fk.mj.mj_kinematics(M_, D_)
    R0 = D_.xmat[tb].reshape(3, 3); p0 = D_.xpos[tb]
    idx_all = []
    for b, P, st, C, R in PARTS:
        T = np.eye(4); T[:3, :3] = R0.T @ D_.xmat[bid[b]].reshape(3, 3); T[:3, 3] = R0.T @ (D_.xpos[bid[b]] - p0) * 1000.0
        T = T @ iT0[b]
        Cw = C @ T[:3, :3].T + T[:3, 3]
        live = np.flatnonzero(np.all((Cw >= BOX[0] - R[:, None]) & (Cw <= BOX[1] + R[:, None]), 1))
        if not len(live):
            continue
        sel = np.concatenate([np.arange(st[c], st[c + 1]) for c in live])
        X = P[sel] @ T[:3, :3].T + T[:3, 3]
        k = np.all((X >= BOX[0]) & (X <= BOX[1]), 1)
        if k.any():
            idx_all.append(np.round((X[k] - BOX[0]) / VS).astype(np.int64))
    if idx_all:
        idx = np.vstack(idx_all)
        flat = np.unique(np.ravel_multi_index(idx.T, SH))
        counts_all.ravel()[flat] += 1
        if adopted_trace[trace[i]]:
            counts.ravel()[flat] += 1
    if i % 50000 == 0:
        print(i, round(time.time() - t0, 1), flush=True)
np.savez_compressed(L.SCRATCH / f'sweep-{side}.npz', counts=counts, counts_all=counts_all, box=BOX, vs=VS)
print('DONE', round(time.time() - t0, 1), int((counts > 0).sum()), int((counts_all > 0).sum()), flush=True)
