"""Where do the shins pass near the lower deck, and could the deck hangers sit somewhere the shins never reach?

Reads SCRATCH/sweep-<side>.npz (1 mm voxel counts of leg surface samples over the walking frames, from leg_sweep.py).
counts = adopted frames (no fall, no blend); counts_all = every frame.
For each candidate hanger footprint (4 mm along x by 2.4 mm along y, z from the deck bottom -57.5 up to the bay floor
-36), it reports how many voxels within a margin of the footprint were ever touched by a leg surface. A footprint with
zero touched voxels inside margin M means no sampled leg surface came within about M - 0.9 mm of it (voxel half
diagonal 0.87 mm, sample spacing 0.5 mm). Writes sweep-summary.json.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pso_lib as L

out = {}
for side in ('left', 'right'):
    p = L.SCRATCH / f'sweep-{side}.npz'
    if not p.exists():
        continue
    z = np.load(p); C = z['counts']; CA = z['counts_all']; BOX = z['box']; VS = float(z['vs'])
    s = 1.0 if side == 'left' else -1.0

    def region_counts(lo, hi, margin, arr):
        lo = np.array(lo) - margin; hi = np.array(hi) + margin
        a = np.maximum(np.ceil((lo - BOX[0]) / VS).astype(int), 0)
        b = np.minimum(np.floor((hi - BOX[0]) / VS).astype(int), np.array(arr.shape) - 1)
        sub = arr[a[0]:b[0] + 1, a[1]:b[1] + 1, a[2]:b[2] + 1]
        return int((sub > 0).sum()), int(sub.max()) if sub.size else 0

    ylo, yhi = sorted([s * 17.95, s * 20.4])
    res = {}
    # current post (x -37.5..-33.5)
    for m in (0.0, 1.0, 2.9):
        res[f'currentPost_margin{m}'] = dict(adopted=region_counts([-37.5, ylo, -57.5], [-33.5, yhi, -36.0], m, C),
                                             all=region_counts([-37.5, ylo, -57.5], [-33.5, yhi, -36.0], m, CA))
    # slide the same post along the deck edge
    scan = []
    for x0 in np.arange(-59.1, -15.9 + 1e-9, 0.5):
        r2 = region_counts([x0, ylo, -57.5], [x0 + 4.0, yhi, -36.0], 2.9, C)
        r2a = region_counts([x0, ylo, -57.5], [x0 + 4.0, yhi, -36.0], 2.9, CA)
        scan.append(dict(x0=round(float(x0), 2), adoptedTouchedVoxels=r2[0], adoptedMaxFrames=r2[1], allTouchedVoxels=r2a[0]))
    res['postSlideAlongDeckEdge_margin2.9'] = scan
    clear = [d['x0'] for d in scan if d['adoptedTouchedVoxels'] == 0]
    res['clearPostX0_adopted'] = clear
    res['clearPostX0_all'] = [d['x0'] for d in scan if d['allTouchedVoxels'] == 0]
    # how far inboard does the leg reach, per x slice, in the deck/post height band (z -57.5..-36)
    zs = slice(int(round((-57.5 - BOX[0][2]) / VS)), int(round((-36.0 - BOX[0][2]) / VS)) + 1)
    ys = BOX[0][1] + VS * np.arange(C.shape[1])
    prof = []
    for xi in range(C.shape[0]):
        x = BOX[0][0] + VS * xi
        if x < -62 or x > -8:
            continue
        col = C[xi, :, zs].max(1) > 0; cola = CA[xi, :, zs].max(1) > 0
        sel = ys[col] * s; sela = ys[cola] * s
        prof.append(dict(x=round(float(x), 1), innermostY_adopted=round(float(sel[sel > 0].min()), 1) if (sel > 0).any() else None,
                         innermostY_all=round(float(sela[sela > 0].min()), 1) if (sela > 0).any() else None))
    res['innermostLegY_inPostBand_byX'] = prof
    # leg occupancy in the deck/post band at |y| < 17.95 (under the tray)
    yin = np.abs(ys) < 17.95
    xs = BOX[0][0] + VS * np.arange(C.shape[0]); xin = (xs >= -86) & (xs <= -11)
    sub = C[np.ix_(xin, yin, np.arange(C.shape[2]))][:, :, zs]
    res['legVoxelsUnderDeckFootprint_adopted'] = int((sub > 0).sum())
    out[side] = res

L.jdump(out, Path(__file__).with_name('sweep-summary.json'))
for side, r in out.items():
    print(side, {k: v for k, v in r.items() if k.startswith('currentPost')})
    print(' clear x0 adopted:', r['clearPostX0_adopted'][:5], '...', r['clearPostX0_adopted'][-5:], len(r['clearPostX0_adopted']))
    print(' clear x0 all:', len(r['clearPostX0_all']))
    print(' profile:', [(d['x'], d['innermostY_adopted']) for d in r['innermostLegY_inPostBand_byX']][::3])
