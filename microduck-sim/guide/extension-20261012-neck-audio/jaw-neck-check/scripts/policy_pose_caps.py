#!/usr/bin/env python3
"""Which simulated policy rows would the jaw pose cap clamp?

Inputs: ../postures-rows.npz and ../postures.json (every simulated pickup row: neck_pitch, head_pitch, head_yaw,
head_roll, jaw in deg; per-trace family and accepted flag), and the three jaw-limit release acceptances in
microduck-simulator/rl/runs/jaw-limit-eval-20261013 (rows with joint = JOINT_NAMES order, ctrl and jaw in rad).
The cap is guide/firmware/pi/jaw_limits.py pose_jaw_cap_deg(): for the posture rows the measured head pose only
(the logs hold no commanded pose); for the acceptance runs the box between the measured neck/head joints and the logged ctrl
(ctrl ignores the gravity offset bias/kp, about 1 deg, so this box is a slightly widened stand-in for the runtime box).
A row is clamped when its jaw opening exceeds the cap by more than 0.01 deg. Many recorded rows predate the 65 deg
head_pitch interlock (releases at head_pitch 71..85 with the jaw open); rows the interlock already rules out (jaw above
2 deg and head_pitch above 65 deg) are reported separately from the new pose-cap clamps. Vectorised lookup, checked against
jaw_limits.pose_contact_deg on a random subset. Writes ../policy-pose-caps.json.
"""
from __future__ import annotations

import itertools
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PI = HERE.parents[2] / 'firmware/pi'
SIM = HERE.parents[3] / 'microduck-simulator'
RUNS = SIM / 'rl/runs/jaw-limit-eval-20261013'
sys.path.insert(0, str(PI))
import jaw_limits as jl  # noqa: E402

TOL = 0.01
NAMES = jl.POSE_JOINTS
N = [jl.POSE_AXES[n][2] for n in NAMES]
FLAT = np.array(jl._POSE_FLAT).reshape(N)


def node_range(name, lo, hi):
    start, step, count = jl.POSE_AXES[name]
    end = start + step * (count - 1)
    tol = jl.JAW_POSE_EDGE_TOLERANCE_DEG + 1e-9
    off = (lo < start - tol) | (hi > end + tol)
    i0 = np.clip(np.floor((lo - start) / step + 1e-9).astype(int), 0, count - 1)
    i1 = np.clip(np.ceil((hi - start) / step - 1e-9).astype(int), 0, count - 1)
    below, above = lo < start - 1e-9, hi > end + 1e-9
    i1 = np.where(below, np.maximum(i1, 1), i1)
    i0 = np.where(above, np.minimum(i0, count - 2), i0)
    return i0, i1, off


def contact_deg(lo, hi):
    """lo, hi: (rows, len(NAMES)) degrees, per-row box. Same answer as jaw_limits.pose_contact_deg for the box."""
    rngs = [node_range(n, lo[:, a], hi[:, a]) for a, n in enumerate(NAMES)]
    out = np.full(len(lo), np.inf)
    spans = [int((r[1] - r[0]).max()) + 1 if len(lo) else 1 for r in rngs]
    for steps in itertools.product(*(range(k) for k in spans)):
        idx = tuple(np.minimum(r[0] + k, r[1]) for r, k in zip(rngs, steps))
        out = np.minimum(out, FLAT[idx])
    off = np.zeros(len(lo), bool)
    for r in rngs:
        off |= r[2]
    for r in np.flatnonzero(off):  # rare: a joint beyond the grid takes its whole axis
        out[r] = jl.pose_contact_deg({n: math.radians(lo[r, a]) for a, n in enumerate(NAMES)},
                                     {n: math.radians(hi[r, a]) for a, n in enumerate(NAMES)})
    return out, off


def caps(contact):
    cap = np.minimum(jl.JAW_MAX_OPEN_DEG, contact - jl.JAW_POSE_CAP_MARGIN_DEG)
    closed = cap < jl.JAW_MIN_USABLE_OPEN_DEG - jl.EPS_DEG
    return np.where(closed, 0.0, cap), closed


def self_check(lo, hi, contact, rng=np.random.default_rng(7), n=3000):
    idx = rng.choice(len(lo), size=min(n, len(lo)), replace=False)
    for r in idx:
        want = jl.pose_contact_deg({k: math.radians(lo[r, a]) for a, k in enumerate(NAMES)},
                                   {k: math.radians(hi[r, a]) for a, k in enumerate(NAMES)})
        if want != contact[r]:
            raise SystemExit(f'vectorised lookup differs at row {r}: {contact[r]} vs {want}')
    return len(idx)


def row(q, cap, contact, closed, extra=None):
    d = {'neck_pitch': round(float(q[0]), 2), 'head_pitch': round(float(q[1]), 2), 'head_yaw': round(float(q[2]), 2),
         'head_roll': round(float(q[3]), 2), 'jaw': round(float(q[4]), 2), 'capDeg': round(float(cap), 2),
         'contactDeg': round(float(contact), 2), 'closedZone': bool(closed)}
    return {**d, **(extra or {})}


