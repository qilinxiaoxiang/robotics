#!/usr/bin/env python3
"""Where an inline 8-way disconnect fits below the head floor, and whether it stays clear over the neck and head motion.

The disconnect rides on the head-pitch bracket (MJCF body neck_pitch), on its -y side next to route A, so the head can
come off with its own short pigtail while the torso-side half stays tied to the bracket.
Envelope (an assumption, stated in the JSON): a mated pair of 2 x 5 Dupont crimp housings (2.54 mm pitch), cross-section
12.7 x 5.08 mm, mated body length 28 mm, plus 3 mm of straight wire at each end before the first bend (plug plus wire
exit), plus 0.5 mm clearance all round.
Steps:
  1. q = 0 placement search on the 0.5 mm occupancy grid with the existing cables (occ.py 'cables'): every box position
     (1 mm steps, 0.5 mm in y) and two orientations (long axis vertical, or long axis along x) lying flat against the
     outside of the bracket's -y plate (inner face 1.5-2 mm outboard of the plate, clear of the screw heads); keep boxes
     whose voxels are all free; take up to 8 distinct ones nearest the head-pitch axis.
  2. Exact check of the best candidates: the box (a manifold cube) moves with neck_pitch; at every pose of the policy,
     pickup, single-joint MJCF and yaw-sweep sets, exact manifold intersection volume with every part on another body
     (bounding-box prefilter) and the exact smallest gap (Manifold.min_gap, 8 mm search) to those parts; at q = 0 also the
     intersection with neck_pitch's own parts and the smallest distance to the existing cable centrelines.
Writes disconnect.json and study-solids/disconnect-envelope.stl (the chosen box at q = 0; a study solid, not a print).
"""
import json
import sys
import time

import numpy as np
import manifold3d as m3
import trimesh

sys.path.insert(0, __import__('os').path.dirname(__file__))
from nr_lib import FK, HERE, SCRATCH, body_of, cable_tubes, ia_lib, jdump, load_solid, rnd  # noqa: E402
from motion import pose_sets  # noqa: E402

ENV = {'name': 'Dupont 2x5 mated pair (female crimp housing on the head pigtail, male crimp housing on the torso side)',
       'crossSectionMm': [12.7, 5.08], 'matedLengthMm': 28.0, 'wireExitMm': 3.0, 'clearanceMm': 0.5,
       'basis': 'nominal 2.54 mm pitch housing outline; mated length and wire exit are assumptions (inference), '
                'check against the housings actually bought'}
L_ALONG = ENV['matedLengthMm'] + 2 * ENV['wireExitMm'] + 2 * ENV['clearanceMm']
W = ENV['crossSectionMm'][0] + 2 * ENV['clearanceMm']
TK = ENV['crossSectionMm'][1] + 2 * ENV['clearanceMm']
ORIENT = {'vertical': np.array([W, TK, L_ALONG]), 'along-x': np.array([L_ALONG, TK, W])}
SEARCH_LO = np.array([0.0, -34.0, 55.0])
SEARCH_HI = np.array([55.0, -14.0, 98.0])
# The box must lie flat against the outside of the bracket's -y side plate (outer face y = -17.5), just clear of the four
# M2 screw heads (1.5 mm high): its inner face between y -19.5 and -19.0.
INNER_FACE = (-19.5, -19.0)
AXIS_PT = np.array([26.0, -19.0, 82.42])     # head-pitch axis where it leaves the -y plate


def placement_search():
    d = np.load(SCRATCH / 'occ-nonotch-cables.npz')
    occ = d['occ'] > 0
    lo, p = d['lo'], float(d['pitch'])
    # summed-volume table for O(1) box occupancy counts
    S = np.zeros(tuple(np.array(occ.shape) + 1), np.int32)
    S[1:, 1:, 1:] = occ.cumsum(0).cumsum(1).cumsum(2)

    def count(i0, i1):
        a, b, c = i0
        x, y, z = i1
        return (S[x, y, z] - S[a, y, z] - S[x, b, z] - S[x, y, c] + S[a, b, z] + S[a, y, c] + S[x, b, c] - S[a, b, c])

    cands = []
    for oname, size in ORIENT.items():
        for x in np.arange(SEARCH_LO[0], SEARCH_HI[0] - size[0] + 1e-6, 1.0):
            for y in np.arange(SEARCH_LO[1], SEARCH_HI[1] - size[1] + 1e-6, 0.5):
                for z in np.arange(SEARCH_LO[2], SEARCH_HI[2] - size[2] + 1e-6, 1.0):
                    bl = np.array([x, y, z])
                    i0 = np.floor((bl - lo) / p).astype(int)
                    i1 = np.ceil((bl + size - lo) / p).astype(int) + 1
                    if not (INNER_FACE[0] <= y + size[1] <= INNER_FACE[1]):
                        continue
                    if count(i0, i1) == 0:
                        c = bl + size / 2
                        cands.append((oname, bl, size, c))
    # rank: nearest to the head-pitch axis (least motion relative to the neck below it)
    cands.sort(key=lambda t: np.linalg.norm(t[3] - AXIS_PT))
    return cands


def cube(bl, size):
    return m3.Manifold.cube(size.tolist()).translate(bl.tolist())


def transform(man, T):
    return man.transform(T[:3, :].tolist())


