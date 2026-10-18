#!/usr/bin/env python3
"""Check the guide-part -> MJCF-body assignment and the joint frames used by the route study.

1. Joint anchors and axes at q = 0 in the robot frame (MJCF).
2. For each body, the bounds of its guide parts next to the bounds of the MJCF visual meshes of that body.
3. Rigid-motion check: for every neck joint at several angles, the exact overlap volume (manifold3d) between all parts
   distal to the joint and all parts proximal to it. With a correct assignment and frame the overlap stays at its q = 0
   value inside the range the policy uses; growth only at range ends marks a hard stop of the real mechanism.
Writes kin-check.json.
"""
import sys

import numpy as np

sys.path.insert(0, __import__('os').path.dirname(__file__))
from nr_lib import BODY_ORDER, FK, HERE, JOINTS, body_of, ia_lib, jdump, load_solid, rnd  # noqa: E402

TRAINED = {'neck_pitch': (-22.6, 39.8), 'head_pitch': (5.9, 68.2), 'head_yaw': (-24.6, 34.0), 'head_roll': (-21.4, 9.9)}
fk = FK()
g = ia_lib.load_guide()
keys = [p['key'] for p in g['parts'] if body_of(p['key']) is not None and p['key'] != 'head_cap'] + ['head_cap_nonotch']
by_body = {b: [] for b in BODY_ORDER}
for k in keys:
    by_body[body_of(k.replace('_nonotch', ''))].append(k)
PARTS = {b: [] for b in BODY_ORDER}           # (key, manifold, vertices) per body; no unions (memory)
for b, ks in by_body.items():
    for k in ks:
        v, f = load_solid(k)
        if v[:, 2].max() < 15:          # torso parts below the neck are irrelevant here
            continue
        PARTS[b].append((k, ia_lib.to_manifold(v, f), v))


def bounds_of(b):
    if not PARTS[b]:
        return None
    V = np.vstack([v for _, _, v in PARTS[b]])
    return rnd([V.min(0), V.max(0)], 1)


def overlap(prox, dist, Tq):
    """Sum of exact pairwise intersection volumes between parts on the two body sets (bounding boxes prefiltered)."""
    A = [(k, m.transform(np.ascontiguousarray(Tq[b][:3, :])), v @ Tq[b][:3, :3].T + Tq[b][:3, 3]) for b in prox for k, m, v in PARTS[b]]
    B = [(k, m.transform(np.ascontiguousarray(Tq[b][:3, :])), v @ Tq[b][:3, :3].T + Tq[b][:3, 3]) for b in dist for k, m, v in PARTS[b]]
    tot, pairs = 0.0, []
    for ka, ma, va in A:
        la, ha = va.min(0), va.max(0)
        for kb, mb, vb in B:
            if (vb.min(0) > ha).any() or (vb.max(0) < la).any():
                continue
            vol = (ma ^ mb).volume()
            if vol > 1e-3:
                tot += vol
                pairs.append((ka, kb, round(vol, 2)))
    return tot, sorted(pairs, key=lambda x: -x[2])[:4]


# MJCF visual mesh bounds per body in the robot frame
mj, M, D = fk.mj, fk.M, fk.D
D.qpos[:] = M.qpos0
mj.mj_kinematics(M, D)
tb = M.body('trunk_base').id
R0, p0 = D.xmat[tb].reshape(3, 3), D.xpos[tb]
mjb = {}
for gi in range(M.ngeom):
    b = M.body(M.geom_bodyid[gi]).name
    if b not in BODY_ORDER or M.geom_dataid[gi] < 0:
        continue
    mid = M.geom_dataid[gi]
    V = M.mesh_vert[M.mesh_vertadr[mid]:M.mesh_vertadr[mid] + M.mesh_vertnum[mid]]
    W = (D.geom_xmat[gi].reshape(3, 3) @ V.T).T + D.geom_xpos[gi]
    W = (R0.T @ (W - p0).T).T * 1000
    if W[:, 2].max() < 15:
        continue
    lo, hi = mjb.get(b, (np.full(3, 1e9), np.full(3, -1e9)))
    mjb[b] = (np.minimum(lo, W.min(0)), np.maximum(hi, W.max(0)))

an = fk.anchors()
res = {'jointsAtQ0': {j: {'anchorMm': rnd(a, 2), 'axis': rnd(x, 4), 'mjcfRangeDeg': rnd(np.degrees(fk.range[j]), 1),
                          'policyTraceQposRangeDeg': TRAINED[j]} for j, (a, x) in an.items()},
       'bodies': {b: {'parts': by_body[b], 'guideBoundsMm': bounds_of(b),
                      'mjcfVisualBoundsMm': rnd(mjb[b], 1) if b in mjb else None} for b in BODY_ORDER},
       'sweeps': []}


for ji, j in enumerate(JOINTS):
    prox = BODY_ORDER[:ji + 1]
    dist = BODY_ORDER[ji + 1:]
    lo, hi = np.degrees(fk.range[j])
    angs = sorted(set([0.0, TRAINED[j][0], TRAINED[j][1], round(lo, 1), round(hi, 1), round(lo / 2, 1), round(hi / 2, 1)]))
    for a in angs:
        Tq = fk.part_T({j: np.radians(a)})
        vol, top = overlap(prox, dist, Tq)
        res['sweeps'].append({'joint': j, 'deg': a, 'overlapProximalVsDistalMm3': rnd(vol, 2), 'largestPairs': top,
                              'inPolicyRange': bool(TRAINED[j][0] - 1e-6 <= a <= TRAINED[j][1] + 1e-6)})
        print(j, a, round(vol, 2), top[:2], flush=True)
# Jaw about its pivot against the rest of the head
for a in (0, 10, 20, 30, 40):
    Tq = fk.part_T({'jaw': a})
    vol, top = overlap(['jaw_soft'], ['jaw'], Tq)
    res['sweeps'].append({'joint': 'jaw', 'deg': a, 'overlapProximalVsDistalMm3': rnd(vol, 2), 'largestPairs': top})
    print('jaw', a, round(vol, 2), top[:2], flush=True)
jdump(res, HERE / 'kin-check.json')
