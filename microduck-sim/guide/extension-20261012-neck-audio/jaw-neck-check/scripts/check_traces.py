#!/usr/bin/env python3
"""Exact jaw-frame overlap at every simulated pickup row (postures-rows.npz from extract_postures.py).

The jaw's pose relative to each body depends only on jaw_neck_check DEPENDS joints, so rows are screened per body:
  neck_pitch parts (head-pitch bracket, ring, idler 11): bins of head_yaw, head_roll at 1 deg
  neck parts (motor 11, motor 12, neck links):          bins of head_pitch, head_yaw, head_roll at 1 deg
  torso parts:                                           bins of all four head joints at 2 deg
Each bin is first evaluated at the row with the largest jaw opening in it (the actual joint values and jaw of that row).
Every bin whose representative is within 3 mm (or touching) is then re-evaluated at each of its distinct rows
(0.1 deg), so every reported contact is an exact evaluation of a real simulated row.
Writes ../trace-check.json.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict

import numpy as np

from jn_lib import DEPENDS, JOINTS, OUT, PARTS, TRAIN_JAW_MAX_DEG, Checker, check_solids, jdump

IDX = {j: i for i, j in enumerate(JOINTS)}
BIN = {'neck_pitch': 1.0, 'neck': 1.0, 'trunk_base': 2.0}
NEAR = 3.0


def main():
    t0 = time.time()
    z = np.load(OUT / 'postures-rows.npz')
    Q, fam, ph, tid = z['q'], z['family'], z['phase'], z['trace']
    traces = json.loads((OUT / 'postures.json').read_text())['traces']
    ck = Checker()
    solids = check_solids(['jaw_frame'] + [k for ks in PARTS.values() for k in ks])
    out = {'_method': __doc__.strip(), 'rows': int(len(Q)), 'trainJawMaxDeg': round(TRAIN_JAW_MAX_DEG, 2),
           'solids': solids, 'bodies': {}}
    for body, deps in DEPENDS.items():
        cols = [IDX[j] for j in deps]
        key = np.round(Q[:, cols] / BIN[body]).astype(int)
        _, inv = np.unique(key, axis=0, return_inverse=True)
        inv = inv.ravel()
        order = np.lexsort((-Q[:, 4], inv))            # within each bin, largest jaw first
        first = order[np.r_[True, inv[order][1:] != inv[order][:-1]]]
        near_bins, rep_min = [], {}
        for n, r in enumerate(first):
            qd = dict(zip(JOINTS, Q[r, :4]))
            rows = ck.jaw_vs(ck.T(qd, Q[r, 4]), (body,), search=NEAR)
            g = rows[0]['gapMm'] if rows else NEAR
            rep_min[int(inv[r])] = g
            if rows:
                near_bins.append(int(inv[r]))
            if n % 2000 == 0:
                print(body, n, len(first), f'{time.time() - t0:.0f}s', file=sys.stderr, flush=True)
        # exact pass over every distinct row of the near bins
        hits, near = [], []
        sel = np.isin(inv, near_bins)
        rq = np.round(Q[sel], 1)
        uq, uinv = np.unique(rq, axis=0, return_inverse=True)
        uinv = uinv.ravel()
        idx_sel = np.nonzero(sel)[0]
        res = []
        for u in uq:
            rows = ck.jaw_vs(ck.T(dict(zip(JOINTS, u[:4])), u[4]), (body,), search=NEAR, detail=True)
            res.append(rows[0] if rows else None)
        per_row_cls = np.array([(res[i]['class'] if res[i] else 'clear') for i in uinv])
        for c in ('interference', 'contact'):
            m = per_row_cls == c
            if not m.any():
                continue
            rr = idx_sel[m]
            hits.append({'class': c, 'rows': int(m.sum()),
                         'byFamily': dict(Counter(map(str, fam[rr]))), 'byPhase': dict(Counter(map(str, ph[rr]))),
                         'byPart': dict(Counter(res[i]['part'] for i in uinv[m])),
                         'traces': sorted({traces[int(k)]['trace'] for k in tid[rr]})[:40],
                         'tracesCount': len({int(k) for k in tid[rr]}),
                         'jawDegRange': [round(float(Q[rr, 4].min()), 2), round(float(Q[rr, 4].max()), 2)],
                         'jointRangeDeg': {j: [round(float(Q[rr, IDX[j]].min()), 1), round(float(Q[rr, IDX[j]].max()), 1)] for j in JOINTS},
                         'worst': max((res[i] for i in set(uinv[m].tolist())), key=lambda r: (r['overlapMm3'], -r['gapMm'])),
                         'worstPoseDeg': None})
            w = hits[-1]['worst']
            wi = next(i for i in set(uinv[m].tolist()) if res[i] is w)
            hits[-1]['worstPoseDeg'] = dict(zip(JOINTS + ('jaw',), uq[wi].tolist()))
        gaps = np.array([res[i]['gapMm'] if res[i] else NEAR for i in uinv]) if len(uinv) else np.array([])
        mn = int(np.argmin(gaps)) if len(gaps) else None
        out['bodies'][body] = {
            'parts': PARTS[body], 'dependsOn': list(deps), 'binDeg': BIN[body], 'bins': int(len(first)),
            'binsWithin3mm': len(near_bins), 'distinctRowsRechecked': int(len(uq)),
            'rowsInterference': int((per_row_cls == 'interference').sum()), 'rowsContact': int((per_row_cls == 'contact').sum()),
            'minGapMmOverAllRows': round(float(gaps.min()), 3) if mn is not None else f'>= {NEAR}',
            'minGapRow': ({'poseDeg': dict(zip(JOINTS + ('jaw',), np.round(Q[idx_sel[mn]], 2).tolist())),
                           'family': str(fam[idx_sel[mn]]), 'phase': str(ph[idx_sel[mn]]),
                           'trace': traces[int(tid[idx_sel[mn]])]['trace'], 'nearest': res[uinv[mn]]}
                          if mn is not None else None),
            'hits': hits}
        print(body, json.dumps({k: v for k, v in out['bodies'][body].items() if k != 'hits'}), f'{time.time() - t0:.0f}s',
              file=sys.stderr, flush=True)
    jdump(out, OUT / 'trace-check.json')


if __name__ == '__main__':
    main()
