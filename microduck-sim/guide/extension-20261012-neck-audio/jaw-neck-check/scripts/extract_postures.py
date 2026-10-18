#!/usr/bin/env python3
"""Collect every simulated pickup row's head joints and jaw angle (read-only on microduck-simulator evidence).

Sources (MuJoCo traces written by the simulator's own runners; joint order = app/src/game/constants.js JOINT_NAMES,
qpos in rad; 'jaw' = beak_joint qpos in rad, 0 = closed, + = open):
  table   rl/runs/**/trial-*.json.gz          (jaw-PPO training/evaluation task: table-edge block)
  ground  rl/runs/ground-*/**/*.json           (ground-ball transfer of the same jaw actor)
  archive app/test-results/*.zip               (ground, household, whole-body and development trials; streamed)
For each trace: task family, accepted flag, beak_joint range from the embedded model XML when present, and every row's
neck_pitch, head_pitch, head_yaw, head_roll, jaw and phase. Writes ../postures.json (per-trace envelopes, binned unique
poses at 1 deg with counts) and ../postures-rows.npz (all rows).
"""
from __future__ import annotations

import glob
import gzip
import json
import re
import sys
import zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
SIM = HERE.parents[3] / 'microduck-simulator'
HEAD = slice(5, 9)                 # neck_pitch, head_pitch, head_yaw, head_roll
RANGE_RE = re.compile(r'name="beak_joint"[^>]*range="([-0-9.e]+) ([-0-9.e]+)"')


def family(name: str) -> str:
    n = name.lower()
    for k in ('household', 'ground', 'whole-body', 'table'):
        if k in n:
            return k
    if 'trial-' in n and ('heldout' in n or 'dev-' in n or 'negative' in n or 'final' in n or 'fine' in n):
        return 'table'
    return 'other'


def take(name, t, traces, rows):
    if not isinstance(t, dict) or not t.get('rows'):
        return
    r0 = t['rows'][0]
    if 'joint' not in r0 or 'jaw' not in r0:
        return
    q = np.array([r['joint'][HEAD] for r in t['rows']], float)
    jw = np.array([r['jaw'] for r in t['rows']], float)
    ph = [r.get('phase', '') for r in t['rows']]
    m = RANGE_RE.search(t.get('modelXml') or '')
    acc = (t.get('acceptance') or {}).get('accepted')
    fam = family(name)
    traces.append({'trace': name, 'family': fam, 'accepted': acc, 'rows': len(jw),
                   'beakRangeRad': [float(m.group(1)), float(m.group(2))] if m else None,
                   'jawMaxDeg': round(float(np.degrees(jw.max())), 2),
                   'rangeDeg': {j: [round(float(a), 1), round(float(b), 1)] for j, a, b in
                                zip(('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll'),
                                    np.degrees(q.min(0)), np.degrees(q.max(0)))}})
    k = len(traces) - 1
    for i in range(len(jw)):
        rows.append((k, *np.degrees(q[i]), np.degrees(jw[i]), ph[i]))


def main():
    traces, rows = [], []
    for p in sorted(glob.glob(str(SIM / 'rl/runs/**/*.json.gz'), recursive=True)):
        take(str(Path(p).relative_to(SIM)), json.load(gzip.open(p)), traces, rows)
    for p in sorted(glob.glob(str(SIM / 'rl/runs/**/*.json'), recursive=True)):
        try:
            take(str(Path(p).relative_to(SIM)), json.loads(Path(p).read_text()), traces, rows)
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    for z in sorted(glob.glob(str(SIM / 'app/test-results/*.zip'))):
        zf = zipfile.ZipFile(z)
        for info in zf.infolist():
            if not info.filename.endswith('.json') or '/source/' in info.filename:
                continue
            try:
                t = json.loads(zf.read(info))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            take(f'{Path(z).relative_to(SIM)}::{info.filename}', t, traces, rows)
            del t
        print(Path(z).name, len(traces), len(rows), file=sys.stderr, flush=True)
    tid = np.array([r[0] for r in rows])
    Q = np.array([r[1:6] for r in rows], float)          # neck, hp, yaw, roll, jaw (deg)
    ph = np.array([r[6] for r in rows])
    fam = np.array([traces[k]['family'] for k in tid])
    np.savez_compressed(OUT / 'postures-rows.npz', trace=tid, q=Q, phase=ph, family=fam)
    by_fam = {}
    for f in sorted(set(fam)):
        s = fam == f
        by_fam[f] = {'traces': int(len({int(k) for k in tid[s]})), 'rows': int(s.sum()),
                     'minDeg': np.round(Q[s].min(0), 1).tolist(), 'maxDeg': np.round(Q[s].max(0), 1).tolist(),
                     'jawOpenRows(>1deg)': int((Q[s, 4] > 1).sum())}
    b = np.round(Q).astype(int)
    uniq, inv, cnt = np.unique(b, axis=0, return_inverse=True, return_counts=True)
    fam_of = {}
    for i, f in zip(inv.ravel(), fam):
        fam_of.setdefault(int(i), set()).add(str(f))
    out = {'_method': __doc__.strip(), 'columns': ['neck_pitch', 'head_pitch', 'head_yaw', 'head_roll', 'jaw'],
           'beakRangesSeenRad': sorted({tuple(t['beakRangeRad']) for t in traces if t['beakRangeRad']}),
           'families': by_fam, 'uniquePoses1deg': int(len(uniq)),
           'poses': [{'q': u.tolist(), 'rows': int(c), 'families': sorted(fam_of[i])} for i, (u, c) in enumerate(zip(uniq, cnt))],
           'traces': traces}
    (OUT / 'postures.json').write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ('beakRangesSeenRad', 'families', 'uniquePoses1deg')}, indent=1))


if __name__ == '__main__':
    main()
