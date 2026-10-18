"""Walking-leg sweep of the material option A+G adds outside the pack body (plug tails behind the cover, the wires on the
cover's back face and over its top edge): study-solids/added_outside_pack_A+G.stl. Same method and frames as
guide/print/rear-pack/pack_sweep2.py (copied; only the target solid and the output path change).
Usage: sweep_added.py <tag> <left|right>   (run under the bounded CAD runner)."""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import uart_lib as U  # noqa: F401  (puts pack_lib / pso_lib on sys.path)
import numpy as np, trimesh
from scipy import ndimage
from scipy.spatial import cKDTree
import pack_lib as P
import pso_lib as L

tag, side = sys.argv[1:3]
OUT = U.STUDY
t0 = time.time()
VS = 1.0; FERR = 0.866 + 0.866 + 0.35; MARGIN = 14.0; CL = 5.0
am = trimesh.load(U.STUDY / 'study-solids' / 'added_outside_pack_A+G.stl')
A = P.mesh_to_m(am)
H = A
pack = am
COMP = {'addedOutside': A}


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


FLD = field(pack)


def lookup(fld, X):
    lo, sh, F = fld
    idx = np.round((X - lo) / VS).astype(int)
    ok = np.all((idx >= 0) & (idx < sh), 1)
    d = np.full(len(X), 99.0, np.float32); d[ok] = F[idx[ok, 0], idx[ok, 1], idx[ok, 2]]
    return d


fk = L.FK(); cfg = L.SIDE[side]; J = cfg['joints']; bodies = list(cfg['parts'])
use_bodies = bodies[2:]
PARTS = []; cover = {}
for b in use_bodies:
    for k in cfg['parts'][b]:
        v, f = L.solid(k); m = trimesh.Trimesh(v, f, process=False)
        n = max(400, int(m.area / 0.25)); p, _ = trimesh.sample.sample_surface(m, n, seed=1); Pp = np.vstack([p, v])
        dense, _ = trimesh.sample.sample_surface(m, min(400000, n * 12), seed=7); cover[k] = float(cKDTree(Pp).query(dense)[0].max())
        key = np.floor(Pp / CL).astype(np.int64); _, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.ravel()
        o = np.argsort(inv, kind='stable'); Pp = Pp[o]; inv = inv[o]
        st = np.r_[0, np.flatnonzero(np.diff(inv)) + 1, len(inv)]
        Cc = np.array([(Pp[a:e].min(0) + Pp[a:e].max(0)) / 2 for a, e in zip(st[:-1], st[1:])])
        Rr = np.array([np.linalg.norm(Pp[a:e] - Cc[i], axis=1).max() for i, (a, e) in enumerate(zip(st[:-1], st[1:]))])
        PARTS.append(dict(key=k, body=b, P=Pp, starts=st, C=Cc, R=Rr, man=L.to_m(v, f), mesh=m))
RCOV = max(cover.values()); T1 = 2.0 + FERR + RCOV
iT0 = {b: np.linalg.inv(fk.T0[b]) for b in use_bodies}
Q = np.load(L.SCRATCH / 'walk_qpos.npy'); trace = np.load(L.SCRATCH / 'walk_trace.npy'); frame = np.load(L.SCRATCH / 'walk_frame.npy')
src = L.walking_sources(); adopted = np.array([not s['fell'] and not s['blend'] for s in src])[trace]
N = len(Q); M_, D_ = fk.M, fk.D; tb = M_.body('trunk_base').id; bid = {b: M_.body(b).id for b in use_bodies}
print(f'[{tag}/{side}] setup {time.time()-t0:.1f}s; frames {N}, adopted {int(adopted.sum())}, T1 {T1:.3f}, pack bounds {np.round(pack.bounds,1).tolist()}', flush=True)