def postures():
    d = np.load(ROOT / 'postures-rows.npz', allow_pickle=True)
    meta = json.loads((ROOT / 'postures.json').read_text())
    q, trace, phase, family = d['q'], d['trace'], d['phase'], d['family']
    accepted = np.array([bool(t['accepted']) for t in meta['traces']])[trace]
    head = q[:, 0:4]                     # neck_pitch, head_pitch, head_yaw, head_roll
    contact, off = contact_deg(head, head)
    checked = self_check(head, head, contact)
    cap, closed = caps(contact)
    over = q[:, 4] > cap + TOL
    res = {'rows': int(len(q)), 'rowsOffGrid': int(off.sum()), 'lookupSelfCheckRows': checked,
           'maxJawDeg': round(float(q[:, 4].max()), 2), 'minCapDeg': round(float(cap.min()), 2),
           'rowsClamped': int(over.sum()), 'rowsClampedAccepted': int((over & accepted).sum()),
           'tracesClamped': int(len(np.unique(trace[over]))),
           'tracesClampedAccepted': int(len(np.unique(trace[over & accepted]))),
           'rowsInClosedZone': int(closed.sum()), 'rowsInClosedZoneJawOpen': int((closed & (q[:, 4] > TOL)).sum()),
           'clampedByFamily': dict(Counter(family[over].tolist())),
           'clampedByPhase': dict(Counter(phase[over].tolist())),
           'clampedAcceptedByFamilyPhase': dict(Counter(f'{f}/{p}' for f, p in zip(family[over & accepted], phase[over & accepted]))),
           'jawOpenRows': int((q[:, 4] > jl.JAW_OPEN_THRESHOLD_DEG).sum())}
    excess = q[:, 4] - cap
    interlocked = (q[:, 4] > jl.JAW_OPEN_THRESHOLD_DEG + jl.EPS_DEG) & (q[:, 1] > jl.HEAD_PITCH_MAX_WHILE_JAW_OPEN_DEG + jl.EPS_DEG)
    new = over & ~interlocked
    res['rowsRuledOutBy65degInterlock'] = int(interlocked.sum())
    res['rowsClampedAlsoInterlocked'] = int((over & interlocked).sum())
    res['new'] = {'rows': int(new.sum()), 'rowsAccepted': int((new & accepted).sum()),
                  'traces': int(len(np.unique(trace[new]))), 'tracesAccepted': int(len(np.unique(trace[new & accepted]))),
                  'byFamilyPhase': dict(Counter(f'{f}/{p}' for f, p in zip(family[new], phase[new]))),
                  'byFamilyPhaseAccepted': dict(Counter(f'{f}/{p}' for f, p in zip(family[new & accepted], phase[new & accepted]))),
                  'closedZoneRows': int((new & closed).sum()),
                  'maxExcessDeg': round(float(excess[new].max()), 2) if new.any() else None}
    # Interlocked rows with the head held at 65 deg instead (what the runtime would command): does the pose cap act there?
    held = head[interlocked].copy()
    held[:, 1] = jl.HEAD_PITCH_MAX_WHILE_JAW_OPEN_DEG
    c65, _ = contact_deg(held, held)
    cap65, closed65 = caps(c65)
    over65 = q[interlocked, 4] > cap65 + TOL
    acc65 = accepted[interlocked]
    res['interlockedRowsAt65'] = {'rows': int(interlocked.sum()), 'clamped': int(over65.sum()),
                                  'clampedAccepted': int((over65 & acc65).sum()),
                                  'tracesClamped': int(len(np.unique(trace[interlocked][over65]))),
                                  'tracesClampedAccepted': int(len(np.unique(trace[interlocked][over65 & acc65]))),
                                  'byFamilyPhase': dict(Counter(f'{f}/{p}' for f, p in zip(family[interlocked][over65], phase[interlocked][over65]))),
                                  'minCapDeg': round(float(cap65.min()), 2) if len(cap65) else None,
                                  'closedZoneRows': int(closed65.sum()),
                                  'maxExcessDeg': round(float((q[interlocked, 4] - cap65)[over65].max()), 2) if over65.any() else None}
    zones_new = Counter()
    for r in np.flatnonzero(new):
        zones_new[(int(round(q[r, 0] / 15) * 15), int(round(q[r, 1] / 5) * 5), int(round(q[r, 2] / 10) * 10),
                   int(round(q[r, 3] / 5) * 5))] += 1
    res['new']['zones'] = [{'neck_pitch': k[0], 'head_pitch': k[1], 'head_yaw': k[2], 'head_roll': k[3], 'rows': v}
                           for k, v in zones_new.most_common(25)]
    wn = np.argsort(-np.where(new, excess, -np.inf))[:15]
    res['new']['worst'] = [row(q[r], cap[r], contact[r], closed[r], {'excessDeg': round(float(excess[r]), 2),
                           'family': str(family[r]), 'phase': str(phase[r]), 'accepted': bool(accepted[r]),
                           'trace': meta['traces'][int(trace[r])]['trace']}) for r in wn if new[r]]
    worst = np.argsort(-np.where(over, excess, -np.inf))[:15]
    res['worstClamped'] = [row(q[r], cap[r], contact[r], closed[r], {'excessDeg': round(float(excess[r]), 2),
                           'family': str(family[r]), 'phase': str(phase[r]), 'accepted': bool(accepted[r]),
                           'trace': meta['traces'][int(trace[r])]['trace']}) for r in worst if over[r]]
    # Pose zones that clamp: binned to the table grid.
    zones = Counter()
    for r in np.flatnonzero(over):
        zones[(int(round(q[r, 0] / 15) * 15), int(round(q[r, 1] / 5) * 5), int(round(q[r, 2] / 10) * 10),
               int(round(q[r, 3] / 5) * 5))] += 1
    res['clampedZones'] = [{'neck_pitch': k[0], 'head_pitch': k[1], 'head_yaw': k[2], 'head_roll': k[3], 'rows': v}
                           for k, v in zones.most_common(25)]
    return res


