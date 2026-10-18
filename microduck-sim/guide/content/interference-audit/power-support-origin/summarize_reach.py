"""Summarise the leg-reach runs into reach-summary.json (no CAD; reads SCRATCH outputs).

Groups: adopted = non-falling, non-blend phase-1 runs (all of them); priorSet = the 98-trace subset the previous study
used (candidate-* folders and zero-walk runs); excluded = falling or blend runs."""
import collections
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pso_lib as L

src = L.walking_sources()
trace = np.load(L.SCRATCH / 'walk_trace.npy'); frame = np.load(L.SCRATCH / 'walk_frame.npy')
Q = np.load(L.SCRATCH / 'walk_qpos.npy')
adopted_t = np.array([not s['fell'] and not s['blend'] for s in src])
prior_t = np.array([(s['file'].startswith('candidate-') or 'zero-walk' in s['file']) and not s['fell'] and not s['blend'] for s in src])
final_t = np.array([s['file'].startswith('phase1-candidate-') for s in src])
delay_t = np.array([s['sensor_delay_ticks'] == 2 for s in src])
G = {'adopted': adopted_t[trace], 'priorSet': prior_t[trace], 'excluded': ~adopted_t[trace],
     'finalController': final_t[trace], 'adoptedSensorDelay40ms': (adopted_t & delay_t)[trace],
     'adoptedNoSensorDelay': (adopted_t & ~delay_t)[trace]}
# identical trajectories (same config rerun under another name) are counted once in 'uniqueRuns'
import hashlib
hsh = []
for t in range(len(src)):
    hsh.append(hashlib.sha1(np.ascontiguousarray(Q[trace == t, 7:]).tobytes()).hexdigest())
first_of = {}
uniq_t = np.array([first_of.setdefault(h, t) == t for t, h in enumerate(hsh)])
out = {'groups': {g: dict(traces=int(len(set(trace[m].tolist()))), uniqueTrajectories=int(len(set(hsh[t] for t in set(trace[m].tolist())))),
                         frames=int(m.sum())) for g, m in G.items()},
       'groupDefinitions': {'adopted': 'non-falling, non-blend phase-1 walking runs', 'priorSet': 'candidate-* folders + zero-walk runs (previous study)',
                            'excluded': 'runs that fell or blended policies', 'finalController': 'top-level phase1-candidate-* (33 cases, kp 275, README candidate)',
                            'adoptedSensorDelay40ms': 'adopted runs with sensor_delay_ticks = 2 (40 ms)', 'adoptedNoSensorDelay': 'other adopted runs'}}

# locate the previous study's frame 54475 (index into its 147000-frame array)
prior_q = np.load('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/print-work/tray/p5_adopted_qpos.npy')
row = prior_q[54475]
hit = np.flatnonzero(np.all(np.abs(Q[:, 7:] - row) < 1e-9, 1))
out['priorFrame54475'] = dict(myIndex=hit.tolist(), files=[src[trace[h]]['file'] for h in hit], frameInRun=[int(frame[h]) for h in hit],
                              q={j: round(float(row[i]), 4) for i, j in enumerate(L.JOINT_ORDER_14) if j.startswith('left_')})