def body_T(i, blist, iT0d, bidd):
    D_.qpos[:] = M_.qpos0
    for j in J:
        D_.qpos[fk.qadr[j]] = Q[i, fk.qadr[j]]
    fk.mj.mj_kinematics(M_, D_)
    R0 = D_.xmat[tb].reshape(3, 3); p0 = D_.xpos[tb]; out = {}
    for b in blist:
        k = bidd[b]; T = np.eye(4); T[:3, :3] = R0.T @ D_.xmat[k].reshape(3, 3); T[:3, 3] = R0.T @ (D_.xpos[k] - p0) * 1000.0
        out[b] = T @ iT0d[b]
    return out


part_T = lambda i: body_T(i, use_bodies, iT0, bid)
coarse = np.full(N, 99.0, np.float32); cpart = {}
for i in range(N):
    PT = part_T(i); best_d = 99.0
    for pr in PARTS:
        Mx = PT[pr['body']]; Rm = Mx[:3, :3]; tv = Mx[:3, 3]
        Cw = pr['C'] @ Rm.T + tv
        live = np.flatnonzero(lookup(FLD, Cw) - pr['R'] < T1)
        if not len(live):
            continue
        st_ = pr['starts']; sel = np.concatenate([np.arange(st_[c], st_[c + 1]) for c in live])
        X = pr['P'][sel] @ Rm.T + tv
        d = float(lookup(FLD, X).min()); best_d = min(best_d, d)
        if d < T1:
            cpart.setdefault(i, []).append(pr['key'])
    coarse[i] = best_d
flag = sorted(cpart)
print(f'stage1 done {time.time()-t0:.1f}s; flagged {len(flag)}', flush=True)
exact = np.full(N, 99.0); epart = {}
PM = {pr['key']: (pr['body'], pr['man']) for pr in PARTS}
for n_, i in enumerate(flag):
    PT = part_T(i)
    for k in cpart[i]:
        b, m = PM[k]
        g = m.transform(np.asarray(PT[b][:3, :4])).min_gap(H, 8.0)
        if g < exact[i]:
            exact[i] = g; epart[i] = k
print(f'stage2 done {time.time()-t0:.1f}s', flush=True)
hip_bodies = bodies[:2]; hip_parts = [(b, k, L.to_m(*L.solid(k))) for b in hip_bodies for k in cfg['parts'][b]]
iT0h = {b: np.linalg.inv(fk.T0[b]) for b in hip_bodies}; bidh = {b: M_.body(b).id for b in hip_bodies}
yr = np.round(Q[:, [fk.qadr[J[0]], fk.qadr[J[1]]]] / 0.005) * 0.005
uniq, inv = np.unique(yr, axis=0, return_inverse=True); inv = inv.ravel()
hip_gap = np.full(len(uniq), 99.0); hip_part = {}
for u, (yaw, roll) in enumerate(uniq):
    D_.qpos[:] = M_.qpos0; D_.qpos[fk.qadr[J[0]]] = yaw; D_.qpos[fk.qadr[J[1]]] = roll
    fk.mj.mj_kinematics(M_, D_); R0 = D_.xmat[tb].reshape(3, 3); p0 = D_.xpos[tb]
    for b, k, m in hip_parts:
        T = np.eye(4); T[:3, :3] = R0.T @ D_.xmat[bidh[b]].reshape(3, 3); T[:3, 3] = R0.T @ (D_.xpos[bidh[b]] - p0) * 1000.0
        g = m.transform(np.asarray((T @ iT0h[b])[:3, :4])).min_gap(H, 8.0)
        if g < hip_gap[u]:
            hip_gap[u] = g; hip_part[u] = k
hip_frame_gap = hip_gap[inv]
print(f'hip grid done {len(uniq)} poses {time.time()-t0:.1f}s', flush=True)
ex = np.where(exact < 99, exact, np.minimum(coarse, 99.0))


