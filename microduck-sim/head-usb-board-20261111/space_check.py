#!/usr/bin/env python3
"""Free space in the head for the USB board, from the guide's part meshes at HOME (guide/data/guide-data.json, robot frame mm).

Method: every head-region part is sampled on its surface into a 0.5 mm voxel grid. For a candidate slab (the thickness the
board with its headers and plugs needs) the grid is collapsed along the slab normal; the largest free rectangle that
contains a seed rectangle is the largest board outline that fits there. Wires are not in the meshes, so every result is
"free of parts", with a separate clearance margin. Parts that leave the head with the new board are removed first.

Run: ~/.venvs/microduck-cad/bin/python space_check.py   -> prints results, writes space-check.json (8 s on the Mac mini)
"""
import base64
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
GUIDE = json.loads((HERE.parent / 'guide' / 'data' / 'guide-data.json').read_text())
VOX = 0.5
REGION = np.array([[0.0, -48.0, 100.0], [95.0, 48.0, 160.0]])
REMOVED = {'amplifier', 'amp_tape'}            # the amp module leaves the head; its chip is on the new board
SOFT = {'camera_cable_stub'}                   # the camera lead is re-routed; reported separately
BREADBOARD = [[51.1, -22.0, 131.0], [63.4, -2.0, 146.0]]   # bringup/a7z/head-wire-lengths.json, on the robot today
PLUG = 16.0                                    # Dupont housing behind a header, same as the breadboard's plug tail


def mesh(p):
    v = np.frombuffer(base64.b64decode(p['positionB64']), dtype='<f4').reshape(-1, 3).astype(float)
    raw = base64.b64decode(p['indexB64'])
    i = None
    if len(raw) % 12 == 0:                       # 32-bit indices: valid when every index is a real vertex
        i4 = np.frombuffer(raw, dtype='<u4')
        if i4.max() < len(v):
            i = i4
    if i is None:
        i = np.frombuffer(raw, dtype='<u2')
        if i.max() >= len(v) or len(i) % 3:
            raise SystemExit(f"{p['key']}: index buffer is neither valid 32-bit nor 16-bit")
    return v, i.reshape(-1, 3)


def surface_points(v, f, step=0.3):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    lo, hi = np.minimum(np.minimum(a, b), c), np.maximum(np.maximum(a, b), c)
    keep = ((hi >= REGION[0]) & (lo <= REGION[1])).all(1)
    a, b, c = a[keep], b[keep], c[keep]
    out = []
    edge = np.maximum(np.linalg.norm(b - a, axis=1), np.linalg.norm(c - a, axis=1))
    n = np.maximum(1, np.ceil(edge / step).astype(int))
    for k in np.unique(n):
        m = n == k
        s, t = np.meshgrid(np.arange(k + 1) / k, np.arange(k + 1) / k)
        ok = s + t <= 1.0 + 1e-9
        s, t = s[ok], t[ok]
        pts = a[m][:, None] + s[None, :, None] * (b[m] - a[m])[:, None] + t[None, :, None] * (c[m] - a[m])[:, None]
        out.append(pts.reshape(-1, 3))
    return np.concatenate(out) if out else np.zeros((0, 3))


