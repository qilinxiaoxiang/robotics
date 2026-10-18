"""Exact re-check of a candidate support against every walking frame / envelope pose that came within 2.5 mm of the
current support. A candidate only removes material, so every other pose keeps a gap >= its current gap (>= 2.5 mm).
Usage: check_candidate.py <candidate_robot_frame_stl> [frames|frames,envelope]   (default: frames)
Writes candidates/<stem>-check.json."""
import collections
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pso_lib as L

cand = Path(sys.argv[1]); MODES = (sys.argv[2] if len(sys.argv) > 2 else 'frames').split(',')
C = L.mesh_to_m(L.tm_load(cand))
B = L.mesh_to_m(L.tm_load(L.CB / 'power-support-integrated-body.stl'))
assert (C - B).volume() < 1e-3, 'candidate must be a subset of the current support'
tray = L.to_m(*L.solid('openrb_tray'))
src = L.walking_sources(); trace = np.load(L.SCRATCH / 'walk_trace.npy'); frame = np.load(L.SCRATCH / 'walk_frame.npy')
adopted = np.array([not s['fell'] and not s['blend'] for s in src])[trace]
final = np.array([s['file'].startswith('phase1-candidate-') for s in src])[trace]
delay = np.array([s['sensor_delay_ticks'] == 2 for s in src])[trace]
fk = L.FK()
out = {'candidate': str(cand)}
for side in ('left', 'right'):
    cfg = L.SIDE[side]; bodies = list(cfg['parts'])[2:]
    parts = [(b, k, L.to_m(*L.solid(k))) for b in bodies for k in cfg['parts'][b]]
    for mode in MODES:
        p = L.SCRATCH / f'reach-{side}-{mode}.npz'
        if not p.exists():
            continue
        z = np.load(p); ex = z['exact']; P = z['poses']
        idx = np.flatnonzero(ex < 2.5)
        new = {}; newtray = {}
        for i in idx:
            q = dict(zip(cfg['joints'], map(float, P[i])))
            PT = fk.part_T(q); g = 99.0; gt = 99.0; who = None
            for b, k, m in parts:
                mt = m.transform(np.asarray(PT[b][:3, :4]))
                d = mt.min_gap(C, 6.0)
                if d < g:
                    g, who = d, k
                gt = min(gt, mt.min_gap(tray, 6.0))
            new[int(i)] = (g, who); newtray[int(i)] = gt
        res = dict(posesRechecked=int(len(idx)), currentMinOutsideRecheck=float(ex[ex >= 2.5].min()) if (ex >= 2.5).any() else None)
        if mode == 'frames':
            for gname, m in (('adopted', adopted), ('finalController', final), ('finalControllerNoSensorDelay', final & ~delay),
                             ('adoptedNoSensorDelay', adopted & ~delay), ('excluded', ~adopted)):
                ii = [i for i in idx if m[i]]
                gaps = np.array([new[i][0] for i in ii]) if ii else np.array([99.0])
                cur = ex[m]
                bad = [i for i in ii if new[i][0] < 2.0]
                res[gname] = dict(currentMin=float(cur.min()), currentUnder2=int((cur < 2).sum()),
                                  candidateMin=float(min(gaps.min(), ex[m & (ex >= 2.5)].min() if (m & (ex >= 2.5)).any() else 99)),
                                  candidateUnder2=int(len(bad)), candidateContact0=int(sum(1 for i in ii if new[i][0] == 0.0)),
                                  runsStillUnder2=dict(collections.Counter(src[trace[i]]['file'] for i in bad)),
                                  trayUnder2InThoseFrames=int(sum(1 for i in bad if newtray[i] < 2.0)),
                                  trayMinInGroupRechecked=float(min([newtray[i] for i in ii] or [99.0])),
                                  stillUnder2_withTrayAlsoUnder2=int(sum(1 for i in bad if newtray[i] < 2.0)),
                                  stillUnder2_parts=dict(collections.Counter(new[i][1] for i in bad)))
        else:
            gaps = np.array([new[i][0] for i in idx]) if len(idx) else np.array([99.0])
            res['envelope'] = dict(currentMin=float(ex.min()), currentUnder2=int((ex < 2).sum()), candidateMin=float(gaps.min()),
                                   candidateUnder2=int((gaps < 2).sum()),
                                   trayUnder2AmongStillUnder2=int(sum(1 for i in idx if new[int(i)][0] < 2 and newtray[int(i)] < 2)))
        out[f'{side}_{mode}'] = res
        print(side, mode, json.dumps(res)[:1500], flush=True)
L.jdump(out, cand.with_name(cand.name.replace('-robot-frame.stl', '-check.json')))