def acceptance(name):
    d = json.loads((RUNS / name).read_text())
    rows = d['rows']
    joint = np.array([json.loads(r['joint']) if isinstance(r['joint'], str) else r['joint'] for r in rows])
    ctrl = np.array([json.loads(r['ctrl']) if isinstance(r['ctrl'], str) else r['ctrl'] for r in rows])
    jaw = np.degrees(np.array([r['jaw'] for r in rows]))
    meas, cmd = np.degrees(joint[:, 5:9]), np.degrees(ctrl[:, 5:9])
    lo, hi = np.minimum(meas, cmd), np.maximum(meas, cmd)
    contact, off = contact_deg(lo, hi)
    self_check(lo, hi, contact, n=300)
    cap, closed = caps(contact)
    jaw_cmd = np.degrees(ctrl[:, 14]) if ctrl.shape[1] > 14 else jaw
    over = np.maximum(jaw, jaw_cmd) > cap + TOL
    phases = [r['phase'] for r in rows]
    q = np.column_stack([meas, jaw])
    res = {'file': name, 'accepted': d.get('acceptance', {}).get('accepted', d.get('phase') == 'done'),
           'rows': len(rows), 'rowsOffGrid': int(off.sum()), 'maxJawDeg': round(float(max(jaw.max(), jaw_cmd.max())), 2),
           'minCapDeg': round(float(cap.min()), 2), 'minCapDegJawOpen': round(float(cap[jaw > jl.JAW_OPEN_THRESHOLD_DEG].min()), 2)
           if (jaw > jl.JAW_OPEN_THRESHOLD_DEG).any() else None,
           'minMarginDeg': round(float((cap - np.maximum(jaw, jaw_cmd)).min()), 2),
           'rowsClamped': int(over.sum()), 'clampedPhases': dict(Counter(p for p, o in zip(phases, over) if o))}
    # The runtime box uses ctrl - bias/kp (gravity offset about 1 deg); widen the logged box by 2 deg per joint to cover it.
    cw, _ = contact_deg(lo - 2.0, hi + 2.0)
    capw, _ = caps(cw)
    res['widened2deg'] = {'rowsClamped': int((np.maximum(jaw, jaw_cmd) > capw + TOL).sum()),
                          'minMarginDeg': round(float((capw - np.maximum(jaw, jaw_cmd)).min()), 2)}
    tight = np.argsort(cap - np.maximum(jaw, jaw_cmd))[:5]
    res['tightestRows'] = [row(q[r], cap[r], contact[r], closed[r], {'phase': phases[r], 'jawCmdDeg': round(float(jaw_cmd[r]), 2)})
                           for r in tight]
    return res


def main():
    out = {'_method': __doc__.strip(), 'table': str(jl.POSE_TABLE_PATH.name),
           'tableSha256': __import__('hashlib').sha256(jl.POSE_TABLE_PATH.read_bytes()).hexdigest(),
           'tableMinContactDeg': jl.POSE_TABLE_MIN_CONTACT_DEG, 'postures': postures(),
           'acceptances': [acceptance(n) for n in ('limited-nominal-learned.json', 'limited-household-pen.json',
                                                    'limited-household-sock.json')]}
    (ROOT / 'policy-pose-caps.json').write_text(json.dumps(out, indent=1) + '\n')
    p = out['postures']
    print('postures', p['rows'], 'clamped', p['rowsClamped'], 'accepted', p['rowsClampedAccepted'], 'traces',
          p['tracesClamped'], 'accepted traces', p['tracesClampedAccepted'], 'closed-zone rows', p['rowsInClosedZone'])
    print('new (not already ruled out by the 65 deg interlock):', {k: v for k, v in p['new'].items() if k not in ('zones', 'worst')})
    print('interlocked rows held at head_pitch 65:', p['interlockedRowsAt65'])
    for a in out['acceptances']:
        print(a['file'], 'rows', a['rows'], 'clamped', a['rowsClamped'], 'min margin', a['minMarginDeg'], 'min cap',
              a['minCapDeg'], 'box widened 2 deg:', a['widened2deg'])


if __name__ == '__main__':
    main()