def grid(keys_skip):
    shape = np.ceil((REGION[1] - REGION[0]) / VOX).astype(int)
    g = np.zeros(shape, dtype=bool)
    owner = {}
    for p in GUIDE['parts']:
        b = p['bounds']
        lo, hi = (b['min'], b['max']) if isinstance(b, dict) else b
        if p['key'] in keys_skip or hi[2] < REGION[0][2] or lo[0] > REGION[1][0] or hi[0] < REGION[0][0]:
            continue
        pts = surface_points(*mesh(p))
        ijk = np.floor((pts - REGION[0]) / VOX).astype(int)
        ok = ((ijk >= 0) & (ijk < shape)).all(1)
        ijk = ijk[ok]
        g[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True
        owner[p['key']] = ijk
    return g, owner


def dilate(g, n):
    out = g.copy()
    for _ in range(n):
        d = out.copy()
        for ax in range(3):
            d |= np.roll(out, 1, ax) | np.roll(out, -1, ax)
        out = d
    return out


def idx(v, ax):
    return int(round((v - REGION[0][ax]) / VOX))


def largest_rect(free, seed):
    """free: 2D bool; seed: (i0, i1, j0, j1) half-open, must be free. Largest free rectangle containing the seed."""
    i0, i1, j0, j1 = seed
    if not free[i0:i1, j0:j1].all():
        return None
    S = np.zeros((free.shape[0] + 1, free.shape[1] + 1), dtype=int)
    S[1:, 1:] = np.cumsum(np.cumsum(~free, 0), 1)
    blocked = lambda a, b, c, d: S[b, d] - S[a, d] - S[b, c] + S[a, c]
    best = (0, seed)
    for a in range(i0, -1, -1):
        if blocked(a, i1, j0, j1):
            break
        for b in range(i1, free.shape[0] + 1):
            if blocked(a, b, j0, j1):
                break
            c = j0
            while c > 0 and not blocked(a, b, c - 1, j1):
                c -= 1
            d = j1
            while d < free.shape[1] and not blocked(a, b, c, d + 1):
                d += 1
            area = (b - a) * (d - c)
            if area > best[0]:
                best = (area, (a, b, c, d))
    return best[1]


def slab_free(g, ax, lo, hi):
    sl = [slice(None)] * 3
    sl[ax] = slice(max(0, idx(lo, ax)), idx(hi, ax))
    return ~g[tuple(sl)].any(ax)


def candidate(g, name, ax, body, plug, seed_box, clearance):
    """ax: slab normal. body/plug: (lo, hi) along ax. seed_box: [[x,y,z],[x,y,z]] known-free start."""
    gg = dilate(g, int(round(clearance / VOX))) if clearance else g
    other = [a for a in range(3) if a != ax]
    seed = (idx(seed_box[0][other[0]], other[0]), idx(seed_box[1][other[0]], other[0]),
            idx(seed_box[0][other[1]], other[1]), idx(seed_box[1][other[1]], other[1]))
    res = {'name': name, 'clearance_mm': clearance}
    for label, free in (('body_only', slab_free(gg, ax, *body)),
                        ('body_and_plugs', slab_free(gg, ax, *body) & slab_free(gg, ax, *plug))):
        r = largest_rect(free, seed)
        if r is None:
            res[label] = None
            continue
        a, b, c, d = r
        res[label] = {'axes': ['xyz'[other[0]], 'xyz'[other[1]]],
                      'from': [round(REGION[0][other[0]] + a * VOX, 1), round(REGION[0][other[1]] + c * VOX, 1)],
                      'to': [round(REGION[0][other[0]] + b * VOX, 1), round(REGION[0][other[1]] + d * VOX, 1)],
                      'size_mm': [round((b - a) * VOX, 1), round((d - c) * VOX, 1)]}
    return res


def main():
    g, owner = grid(REMOVED | SOFT)
    g_cable, _ = grid(REMOVED)
    out = {'guide_revision': GUIDE['revision'], 'voxel_mm': VOX, 'removed': sorted(REMOVED), 'not_modelled': 'wires',
           'candidates': []}
    bb = BREADBOARD
    shrink = lambda box, m: [[box[0][0], box[0][1] + m, box[0][2] + m], [box[1][0], box[1][1] - m, box[1][2] - m]]
    for cl in (0.0, 1.0):
        # A: upright on the camera back, where the breadboard is; plugs point backwards (-x)
        out['candidates'].append(candidate(g, 'A camera back, upright (breadboard place)', 0,
                                           (bb[0][0] + 0.5, bb[1][0] - 0.5), (bb[0][0] - PLUG, bb[0][0] + 0.5), shrink(bb, 2.0), cl))
        out['candidates'].append(candidate(g_cable, 'A with the camera lead where it is now', 0,
                                           (bb[0][0] + 0.5, bb[1][0] - 0.5), (bb[0][0] - PLUG, bb[0][0] + 0.5), shrink(bb, 2.0), cl))
    print(json.dumps(out, indent=1, ensure_ascii=False))
    (HERE / 'space-check.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    return g, out


if __name__ == '__main__':
    main()
