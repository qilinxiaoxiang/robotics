#!/usr/bin/env python3
"""Inventory small round holes (1.0-3.8 mm) in printed parts and boards by slicing along x, y and z.

A hole is a void face (odd containment depth) in a planar section with area-equivalent diameter 1.0-3.8 mm and
circularity >= 0.7, tracked across consecutive 0.4 mm slices. Output: holes per part with centre at both ends,
axis, depth range and diameter profile.
"""
import argparse, json, math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import geom

AXES = {'x': (1, 0, 0), 'y': (0, 1, 0), 'z': (0, 0, 1)}


def inventory(key, kind='full', step=0.4, dmin=1.0, dmax=3.8, extra_axes=()):
    m = geom.mesh(key, kind)
    lo, hi = m.bounds
    holes = []
    axes = list(AXES.items()) + list(extra_axes)
    for name, ax in axes:
        ax = np.asarray(ax, float); ax /= np.linalg.norm(ax)
        u, v, a = geom.frame(ax)
        proj = m.vertices @ a
        hs = np.arange(proj.min() + step / 2, proj.max(), step)
        secs = geom.section_polys(m, np.zeros(3), a, hs, u, v)
        tracks = []  # each: dict(h list, c list, d list)
        open_tracks = []
        for h, polys in zip(hs, secs):
            found = []
            for p, depth in polys:
                if depth % 2 == 0:
                    continue
                A = p.area; P = p.exterior.length
                if A <= 0:
                    continue
                d = 2 * math.sqrt(A / math.pi)
                circ = 4 * math.pi * A / (P * P)
                if dmin <= d <= dmax and circ >= 0.7:
                    c = p.centroid
                    found.append((c.x, c.y, d, circ))
            nxt = []
            for cx, cy, d, circ in found:
                best = None
                for t in open_tracks:
                    pc = t['c'][-1]
                    dist = math.hypot(cx - pc[0], cy - pc[1])
                    if dist < 0.35 and (best is None or dist < best[0]):
                        best = (dist, t)
                if best:
                    t = best[1]; open_tracks.remove(t)
                else:
                    t = {'h': [], 'c': [], 'd': [], 'circ': []}; tracks.append(t)
                t['h'].append(float(h)); t['c'].append((cx, cy)); t['d'].append(d); t['circ'].append(circ)
                nxt.append(t)
            open_tracks = nxt
        for t in tracks:
            if len(t['h']) < 2:
                continue
            c0 = np.array(t['c'][0]); c1 = np.array(t['c'][-1])
            p0 = c0[0] * u + c0[1] * v + t['h'][0] * a
            p1 = c1[0] * u + c1[1] * v + t['h'][-1] * a
            d = np.array(t['d'])
            holes.append({'axis': name if name in AXES else [round(x, 4) for x in a], 'start': [round(x, 3) for x in p0],
                          'end': [round(x, 3) for x in p1], 'depthMm': round(t['h'][-1] - t['h'][0] + step, 2),
                          'dMin': round(float(d.min()), 3), 'dMedian': round(float(np.median(d)), 3), 'dMax': round(float(d.max()), 3),
                          'profile': [[round(h - t['h'][0], 2), round(x, 2)] for h, x in zip(t['h'], t['d'])]})
    return {'key': key, 'kind': kind, 'faces': int(len(m.faces)), 'watertight': bool(m.is_watertight), 'holes': holes}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keys', nargs='+', required=True)
    ap.add_argument('--kind', default='full')
    ap.add_argument('--out', required=True)
    ap.add_argument('--extra-axis', action='append', default=[], help='name:x,y,z')
    a = ap.parse_args()
    extra = [(s.split(':')[0], [float(x) for x in s.split(':')[1].split(',')]) for s in a.extra_axis]
    res = {}
    outp = Path(a.out)
    if outp.exists():
        res = json.loads(outp.read_text())
    for k in a.keys:
        r = inventory(k, a.kind, extra_axes=extra)
        res[k] = r
        outp.write_text(json.dumps(res, indent=1))
        print(k, 'holes', len(r['holes']), 'watertight', r['watertight'], flush=True)


if __name__ == '__main__':
    main()