def summarize(side, tag=''):
    p = L.SCRATCH / f'reach-{side}-frames{tag}.json'
    if not p.exists():
        return None
    r = json.loads(p.read_text()); z = np.load(L.SCRATCH / f'reach-{side}-frames{tag}.npz')
    ex = z['exact']; tb = z['exact_tb']; ea = z['exact_added']
    res = dict(T1=r['T1'], legCoverMaxMm=max(r['legCoverRadiusMm'].values()), flagged=r['flaggedSupport'])
    for g, m in G.items():
        e = ex[m]
        um = m & uniq_t[trace]
        d = dict(frames=int(m.sum()), minGapSupport=float(e.min()), minGapAddedOnly=float(ea[m].min()),
                 uniqueFramesUnder2=int((ex[um] < 2).sum()), uniqueFramesContact0=int((ex[um] == 0).sum()), uniqueFrames=int(um.sum()),
                 runsUnder2=sorted(set(src[t]['file'] for t in trace[m][e < 2].tolist())),
                 under2=int((e < 2).sum()), under1=int((e < 1).sum()), under05=int((e < 0.5).sum()), contact0=int((e == 0).sum()),
                 tracesUnder2=int(len(set(trace[m][e < 2].tolist()))),
                 minGapTray=float(tb[m, 0].min()), minGapBoard=float(tb[m, 1].min()),
                 trayUnder2=int((tb[m, 0] < 2).sum()), boardUnder2=int((tb[m, 1] < 2).sum()))
        idx = np.flatnonzero(m)
        # region counts (exact, < 2 mm) and parts
        regc = collections.Counter(); partc = collections.Counter(); regmin = {}
        for i in idx[e < 2]:
            rg = r['regionGap'].get(str(int(i)), {})
            for name, (gap, part) in rg.items():
                if gap < 2:
                    regc[name] += 1; partc[L.LABEL.get(part, part)] += 1
                    regmin[name] = min(regmin.get(name, 99), gap)
        d['framesUnder2ByRegion'] = dict(regc); d['regionMinGap'] = regmin; d['partHitsUnder2'] = dict(partc)
        if len(idx):
            i = int(idx[np.argmin(e)])
            d['closestFrame'] = dict(index=i, file=src[trace[i]]['file'], frameInRun=int(frame[i]), gap=float(ex[i]),
                                     part=r['exactPart'].get(str(i)), q={j: round(float(v), 4) for j, v in zip(L.SIDE[side]['joints'], z['poses'][i])},
                                     overlap=r['overlap'].get(str(i)))
        d['contactFramesOverlapMm3Max'] = max([r['overlap'][str(int(i))][0] for i in idx if str(int(i)) in r['overlap']] or [0.0])
        res[g] = d
    pts = z['pts']
    if len(pts):
        sel = G['adopted'][pts[:, 0].astype(int)]
        for g, s in (('adopted', sel), ('all', np.ones(len(pts), bool))):
            if s.any():
                P = pts[s]
                res[f'nearestSupportPointsUnder2_{g}'] = dict(n=int(len(P)), supportMin=P[:, 1:4].min(0).round(2).tolist(),
                                                             supportMax=P[:, 1:4].max(0).round(2).tolist(),
                                                             legMin=P[:, 4:7].min(0).round(2).tolist(), legMax=P[:, 4:7].max(0).round(2).tolist(),
                                                             regions=dict(collections.Counter(L.region_of(p) for p in P[:, 1:4])))
    # how the near frames are distributed in time inside their runs
    near = np.flatnonzero(G['adopted'] & (ex < 2))
    res['adoptedUnder2_runs'] = dict(collections.Counter(src[trace[i]]['file'] for i in near).most_common(12))
    res['adoptedUnder2_frameInRunRange'] = [int(frame[near].min()), int(frame[near].max())] if len(near) else None
    return res


for side in ('left', 'right'):
    out[side] = summarize(side)
    out[side + '_originalSupport'] = summarize(side, '-original-power-support-body')
for side in ('left', 'right'):
    for mode in ('envelope', 'hipgrid'):
        p = L.SCRATCH / f'reach-{side}-{mode}.json'
        if p.exists():
            r = json.loads(p.read_text()); z = np.load(L.SCRATCH / f'reach-{side}-{mode}.npz')
            ex = z['exact']
            regc = collections.Counter()
            for i in np.flatnonzero(ex < 2):
                for name, (gap, part) in r['regionGap'].get(str(int(i)), {}).items():
                    if gap < 2:
                        regc[name] += 1
            i = int(np.argmin(ex))
            out[f'{side}_{mode}'] = dict(poses=r['poses'], grid=r['grid'], minGapSupport=float(ex.min()), minGapAdded=float(z['exact_added'].min()),
                                         under2=int((ex < 2).sum()), contact0=int((ex == 0).sum()), byRegionUnder2=dict(regc),
                                         minTray=r['exactMinTray'], minBoard=r['exactMinBoard'],
                                         closest=dict(q={j: round(float(v), 4) for j, v in zip(L.SIDE[side]['joints'], z['poses'][i])},
                                                      part=r['exactPart'].get(str(i)), gap=float(ex[i])))
L.jdump(out, Path(__file__).with_name('reach-summary.json'))
print(json.dumps(out, indent=1)[:12000])
