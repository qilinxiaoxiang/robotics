#!/usr/bin/env python3
"""Free translation of one part before it meets any listed neighbour, per direction (+x..-z).

For direction d, surface points whose outward normal has component > 0.35 along d cast a ray along d; the travel
before a neighbour is hit is that point's free play. The minimum over points is the part's free travel in d
(ignoring rotation and friction). 'none within 30 mm' means nothing stops it in that direction.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import geom

DIRS = {'+x': [1, 0, 0], '-x': [-1, 0, 0], '+y': [0, 1, 0], '-y': [0, -1, 0], '+z': [0, 0, 1], '-z': [0, 0, -1]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kind', default='full')
    ap.add_argument('--out', required=True)
    ap.add_argument('--part', required=True)
    ap.add_argument('--neighbours', default='', help='comma list; default = every cached part except screw display models')
    ap.add_argument('--exclude', default='', help='comma list of parts to ignore (e.g. a part moving with this one)')
    ap.add_argument('--n', type=int, default=6000)
    a = ap.parse_args()
    m = geom.mesh(a.part, a.kind)
    pts, fi = m.sample(a.n, return_index=True)
    nrm = m.face_normals[fi]
    lo, hi = m.bounds[0] - 30, m.bounds[1] + 30
    res = {}
    for name, d in DIRS.items():
        d = np.array(d, float)
        sel = nrm @ d > 0.35
        P = pts[sel] + 0.02 * d
        best = np.full(len(P), np.inf); who = np.array([''] * len(P), dtype=object)
        neigh = a.neighbours.split(',') if a.neighbours else [k for k in geom.available(a.kind)
                                                                 if not k.startswith(('camera_clamp_screw_', 'speaker_mount_screw_')) and k != 'jaw_support_guide_pose']
        for q in neigh:
            if q == a.part or q in a.exclude.split(','):
                continue
            try:
                Q = geom.mesh(q, a.kind)
            except FileNotFoundError:
                continue
            if np.any(Q.bounds[1] < lo) or np.any(Q.bounds[0] > hi):
                continue
            locs, ri, ti = Q.ray.intersects_location(P, np.repeat(d[None], len(P), 0), multiple_hits=True)
            if len(locs):
                dist = (locs - P[ri]) @ d
                order = np.lexsort((dist, ri))
                ri, dist, ti = ri[order], dist[order], ti[order]
                first = np.r_[True, ri[1:] != ri[:-1]]
                ri, dist, ti = ri[first], dist[first], ti[first]
                # first face met within 1 mm is an exit face -> the start point is inside Q (overlap): no free travel.
                # Farther exit faces are treated as ordinary hits (some purchased-part hulls have inverted normals).
                dist = np.where((Q.face_normals[ti] @ d > 0) & (dist <= 1.0), 0.0, dist)
                upd = dist < best[ri]
                best[ri[upd]] = dist[upd]; who[ri[upd]] = q
        fin = np.isfinite(best) & (best <= 30)
        if fin.any():
            i = np.argmin(np.where(fin, best, np.inf))
            res[name] = {'freeTravelMm': round(float(best[i]), 2), 'stoppedBy': who[i], 'pointsStopped': int(fin.sum()), 'pointsTested': int(len(P))}
        else:
            res[name] = {'freeTravelMm': None, 'stoppedBy': None, 'pointsStopped': 0, 'pointsTested': int(len(P))}
    outp = Path(a.out)
    allr = json.loads(outp.read_text()) if outp.exists() else {}
    allr[a.part] = res
    outp.write_text(json.dumps(allr, indent=1))
    print(a.part, {k: (v['freeTravelMm'], v['stoppedBy']) for k, v in res.items()}, flush=True)


if __name__ == '__main__':
    main()
