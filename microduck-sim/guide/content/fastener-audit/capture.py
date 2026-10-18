#!/usr/bin/env python3
"""Retention check for joints that have no screw: which neighbouring parts touch a part, and in which of the six
translation directions those contacts block it.

Method: sample points on the part surface (area weighted); from each point cast a 0.8 mm ray along the outward face
normal starting 0.25 mm inside. A hit on a neighbour (or a start point already inside it) within that range is a
contact. A contact whose outward normal has a component > 0.35 along +d blocks translation in +d. A part is captured
in translation when all six directions are blocked. Rotation is not assessed (inference only; see notes).
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import geom

DIRS = {'+x': [1, 0, 0], '-x': [-1, 0, 0], '+y': [0, 1, 0], '-y': [0, -1, 0], '+z': [0, 0, 1], '-z': [0, 0, -1]}


def contacts(part, neighbours, kind, n=8000, seed=1):
    m = geom.mesh(part, kind)
    pts, fi = m.sample(n, return_index=True, seed=seed) if 'seed' in m.sample.__code__.co_varnames else m.sample(n, return_index=True)
    nrm = m.face_normals[fi]
    out = {}
    for q in neighbours:
        if q == part:
            continue
        try:
            Q = geom.mesh(q, kind)
        except FileNotFoundError:
            continue
        lo, hi = m.bounds[0] - 1, m.bounds[1] + 1
        if np.any(Q.bounds[1] < lo) or np.any(Q.bounds[0] > hi):
            continue
        o = pts - 0.25 * nrm
        hit = np.zeros(len(pts), bool)
        locs, ri, _ = Q.ray.intersects_location(o, nrm, multiple_hits=False)
        if len(locs):
            dist = np.linalg.norm(locs - o[ri], axis=1)
            hit[ri[dist <= 0.8]] = True
        if not hit.any():
            continue
        blocks = {}
        for name, d in DIRS.items():
            comp = nrm[hit] @ np.array(d, float)
            blocks[name] = int((comp > 0.35).sum())
        out[q] = {'contactSamples': int(hit.sum()), 'blocks': blocks}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kind', default='full')
    ap.add_argument('--out', required=True)
    ap.add_argument('--part', action='append', required=True, help='part:neighbour1,neighbour2,...')
    a = ap.parse_args()
    outp = Path(a.out)
    res = json.loads(outp.read_text()) if outp.exists() else {}
    for spec in a.part:
        p, ns = spec.split(':')
        c = contacts(p, ns.split(','), a.kind)
        blocked = {name: sorted(q for q, v in c.items() if v['blocks'][name] >= 5) for name in DIRS}
        res[p] = {'neighbours': c, 'blockedBy': blocked, 'freeDirections': [k for k, v in blocked.items() if not v]}
        outp.write_text(json.dumps(res, indent=1))
        print(p, 'free:', res[p]['freeDirections'], {k: v for k, v in blocked.items()}, flush=True)


if __name__ == '__main__':
    main()
