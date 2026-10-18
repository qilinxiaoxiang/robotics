"""Can any trim of the deck hanger posts give >= 2 mm shin clearance while the posts still hold the deck?

The posts (x -37.5..-33.5, |y| 18.0..20.4, z -57.5..-35.5, solid, build_compact_battery.py) are the only link between
the lower deck and the rest of the support (geometry.json: connectivity). For every walking frame whose exact gap to the
current support is below 2.5 mm (frames at >= 2.5 mm already clear 2 mm after any trim), this marks every post point
that lies within 2 mm (+ sample error) of a leg surface. Those points must be removed by any trim that clears 2 mm.
If at some height every point of the post section must be removed, the post is cut through and no trim works.
The same test runs on the outer strip of the deck next to each post (x -44..-22, |y| 12..17.95, z -57.5..-53.5),
because the shin also comes within 2 mm of the deck edge there.

Usage: trim_feasibility.py            Writes trim-feasibility.json.
Leg surfaces: for every leg triangle that comes near the test region in a considered frame, a barycentric point grid
with spacing <= 0.35 mm (any surface point lies within 0.35/sqrt(3) = 0.21 mm of a grid point; that error is added to
the threshold). Test grids: cell centres, 0.2 mm pitch in x and y, 0.5 mm in z.
"""
import gc
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pso_lib as L

SP = 0.35; ERR = SP / np.sqrt(3); THR = 2.0 + ERR
src = L.walking_sources(); trace = np.load(L.SCRATCH / 'walk_trace.npy')
adopted = np.array([not s['fell'] and not s['blend'] for s in src])[trace]
final = np.array([s['file'].startswith('phase1-candidate-') for s in src])[trace]
delay = np.array([s['sensor_delay_ticks'] == 2 for s in src])[trace]
kp300 = np.array([(s.get('kp') or 0) >= 300 for s in src])[trace]
GROUPS = {'finalController': final, 'finalControllerNoSensorDelay': final & ~delay, 'adoptedExceptKp300': adopted & ~kp300,
          'adopted': adopted, 'all': np.ones_like(adopted)}

# poses and transforms first, then free the MuJoCo model
fk = L.FK()
POSES = {}
for side in ('left', 'right'):
    cfg = L.SIDE[side]; bodies = list(cfg['parts'])[2:]
    z = np.load(L.SCRATCH / f'reach-{side}-frames.npz'); ex = z['exact']; P = z['poses']
    idx = np.flatnonzero(ex < 2.5)
    POSES[side] = (idx, [{b: T for b, T in fk.part_T(dict(zip(cfg['joints'], map(float, P[i])))).items() if b in bodies} for i in idx])
del fk; gc.collect()

out = {'threshold_mm': THR, 'sampleSpacing_mm': SP, 'postBox': 'x -37.5..-33.5, |y| 18.0..20.4 (solid)',
       'deckStrip': 'x -44..-22, |y| 12..17.95, z -57.5..-53.5'}
pxs = np.arange(-37.4, -33.5, 0.2); pys = np.arange(18.1, 20.4, 0.2); pzs = np.arange(-57.25, -35.7, 0.5)
dxs = np.arange(-43.9, -22.0, 0.2); dys = np.arange(12.1, 17.95, 0.2); dzs = np.arange(-57.25, -53.4, 0.5)
cell = 0.2 * 0.2
for side in ('left', 'right'):
    s = 1.0 if side == 'left' else -1.0
    GP = np.stack(np.meshgrid(pxs, s * pys, pzs, indexing='ij'), -1).reshape(-1, 3)
    GD = np.stack(np.meshgrid(dxs, s * dys, dzs, indexing='ij'), -1).reshape(-1, 3)
    G = np.vstack([GP, GD]); nP = len(GP)
    cfg = L.SIDE[side]; bodies = list(cfg['parts'])[2:]
    idx, PTs = POSES[side]
    must = {g: np.zeros(len(G), bool) for g in GROUPS}
    lo = G.min(0) - THR - 1; hi = G.max(0) + THR + 1
    samples = []
    for b in bodies:
        for k in cfg['parts'][b]:
            v, f = L.solid(k); v = np.asarray(v, float); f = np.asarray(f, np.int64)
            near = np.zeros(len(f), bool)
            for PT in PTs:
                T = PT[b]; V = v @ T[:3, :3].T + T[:3, 3]; tri = V[f]
                near |= np.all((tri.max(1) >= lo) & (tri.min(1) <= hi), 1)
            if not near.any():
                continue
            pts = []
            for tri in v[f[near]]:
                L_ = max(np.linalg.norm(tri[0] - tri[1]), np.linalg.norm(tri[1] - tri[2]), np.linalg.norm(tri[2] - tri[0]))
                n = max(1, int(np.ceil(L_ / SP)))
                ij = np.array([(i, j) for i in range(n + 1) for j in range(n + 1 - i)], float) / n
                pts.append(np.c_[1 - ij.sum(1), ij] @ tri)
            samples.append((b, np.unique(np.vstack(pts).round(4), axis=0)))
    out.setdefault('legSamplesNearRegion', {})[side] = int(sum(len(S) for _, S in samples))
    for n_, i in enumerate(idx):
        X = []
        for b, S in samples:
            T = PTs[n_][b]; Y = S @ T[:3, :3].T + T[:3, 3]
            X.append(Y[np.all((Y >= lo) & (Y <= hi), 1)])
        X = np.vstack(X) if X else np.zeros((0, 3))
        if not len(X):
            continue
        d, _ = cKDTree(X).query(G, distance_upper_bound=THR)
        hit = d < THR
        for g, m in GROUPS.items():
            if m[i]:
                must[g] |= hit
    res = {'framesConsidered': int(len(idx))}
    nx, ny, nz = len(pxs), len(pys), len(pzs)
    for g in GROUPS:
        M = must[g][:nP].reshape(nx, ny, nz)
        keep_area = (~M).sum((0, 1)) * cell
        j = int(np.argmin(keep_area))
        MD = must[g][nP:]
        res[g] = dict(frames=int(sum(1 for i in idx if GROUPS[g][i])), postSectionFull_mm2=round(float(nx * ny * cell), 3),
                      postMinRemainingSection_mm2=round(float(keep_area[j]), 3), postAtZ=float(pzs[j]),
                      postZLevelsCutThrough=[float(zz) for zz, a in zip(pzs, keep_area) if a == 0],
                      postRemovedFraction_max=round(float(1 - keep_area.min() / (nx * ny * cell)), 3),
                      postMustRemoveBounds=[GP[must[g][:nP]].min(0).round(2).tolist(), GP[must[g][:nP]].max(0).round(2).tolist()] if M.any() else None,
                      postRemainingSectionByZ={float(zz): round(float(a), 3) for zz, a in zip(pzs[::4], keep_area[::4])},
                      deckMustRemovePoints=int(MD.sum()),
                      deckMustRemoveBounds=[GD[MD].min(0).round(2).tolist(), GD[MD].max(0).round(2).tolist()] if MD.any() else None,
                      deckMustRemoveInnermostAbsY=round(float(np.abs(GD[MD][:, 1]).min()), 2) if MD.any() else None)
    out[side] = res
    print(side, json.dumps({g: {k: res[g][k] for k in ('frames', 'postMinRemainingSection_mm2', 'postAtZ', 'postMustRemoveBounds',
                                                        'deckMustRemoveBounds', 'deckMustRemoveInnermostAbsY')} for g in GROUPS}), flush=True)
L.jdump(out, Path(__file__).with_name('trim-feasibility.json'))