def main():
    t0 = time.time()
    cands = placement_search()
    print(len(cands), 'free q0 boxes', f'{time.time() - t0:.0f}s', flush=True)
    # several distinct candidates (different orientation or > 4 mm apart)
    picked = []
    for c in cands:
        if all(c[0] != p[0] or np.linalg.norm(c[3] - p[3]) > 4 for p in picked):
            picked.append(c)
        if len(picked) >= 8:
            break
    fk = FK()
    sets = pose_sets(fk)
    g = ia_lib.load_guide()
    keys = [p['key'] for p in g['parts'] if body_of(p['key']) is not None and p['key'] != 'head_cap'] + ['head_cap_nonotch']
    parts = []
    for k in keys:
        v, f = load_solid(k)
        if v[:, 2].max() < 35 or v[:, 2].min() > 150:
            continue
        parts.append((k, body_of(k.replace('_nonotch', '')), ia_lib.to_manifold(v, f), v.min(0), v.max(0)))
    tubes = cable_tubes(0.25)
    out = {'_method': __doc__.strip(), 'envelope': ENV, 'envelopeBoxMm': {k: v.tolist() for k, v in ORIENT.items()},
           'searchBoxMm': [SEARCH_LO.tolist(), SEARCH_HI.tolist()], 'freeQ0Boxes': len(cands), 'candidates': []}
    for oname, bl, size, ctr in picked:
        box = cube(bl, size)
        rec = {'orientation': oname, 'minCornerQ0': rnd(bl, 2), 'sizeMm': rnd(size, 2), 'centreQ0': rnd(ctr, 2), 'sets': {}}
        # q = 0: own-body parts and cables
        own = [(k, float((box ^ m).volume())) for k, b, m, lo, hi in parts if b == 'neck_pitch' and ia_lib.aabb_overlap((bl, bl + size), (lo, hi), 0.1)]
        rec['q0OwnBodyOverlapMm3'] = rnd(sum(v for _, v in own), 4)
        cd = {}
        for cid, pts, r in tubes:
            dd = np.linalg.norm(np.maximum(0, np.maximum(bl - pts, pts - (bl + size))), axis=1).min() - r
            cd[cid] = rnd(dd, 2)
        rec['q0CableSurfaceGapMm'] = cd
        for sname, poses in sets.items():
            worst_vol, min_gap, gap_part, gap_pose, hits = 0.0, np.inf, None, None, []
            for q in poses:
                T = fk.part_T(q)
                bx = transform(box, T['neck_pitch'])
                Tn = T['neck_pitch']
                bc = np.array([[a, c, e] for a in (bl[0], bl[0] + size[0]) for c in (bl[1], bl[1] + size[1]) for e in (bl[2], bl[2] + size[2])])
                bw = bc @ Tn[:3, :3].T + Tn[:3, 3]
                blo, bhi = bw.min(0), bw.max(0)
                for k, b, m, lo, hi in parts:
                    if b == 'neck_pitch':
                        continue
                    Tb = T[b]
                    corners = np.array([[a, c, e] for a in (lo[0], hi[0]) for c in (lo[1], hi[1]) for e in (lo[2], hi[2])])
                    wc = corners @ Tb[:3, :3].T + Tb[:3, 3]
                    wlo, whi = wc.min(0), wc.max(0)
                    if not ia_lib.aabb_overlap((blo, bhi), (wlo, whi), 8.0):
                        continue
                    pm = transform(m, Tb)
                    vol = float((bx ^ pm).volume())
                    if vol > 1e-6:
                        hits.append({'part': k, 'volumeMm3': rnd(vol, 3),
                                     'poseDeg': {a: rnd(np.degrees(x) if a != 'jaw' else x, 1) for a, x in q.items()}})
                        worst_vol = max(worst_vol, vol)
                        gap = 0.0
                    else:
                        gap = float(bx.min_gap(pm, 8.0))
                    if gap < min_gap:
                        min_gap, gap_part, gap_pose = gap, k, q
            rec['sets'][sname] = {'poses': len(poses), 'overlapPoses': len({json.dumps(h['poseDeg']) for h in hits}),
                                  'worstOverlapMm3': rnd(worst_vol, 3), 'overlapExamples': hits[:6],
                                  'minGapMm': rnd(min(min_gap, 8.0), 2), 'minGapPart': gap_part,
                                  'minGapPoseDeg': {a: rnd(np.degrees(x) if a != 'jaw' else x, 1) for a, x in (gap_pose or {}).items()}}
            print(oname, rnd(ctr, 1), sname, 'overlap poses', rec['sets'][sname]['overlapPoses'], 'min gap',
                  rec['sets'][sname]['minGapMm'], gap_part, f'{time.time() - t0:.0f}s', flush=True)
        rec['clearAllSets'] = all(s['overlapPoses'] == 0 for s in rec['sets'].values()) and rec['q0OwnBodyOverlapMm3'] == 0
        rec['clearPolicyAndPickup'] = all(rec['sets'][s]['overlapPoses'] == 0 for s in ('policy', 'pickup')) and rec['q0OwnBodyOverlapMm3'] == 0
        out['candidates'].append(rec)
        jdump(out, HERE / 'disconnect.json')
    best = next((c for c in out['candidates'] if c['clearAllSets']), None) or next((c for c in out['candidates'] if c['clearPolicyAndPickup']), None)
    out['chosen'] = best
    if best:
        bl, size = np.array(best['minCornerQ0']), np.array(best['sizeMm'])
        v, f = ia_lib.from_manifold(cube(bl, size))
        (HERE / 'study-solids').mkdir(exist_ok=True)
        trimesh.Trimesh(v, f).export(HERE / 'study-solids' / 'disconnect-envelope.stl')
    jdump(out, HERE / 'disconnect.json')


if __name__ == '__main__':
    main()