def attribute(i, k):
    b, m = PM[k]; T = part_T(i)[b]; man = m.transform(np.asarray(T[:3, :4]))
    comp = {name: float(man.min_gap(cm_, 12.0)) for name, cm_ in COMP.items()}
    pen = float((man ^ H).volume())
    pm = [p for p in PARTS if p['key'] == k][0]['mesh'].copy(); pm.apply_transform(T)
    V = pm.vertices; near = np.all((V >= pack.bounds[0] - 12) & (V <= pack.bounds[1] + 12), axis=1)
    V = V[near] if near.any() else V
    if len(V) > 4000:
        V = V[np.random.default_rng(0).choice(len(V), 4000, replace=False)]
    _, d, _ = trimesh.proximity.closest_point(pack, V); j = int(np.argmin(d))
    return {'closestComponent': min(comp, key=comp.get), 'componentGaps': {kk: round(vv, 3) for kk, vv in sorted(comp.items(), key=lambda t: t[1])},
            'penetrationVolumeMm3': round(pen, 3), 'closestLegPointXYZ': np.round(V[j], 2).tolist(), 'vertexGap': round(float(d[j]), 3),
            'note': 'closest point from a subset of the leg vertices (memory bound); minGapMm is the exact manifold value'}


def summary(mask):
    sel = np.flatnonzero(mask); i = int(sel[np.argmin(ex[sel])])
    hsel = hip_frame_gap[sel]; hi = int(sel[np.argmin(hsel)])
    k = epart.get(i) or (cpart[i][0] if i in cpart else None)
    d = {'frames': int(len(sel)),
         'pitchChain': {'minGapMm': float(ex[i]), 'exactChecked': bool(i in epart), 'worstGlobalFrame': i, 'worstFile': src[trace[i]]['file'],
                        'worstFrameInRun': int(frame[i]), 'worstPart': k, 'label': L.LABEL.get(k) if k else None,
                        'framesUnder1': int((ex[sel] < 1).sum()), 'framesUnder2': int((ex[sel] < 2).sum()), 'framesUnder3': int((ex[sel] < 3).sum()),
                        'q': {j: float(Q[i, fk.qadr[j]]) for j in J}},
         'hipBodies': {'minGapMm': float(hsel.min()), 'worstGlobalFrame': hi, 'worstFile': src[trace[hi]]['file'], 'worstFrameInRun': int(frame[hi]),
                       'worstPart': hip_part.get(int(inv[hi]))}}
    if k and ex[i] < 8:
        d['pitchChain']['attribution'] = attribute(i, k)
    hk = hip_part.get(int(inv[hi]))
    if hk and hsel.min() < 8:
        b = [bb for bb in hip_bodies if hk in cfg['parts'][bb]][0]; m = [mm for (bb, kk, mm) in hip_parts if kk == hk][0]
        D_.qpos[:] = M_.qpos0; D_.qpos[fk.qadr[J[0]]] = Q[hi, fk.qadr[J[0]]]; D_.qpos[fk.qadr[J[1]]] = Q[hi, fk.qadr[J[1]]]
        fk.mj.mj_kinematics(M_, D_); R0 = D_.xmat[tb].reshape(3, 3); p0 = D_.xpos[tb]
        T = np.eye(4); T[:3, :3] = R0.T @ D_.xmat[bidh[b]].reshape(3, 3); T[:3, 3] = R0.T @ (D_.xpos[bidh[b]] - p0) * 1000.0
        man = m.transform(np.asarray((T @ iT0h[b])[:3, :4]))
        d['hipBodies']['componentGaps'] = {name: round(float(man.min_gap(cm_, 12.0)), 3) for name, cm_ in COMP.items()}
    return d


res = {'tag': tag, 'side': side, 'packParts': ['study-solids/added_outside_pack_A+G.stl'], 'packBounds': pack.bounds.tolist(),
       'addedVolumeMm3': round(float(pack.volume), 2), 'T1': T1, 'legCoverRadiusMm': cover, 'flagged': len(flag),
       'adopted': summary(adopted), 'allFramesIncludingExcludedRuns': summary(np.ones(N, bool))}
res['elapsed_s'] = round(time.time() - t0, 1)
json.dump(res, open(OUT / f'sweep-{tag}-{side}.json', 'w'), indent=1)
print('DONE', json.dumps(res['adopted']), flush=True)
