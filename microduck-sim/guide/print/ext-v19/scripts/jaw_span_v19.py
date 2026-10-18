#!/usr/bin/env python3
"""Jaw against the V1.9 wires that jaw_cap_v19.py does not cover: the free span from the torso guide to the bracket
clip, and every wire fixed on the head.

  span_P5_P6  route-v19.json point 5 (torso guide, trunk_base) to point 6 (bracket clip tie, neck_pitch): a taut
              straight tube of the group radius, rebuilt for each pose (it moves with neck_pitch and head_pitch).
              For every node of the runtime pose-cap grid whose table value is above 0, a lower bound of the gap
              between the jaw swept over 0..27 deg (pose_cap_sweep.Sweep sphere cover) and the segment is computed;
              nodes whose bound exceeds the contact threshold are clear, the others are scanned exactly up to the
              table value at that node (same contact rule as pose_cap_sweep).
  headFixed   the bundle from the head slot guide on (route points 9..32, jaw_soft), the eight fan wires and the five
              audio jumpers (route-v19.json fanWires / audioWires, radius 0.65 mm): their pose relative to the jaw
              depends on the jaw angle only; one scan from 0 to 40 deg each.
A span contact below the table value is a new restriction, like the parts in jaw_cap_v19.py.
Usage: jaw_span_v19.py   Writes the 'spans' entry of ../checks/jaw-cap-v19.json and
$EXT19_SCRATCH/jaw-cap-v19-spans-comb.npy.
"""
from __future__ import annotations

import json
import math
import time

import numpy as np

import ext_lib as E
import jaw_cap_v19 as JC

PCS = JC.PCS
JOINTS = JC.JOINTS


def seg_dist(c, a, b):
    ab = b - a
    t = np.clip(((c - a) @ ab) / max(ab @ ab, 1e-12), 0.0, 1.0)
    return np.linalg.norm(c - (a + t[:, None] * ab), axis=1)


def main():
    t_start = time.time()
    S, pts, rad = JC.parts()
    rt = json.loads((E.OUT / 'route-v19.json').read_text())
    head = {'bundle_head': JC.tube([p[:3] for p in pts[9:]], rad)}
    assert all(p[3] == 'jaw_soft' for p in pts[9:])
    for grp in ('fanWires', 'audioWires'):
        r = rt[grp]['radiusMm']
        for nm, pl in rt[grp]['polylines'].items():
            head[f'{grp}:{nm}'] = JC.tube([p[:3] for p in pl], r)
    S.update(head)
    JC.patch(S)
    axes, t, _ = JC.table()
    sw = PCS.Sweep(simplify=True)
    for k, M in head.items():
        sw.ck.man[k] = M
    sc = JC.Scanner(sw)
    out = {'_method': __doc__.strip(), 'headFixed': {}, 'span_P5_P6': {}}
    for k in head:
        a, part = sc.first({}, 'jaw_soft', [k], 40.0)
        out['headFixed'][k] = {'firstContactDeg': a}
        print('head-fixed', k, 'first contact', a, flush=True)
    p5, p6 = np.array(pts[5][:3], float), np.array(pts[6][:3], float)
    assert pts[5][3] == 'trunk_base' and pts[6][3] == 'neck_pitch'
    comb = np.full(t.shape, np.inf)
    rows, stats = [], {'nodes': 0, 'clearByBound': 0, 'scanned': 0, 'skippedClosed': 0}
    centres, r_s = sw.centres, sw.r_sphere
    for idx in np.ndindex(*t.shape):
        stats['nodes'] += 1
        L = float(t[idx])
        if L <= 0:
            stats['skippedClosed'] += 1
            continue
        q = {j: float(axes[j][i]) for j, i in zip(JOINTS, idx)}
        T = sw.ck.T(q, 0.0)
        Ti = np.linalg.inv(T['trunk_base'])
        M = Ti @ T['jaw_soft']
        c = centres @ M[:3, :3].T + M[:3, 3]
        b = (Ti @ T['neck_pitch'] @ np.r_[p6, 1.0])[:3]
        lb = float(seg_dist(c, p5, b).min()) - r_s - rad
        if lb > sw.gap:
            stats['clearByBound'] += 1
            continue
        sw.ck.man['span_P5_P6'] = JC.tube([p5, b], rad)
        a, part = sc.first(q, 'trunk_base', ['span_P5_P6'], L)
        stats['scanned'] += 1
        if a is not None:
            comb[idx] = a
            rows.append({**q, 'firstContactDeg': a, 'tableDeg': L,
                         'at': sc.locate(q, 'trunk_base', ['span_P5_P6'], a)})
            print('span56', q, 'contact', a, 'table', L, flush=True)
    out['span_P5_P6'] = {'stats': stats, 'newContacts': rows, 'tableNodesLowered': len(rows),
                         'summary': JC.summarize(t, comb)}
    np.save(E.SCRATCH / 'jaw-cap-v19-spans-comb.npy', comb)
    out['elapsedSeconds'] = round(time.time() - t_start, 1)
    path = E.OUT / 'checks' / 'jaw-cap-v19.json'
    d = json.loads(path.read_text()) if path.exists() else {}
    d['spans'] = out
    E.jdump(d, path)
    print('span56', stats, out['span_P5_P6']['summary'], flush=True)


if __name__ == '__main__':
    main()
