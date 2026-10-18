#!/usr/bin/env python3
"""Build the jaw pose-cap table guide/firmware/pi/jaw_pose_caps.json from the pose_cap_sweep.py grids.

First contact at a pose (neck_pitch, head_pitch, head_yaw, head_roll) is the smallest of:
  bracket group (head_yaw, head_roll), neck group (head_pitch, head_yaw, head_roll), torso group (all four).
null in the table means no contact up to clear_to_deg. Every grid node must be covered by the inputs.
The simulator copy microduck-simulator/app/src/game/jaw-pose-caps.json is written byte-identical, together with the
jaw_limits.json mirror.
Usage: build_pose_caps.py [--check]   (--check only verifies that the written files match a fresh build)
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GRIDS = HERE.parent
ROBOTICS = HERE.parents[4]
PI = ROBOTICS / 'microduck-sim/guide/firmware/pi'
SIM = ROBOTICS / 'microduck-sim/microduck-simulator/app/src/game'
OUT = PI / 'jaw_pose_caps.json'
MIRROR = SIM / 'jaw-pose-caps.json'
LIMITS_MIRROR = (PI / 'jaw_limits.json', SIM / 'jaw-limits.json')
JOINTS = ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll')


def load(pattern):
    files = sorted(GRIDS.glob(pattern))
    if not files:
        raise SystemExit(f'missing {pattern} in {GRIDS}')
    return [(f, json.loads(f.read_text())) for f in files]


def axis(values):
    values = sorted(set(values))
    step = values[1] - values[0]
    if any(abs(b - a - step) > 1e-9 for a, b in zip(values, values[1:])):
        raise SystemExit('grid axis is not uniform')
    return values, step


def main():
    check_only = '--check' in sys.argv[1:]
    groups = {'bracket': load('pose-grid-bracket.json'), 'neck': load('pose-grid-neck*.json'),
              'torso': load('pose-grid-torso*.json')}
    hi = {d['hiDeg'] for parts in groups.values() for _, d in parts}
    if len(hi) != 1:
        raise SystemExit('inputs disagree on hiDeg')
    hi = hi.pop()
    ax = {}
    for j in JOINTS:
        ax[j] = sorted({float(v) for parts in groups.values() for _, d in parts if j in d['axesDeg'] for v in d['axesDeg'][j]})
    values, bounds = {}, []
    for name, parts in groups.items():
        table = {}
        for _, d in parts:
            for n in d['nodes']:
                key = tuple(float(n[j]) for j in d['joints'])
                v = math.inf if n['firstContactJawDeg'] is None else float(n['firstContactJawDeg'])
                if key not in table or v < table[key][0]:
                    table[key] = (v, n['part'])
                if n['firstContactJawDeg'] is None and n.get('scanLimitDeg') is not None:
                    # Torso node scanned only up to the contact already known for its head pose: any contact is at or
                    # beyond scanLimitDeg, so the combined minimum must not exceed it (checked below).
                    bounds.append((dict(zip(d['joints'], key)), float(n['scanLimitDeg'])))
        values[name] = (parts[0][1]['joints'], table)

    def need(name, q):
        joints, table = values[name]
        key = tuple(q[j] for j in joints)
        if key not in table:
            raise SystemExit(f'{name} grid misses node {dict(zip(joints, key))}')
        return table[key]

    grid, limiting = [], {}
    for n in ax['neck_pitch']:
        cube = []
        for p in ax['head_pitch']:
            plane = []
            for y in ax['head_yaw']:
                row = []
                for r in ax['head_roll']:
                    q = {'neck_pitch': n, 'head_pitch': p, 'head_yaw': y, 'head_roll': r}
                    cands = [need('bracket', q) + ('bracket',), need('neck', q) + ('neck',), need('torso', q) + ('torso',)]
                    v, part, group = min(cands, key=lambda c: c[0])
                    row.append(None if not math.isfinite(v) or v >= hi else round(v, 2))
                    if math.isfinite(v) and v < hi:
                        limiting[(n, p, y, r)] = (v, part, group)
                plane.append(row)
            cube.append(plane)
        grid.append(cube)

    index = {j: {v: i for i, v in enumerate(ax[j])} for j in JOINTS}
    for q, limit in bounds:
        v = grid[index['neck_pitch'][q['neck_pitch']]][index['head_pitch'][q['head_pitch']]][index['head_yaw'][q['head_yaw']]][index['head_roll'][q['head_roll']]]
        if (hi if v is None else v) > limit + 1e-9:
            raise SystemExit(f'torso node {q} was scanned only to {limit} deg but the combined contact is {v}')
    axes = {}
    for j in JOINTS:
        vals, step = axis(ax[j])
        axes[j] = [vals[0], step, len(vals)]
    finite = [v for cube in grid for plane in cube for row in plane for v in row if v is not None]
    low = sorted(limiting.items(), key=lambda kv: kv[1][0])[:12]
    doc = {
        'schema': 1,
        'description': 'First jaw contact angle (deg of opening from the closed jaw) over the neck and head pose grid; '
                       'null = clear to clear_to_deg. Read by jaw_limits.py and the simulator jaw-safety.js.',
        'joints': list(JOINTS),
        'axes_deg': axes,
        'clear_to_deg': hi,
        'method': 'guide/extension-20261012-neck-audio/jaw-neck-check/scripts/pose_cap_sweep.py (CAD contact sweep, '
                  '0.2 mm contact on meshes simplified to 0.05 mm with a 0.3 mm threshold, bisected to 0.25 deg) '
                  'combined by build_pose_caps.py: min over the bracket, neck and torso part groups (torso nodes '
                  'scanned up to the bracket/neck contact for the head pose, which leaves the minimum unchanged).',
        'sources': {str(f.relative_to(GRIDS)): hashlib.sha256(f.read_bytes()).hexdigest()
                    for parts in groups.values() for f, _ in parts},
        'summary': {
            'nodes': math.prod(len(ax[j]) for j in JOINTS),
            'nodes_with_contact_below_clear': len(finite),
            'min_contact_deg': min(finite) if finite else None,
            'contact_below_7_deg_nodes': sum(1 for v in finite if v < 7),
            'lowest_nodes': [{**dict(zip(JOINTS, k)), 'contact_deg': round(v[0], 2), 'part': v[1], 'group': v[2]}
                             for k, v in low],
        },
        'first_contact_deg': grid,
    }
    head = json.dumps({k: v for k, v in doc.items() if k != 'first_contact_deg'}, indent=2)[:-2]
    cubes = ',\n'.join('    ' + json.dumps(cube, separators=(',', ':')) for cube in grid)
    text = head + ',\n  "first_contact_deg": [\n' + cubes + '\n  ]\n}\n'
    assert json.loads(text) == doc
    if check_only:
        bad = [str(p) for p in (OUT, MIRROR) if not p.exists() or p.read_text() != text]
        bad += [str(LIMITS_MIRROR[1])] if LIMITS_MIRROR[1].read_bytes() != LIMITS_MIRROR[0].read_bytes() else []
        print('stale: ' + ', '.join(bad) if bad else 'up to date')
        return 1 if bad else 0
    OUT.write_text(text)
    MIRROR.write_text(text)
    LIMITS_MIRROR[1].write_bytes(LIMITS_MIRROR[0].read_bytes())
    print(f'wrote {OUT} and {MIRROR}; nodes {doc["summary"]["nodes"]}, contact below {hi:g} at '
          f'{len(finite)}, min {doc["summary"]["min_contact_deg"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
