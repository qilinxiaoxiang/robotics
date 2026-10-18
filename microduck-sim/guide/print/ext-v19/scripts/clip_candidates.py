#!/usr/bin/env python3
"""Design probe: first jaw contact with bracket clip shape variants, against the wire group the clip holds.

For each candidate (clips_v19.horn_clip channel options, before the build's neighbour trims) and every (head_yaw,
head_roll) node of the bracket group grid, the jaw is scanned from 0 up to the largest pose-cap table value for that
(yaw, roll) with pose_cap_sweep.Sweep.first_contact (no lower-bound pre-filter; the clip together with the raised
S11-horn-040 head). The result is compared with the first contact of the wire group fixed on the bracket (bundle
category of ../checks/jaw-cap-v19.json): a node where the clip is touched before the group is a restriction the clip
adds beyond the group.
Usage: clip_candidates.py name='{"r_out": 2.4, ...}' ...   (JSON channel options; "floor"/"ch_h" move the group centre)
Writes ../checks/clip-candidates-v19.json (merged per candidate).
"""
from __future__ import annotations

import json
import sys
import time

import numpy as np

import clips_v19 as C
import ext_lib as E
import jaw_cap_v19 as JC

PCS = JC.PCS


def main():
    cands = {}
    for a in sys.argv[1:]:
        k, v = a.split('=', 1)
        cands[k] = json.loads(v)
    S, pts, rad = JC.parts()
    for k, kw in cands.items():
        clip, rec = C.horn_clip('S11-horn-040', axis_point=[26.0, -17.5, 82.421], channel_dir=[0, 0, 1], channel_kw=kw)
        S[f'cand_{k}'] = clip
        cands[k] = {'channelOptions': kw, 'channel': rec['channel'], 'groupCentre': np.round(rec['channelInteriorCentre'], 3).tolist(),
                    'outerMostY': round(float(E.bbox(clip)[0][1]), 3), 'volumeMm3': round(clip.volume(), 2)}
    JC.patch(S)
    axes, t, _ = JC.table()
    sw = PCS.Sweep(simplify=True)
    for k in cands:
        sw.ck.man[f'cand_{k}'] = S[f'cand_{k}']
    sc = JC.Scanner(sw)
    jc = json.loads((E.OUT / 'checks' / 'jaw-cap-v19.json').read_text())
    bun = {(r['head_yaw'], r['head_roll']): r['firstContactDeg'] for r in jc['bracket']['categories']['bundle']['newContacts']}
    lim = t.max(axis=(0, 1))
    out_path = E.OUT / 'checks' / 'clip-candidates-v19.json'
    out = json.loads(out_path.read_text()) if out_path.exists() else {}
    out['_method'] = __doc__.strip()
    for k, info in cands.items():
        t0 = time.time()
        rows, worse, byroll = [], 0, {}
        for iy, y in enumerate(axes['head_yaw']):
            for ir, r in enumerate(axes['head_roll']):
                L = float(lim[iy, ir])
                if L <= 0:
                    continue
                q = {'head_yaw': float(y), 'head_roll': float(r)}
                a, part = sc.first(q, 'neck_pitch', [f'cand_{k}', 'raised_head_S11-horn-040'], L)
                if a is None:
                    continue
                b = bun.get((float(y), float(r)))
                ref = min(L, b) if b is not None else L
                byroll[r] = min(byroll.get(r, 99.0), a)
                if a < ref - 1e-9:
                    worse += int((t[:, :, iy, ir] > a + 1e-9).sum() - (t[:, :, iy, ir] > ref + 1e-9).sum())
                    rows.append({'head_yaw': float(y), 'head_roll': float(r), 'clipDeg': a, 'part': part, 'groupDeg': b,
                                 'at': sc.locate(q, 'neck_pitch', [f'cand_{k}', 'raised_head_S11-horn-040'], a)})
        info.update({'minClipContactDeg': min(byroll.values()) if byroll else None,
                     'minByRoll': {f'{r:g}': v for r, v in sorted(byroll.items())},
                     'nodesWhereClipBeforeGroup': len(rows), 'tableNodesLoweredBeyondGroup': worse,
                     'worst': sorted(rows, key=lambda x: x['clipDeg'])[:8], 'seconds': round(time.time() - t0, 1)})
        out[k] = info
        print(k, {kk: info[kk] for kk in ('outerMostY', 'groupCentre', 'minClipContactDeg', 'nodesWhereClipBeforeGroup',
                                          'tableNodesLoweredBeyondGroup')}, info['minByRoll'], flush=True)
        for w in info['worst'][:4]:
            print('    ', w['head_yaw'], w['head_roll'], w['clipDeg'], w['part'], 'group', w['groupDeg'],
                  [(x['part'], x['centre']) for x in w['at']], flush=True)
    E.jdump(out, out_path)


if __name__ == '__main__':
    main()
