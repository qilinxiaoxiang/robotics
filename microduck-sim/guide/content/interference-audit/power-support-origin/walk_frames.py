"""Collect the phase-1 walking frames and check that guide leg parts sit at MJCF qpos0.
Writes walk-frames.json (sources, joint stats) and SCRATCH/walk_qpos.npy (all frames, 21-wide qpos)."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pso_lib as L

src = L.walking_sources()
Q = []; meta = []
for s in src:
    d = json.loads((L.PHASE1 / s['file']).read_text())
    q = np.array([r['qpos'] for r in d['rows']], float)
    Q.append(q)
Qall = np.vstack(Q)
trace = np.concatenate([[i] * len(q) for i, q in enumerate(Q)])
frame = np.concatenate([np.arange(len(q)) for q in Q])
adopted_trace = np.array([not s['fell'] and not s['blend'] for s in src])
adopted = adopted_trace[trace]
np.save(L.SCRATCH / 'walk_qpos.npy', Qall)
np.save(L.SCRATCH / 'walk_trace.npy', trace)
np.save(L.SCRATCH / 'walk_frame.npy', frame)

fk = L.FK()
names = [n for n in fk.jnames]
# qpos layout check: free joint (7) + 14 hinge joints in model order
order = [n for n in names if fk.M.joint(n).type != 0]
assert fk.M.nq == Qall.shape[1], (fk.M.nq, Qall.shape)
stats = {}
for j in order:
    a = Qall[adopted, fk.qadr[j]]
    stats[j] = dict(min=round(float(a.min()), 4), p005=round(float(np.percentile(a, 0.5)), 4), median=round(float(np.median(a)), 4),
                    p995=round(float(np.percentile(a, 99.5)), 4), max=round(float(a.max()), 4),
                    range=[round(float(x), 4) for x in fk.M.jnt_range[fk.M.joint(j).id]])

# qpos0 check: ring centres vs joint anchors, ring thin axis vs joint axis
ring = {'left_hip_pitch': 'ring8', 'left_knee': 'ring7', 'left_ankle': 'smallring', 'left_hip_roll': 'ring9',
        'right_hip_pitch': 'ring3', 'right_knee': 'ring2', 'right_ankle': 'right_smallring', 'right_hip_roll': 'ring4'}
check = {}
for j, k in ring.items():
    v, f = L.solid(k)
    c = (v.min(0) + v.max(0)) / 2; ext = v.max(0) - v.min(0)
    a, ax = fk.anchor(j)
    # perpendicular distance from ring centre to the joint axis
    d = c - a; perp = np.linalg.norm(d - np.dot(d, ax) * ax)
    check[j] = dict(ring=k, ringCentre=c.round(3).tolist(), anchor=a.round(3).tolist(), axis=ax.round(3).tolist(),
                    ringThinAxis=int(np.argmin(ext)), perpDistMm=round(float(perp), 3))
# MJCF 'leg' collision mesh at qpos0 vs guide 'lower' (shin) bounds
import mujoco
M, D = fk.M, fk.D
D.qpos[:] = M.qpos0; mujoco.mj_kinematics(M, D)
tb = M.body('trunk_base').id; R0 = D.xmat[tb].reshape(3, 3); p0 = D.xpos[tb]
legb = {}
for g in range(M.ngeom):
    if M.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH:
        continue
    mid = M.geom_dataid[g]; name = M.mesh(mid).name; body = M.body(M.geom_bodyid[g]).name
    if name != 'leg':
        continue
    va, vn = M.mesh_vertadr[mid], M.mesh_vertnum[mid]
    X = ((M.mesh_vert[va:va + vn] @ D.geom_xmat[g].reshape(3, 3).T + D.geom_xpos[g]) - p0) @ R0 * 1000.0
    legb[body] = [X.min(0).round(2).tolist(), X.max(0).round(2).tolist()]
for k in ('lower', 'right_lower'):
    v, _ = L.solid(k); legb['guide_' + k] = [v.min(0).round(2).tolist(), v.max(0).round(2).tolist()]

out = dict(sources=src, totalFrames=int(len(Qall)), adoptedTraces=int(adopted_trace.sum()), adoptedFrames=int(adopted.sum()),
           excluded=[s['file'] for s in src if s['fell'] or s['blend']], qposWidth=int(Qall.shape[1]), hingeOrder=order,
           stats_adopted=stats, qpos0Check=check, shinMeshBounds=legb)
L.jdump(out, Path(__file__).with_name('walk-frames.json'))
print(json.dumps({k: v for k, v in out.items() if k != 'sources'}, indent=1))
